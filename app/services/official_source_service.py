from __future__ import annotations

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.scheme_repository import SchemeRepository
from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class _VisibleTextParser(HTMLParser):
    SKIP = {"script", "style", "svg", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._heading_depth = 0
        self.lines: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag in {"h1", "h2"}:
            self._heading_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"h1", "h2"} and self._heading_depth:
            self._heading_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if cleaned and cleaned not in self.lines:
            self.lines.append(cleaned)
        if self._heading_depth and cleaned and cleaned not in self.headings:
            self.headings.append(cleaned)


@dataclass(slots=True)
class SyncResult:
    discovered: int
    attempted: int
    imported: int
    skipped: int
    failed: int
    source: str


class OfficialSourceService:
    """Incrementally cache public scheme pages from explicitly trusted government hosts."""

    USER_AGENT = "JanScopeAI/1.0 (+public scheme information cache; contact project administrator)"
    MYScheme_SITEMAP = "https://www.myscheme.gov.in/sitemap.xml"
    MYScheme_DIRECTORY = "https://rules.myscheme.gov.in/"
    MYScheme_API = "https://api.myscheme.gov.in/schemes/v6/public/schemes"
    SECTION_NAMES = {
        "details": ("details", "about the scheme"),
        "benefits": ("benefits",),
        "eligibility": ("eligibility",),
        "application_steps": ("application process", "how to apply"),
        "required_documents": ("documents required", "required documents"),
    }

    def __init__(self, settings: Settings, retrieval: RetrievalService):
        self.settings = settings
        self.retrieval = retrieval

    def _allowed(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").casefold()
        return any(host == domain or host.endswith(f".{domain}") for domain in self.settings.official_source_domains)

    def _robots_allows(self, client: httpx.Client, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            response = client.get(robots_url)
            if response.status_code >= 400:
                return False
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            return parser.can_fetch(self.USER_AGENT, url)
        except httpx.HTTPError:
            return False

    @staticmethod
    def _sitemap_urls(xml_text: str) -> list[str]:
        root = ET.fromstring(xml_text)
        return [
            node.text.strip()
            for node in root.iter()
            if node.tag.rsplit("}", 1)[-1] == "loc" and node.text
        ]

    def _discover_scheme_urls(self, client: httpx.Client) -> list[str]:
        pending = [self.MYScheme_SITEMAP]
        visited: set[str] = set()
        schemes: set[str] = set()
        while pending and len(visited) < 50:
            sitemap_url = pending.pop(0)
            if sitemap_url in visited or not self._allowed(sitemap_url):
                continue
            visited.add(sitemap_url)
            response = client.get(sitemap_url)
            response.raise_for_status()
            for url in self._sitemap_urls(response.text):
                path = urlparse(url).path.casefold()
                if "/schemes/" in path and self._allowed(url):
                    schemes.add(url.split("?", 1)[0])
                elif (path.endswith(".xml") or "sitemap" in path) and self._allowed(url):
                    pending.append(url)
        try:
            response = client.get(self.MYScheme_DIRECTORY)
            response.raise_for_status()
            for match in re.findall(
                r"(?:https://www\.myscheme\.gov\.in)?/schemes/[a-z0-9-]+",
                response.text,
                flags=re.IGNORECASE,
            ):
                url = match if match.startswith("http") else f"https://www.myscheme.gov.in{match}"
                if self._allowed(url):
                    schemes.add(url)
        except httpx.HTTPError as exc:
            logger.warning("Official scheme directory unavailable error=%s", type(exc).__name__)
        schemes.update(url for url in self.settings.official_bootstrap_urls if self._allowed(url))
        return sorted(schemes)

    @staticmethod
    def _sections(lines: list[str]) -> dict[str, list[str]]:
        aliases = {
            alias.casefold(): key
            for key, names in OfficialSourceService.SECTION_NAMES.items()
            for alias in names
        }
        output = {key: [] for key in OfficialSourceService.SECTION_NAMES}
        current = "details"
        for line in lines:
            normalized = line.casefold().strip(" :")
            if normalized in aliases:
                current = aliases[normalized]
                continue
            if line in {"Frequently Asked Questions", "Quick Links", "Get in touch"}:
                current = ""
            if current and 2 < len(line) < 1500:
                output[current].append(line)
        return output

    def _parse_scheme(self, url: str, html_text: str) -> dict | None:
        parser = _VisibleTextParser()
        parser.feed(html_text)
        lines = parser.lines
        sections = self._sections(lines)
        ignored = {name.casefold() for names in self.SECTION_NAMES.values() for name in names}
        candidates = [
            line for line in lines
            if 4 <= len(line) <= 240
            and line.casefold() not in ignored
            and not line.startswith(("©", "http"))
        ]
        title = next(
            (
                line for line in parser.headings
                if line.casefold() not in ignored
                and line not in {"Frequently Asked Questions", "Quick Links", "Useful Links", "Get in touch"}
            ),
            None,
        )
        if not title:
            title = next((line for line in candidates if "scheme" in line.casefold() or "yojana" in line.casefold()), None)
        boilerplate = {"useful links", "quick links", "get in touch", "network error", "back"}
        meaningful_lines = [line for line in lines if line.casefold() not in boilerplate]
        if (
            not title
            or title.casefold() in boilerplate
            or len(" ".join(sections["details"])) < 80
            or not any(term in " ".join(meaningful_lines).casefold() for term in ("eligibility", "benefit", "scheme", "yojana"))
        ):
            return None
        slug = urlparse(url).path.rstrip("/").split("/")[-1].casefold()
        slug = re.sub(r"[^a-z0-9-]", "-", slug).strip("-")
        if not slug:
            slug = hashlib.sha256(url.encode()).hexdigest()[:20]
        description = " ".join(sections["details"][:8])[:4000]
        benefits = " ".join(sections["benefits"][:8])[:4000] or description[:1000]
        source_text = "\n".join(lines[:220])[:12000]
        return {
            "slug": f"myscheme-{slug}",
            "name": title,
            "short_name": "",
            "description": description,
            "category": "Government Scheme",
            "level": "Central/State",
            "states": ["All India"],
            "benefits": benefits,
            "application_steps": sections["application_steps"][:20],
            "required_documents": sections["required_documents"][:30],
            "official_url": url,
            "last_verified": date.today().isoformat(),
            "source_excerpt": source_text,
            "active": True,
        }

    @staticmethod
    def _flatten_text(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = " ".join(value.replace("#", " ").replace("*", " ").split())
            return [cleaned] if cleaned else []
        if isinstance(value, dict):
            output: list[str] = []
            for key, item in value.items():
                if key.casefold() not in {
                    "_id", "id", "createdat", "updatedat", "type", "format", "elementtype"
                }:
                    output.extend(OfficialSourceService._flatten_text(item))
            return output
        if isinstance(value, list):
            output: list[str] = []
            for item in value:
                output.extend(OfficialSourceService._flatten_text(item))
            return output
        return [str(value)]

    @staticmethod
    def _display_value(value, fallback: str = "") -> str:
        if isinstance(value, dict):
            return str(value.get("label") or value.get("name") or value.get("value") or fallback)
        if isinstance(value, list):
            return ", ".join(OfficialSourceService._display_value(item) for item in value if item)
        return str(value or fallback)

    def _fetch_api_scheme(self, client: httpx.Client, url: str) -> dict | None:
        if not self.settings.myscheme_public_api_key:
            return None
        slug = urlparse(url).path.rstrip("/").split("/")[-1].casefold()
        response = client.get(
            self.MYScheme_API,
            params={"slug": slug, "lang": "en"},
            headers={"x-api-key": self.settings.myscheme_public_api_key},
        )
        response.raise_for_status()
        payload = response.json().get("data") or {}
        content = payload.get("en") or {}
        basic = content.get("basicDetails") or {}
        scheme_content = content.get("schemeContent") or {}
        eligibility = content.get("eligibilityCriteria") or {}
        name = str(basic.get("schemeName") or "").strip()
        description_parts = self._flatten_text(
            scheme_content.get("detailedDescription_md")
            or scheme_content.get("detailedDescription")
            or scheme_content.get("briefDescription")
        )
        invalid_name_terms = ("support-", "[at]", "@", "get in touch", "useful links")
        if (
            not name
            or not description_parts
            or any(term in name.casefold() for term in invalid_name_terms)
        ):
            return None
        benefits = self._flatten_text(
            scheme_content.get("benefits_md") or scheme_content.get("benefits")
        )
        application_steps = self._flatten_text(content.get("applicationProcess"))
        eligibility_text = self._flatten_text(
            eligibility.get("eligibilityDescription_md") or eligibility.get("eligibilityDescription")
        )
        tags = self._flatten_text(basic.get("tags") or basic.get("schemeCategory"))
        source_lines = [
            name,
            *description_parts,
            "Benefits",
            *benefits,
            "Eligibility",
            *eligibility_text,
            "Application Process",
            *application_steps,
        ]
        return {
            "slug": f"myscheme-{slug}",
            "name": name,
            "short_name": str(basic.get("schemeShortTitle") or "")[:80],
            "description": " ".join(description_parts)[:4000],
            "category": (tags[0] if tags else "Government Scheme")[:100],
            "level": self._display_value(basic.get("level"), "Central/State")[:40],
            "states": [],
            "benefits": " ".join(benefits)[:4000] or "See the official source for current benefits.",
            "application_steps": application_steps[:30],
            "required_documents": [],
            "official_url": url,
            "last_verified": date.today().isoformat(),
            "source_excerpt": "\n".join(source_lines)[:12000],
            "active": True,
        }

    def sync_myscheme(self, db: Session, max_pages: int | None = None) -> SyncResult:
        limit = min(max_pages or self.settings.live_sync_max_pages, self.settings.live_sync_max_pages)
        timeout = httpx.Timeout(self.settings.official_fetch_timeout_seconds, connect=5.0)
        imported = skipped = failed = attempted = 0
        with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": self.USER_AGENT}) as client:
            if not self._allowed(self.MYScheme_SITEMAP) or not self._robots_allows(client, self.MYScheme_SITEMAP):
                raise ValueError("Official source policy does not permit synchronization")
            urls = self._discover_scheme_urls(client)
            repository = SchemeRepository(db)
            existing = {item.official_url: item for item in repository.list()}
            urls.sort(key=lambda item: (item in existing, item))
            for url in urls[:limit]:
                attempted += 1
                try:
                    item = self._fetch_api_scheme(client, url)
                    if item is None:
                        response = client.get(url)
                        response.raise_for_status()
                        item = self._parse_scheme(url, response.text)
                    if not item:
                        skipped += 1
                        continue
                    scheme = repository.upsert_from_dict(item)
                    db.commit()
                    self.retrieval.ingest_document(
                        db,
                        scheme,
                        f"{scheme.name} — myScheme official page",
                        item["source_excerpt"],
                        url,
                    )
                    existing[url] = scheme
                    imported += 1
                except (httpx.HTTPError, ValueError, ET.ParseError) as exc:
                    logger.warning("Official source sync skipped url_hash=%s error=%s", hashlib.sha256(url.encode()).hexdigest()[:10], type(exc).__name__)
                    db.rollback()
                    failed += 1
                time.sleep(self.settings.official_fetch_delay_seconds)
        return SyncResult(len(urls), attempted, imported, skipped, failed, self.MYScheme_SITEMAP)
