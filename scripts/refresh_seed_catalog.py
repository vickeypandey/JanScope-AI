from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.services.official_source_service import OfficialSourceService


CATALOG_PATH = ROOT / "data" / "schemes.json"
API_URL = "https://api.myscheme.gov.in/schemes/v6/public/schemes"
CURATED_SLUGS = """
ab-pmjay pmmvy pmay-g pmay-u pmjjby pmsby apy pmfby pm-kisan kcc pmv
pmegp pm-poshan pmmy ignwps igndps aaby sgs maps jsy1 agr4fmsscf rf mysy
gshtn pm-svanidhi pmjdy namo-shetkari-mahasanman-nidhi-yojana pm-sym
""".split()


def _scheme_from_api(record: dict) -> dict | None:
    content = record.get("en") or {}
    basic = content.get("basicDetails") or {}
    scheme_content = content.get("schemeContent") or {}
    name = str(basic.get("schemeName") or "").strip()
    description_parts = OfficialSourceService._flatten_text(
        scheme_content.get("detailedDescription_md")
        or scheme_content.get("detailedDescription")
        or scheme_content.get("briefDescription")
    )
    if not name or not description_parts:
        return None
    slug = str(record.get("slug") or "").strip()
    benefits = OfficialSourceService._flatten_text(
        scheme_content.get("benefits_md") or scheme_content.get("benefits")
    )
    steps = OfficialSourceService._flatten_text(content.get("applicationProcess"))
    documents = OfficialSourceService._flatten_text(content.get("documentsRequired"))
    tags = OfficialSourceService._flatten_text(
        basic.get("schemeCategory") or basic.get("tags")
    )
    level = OfficialSourceService._display_value(basic.get("level"), "Central/State")
    state = OfficialSourceService._display_value(basic.get("state"))
    return {
        "slug": f"myscheme-{slug}",
        "name": name,
        "short_name": str(basic.get("schemeShortTitle") or "")[:80],
        "description": " ".join(description_parts)[:4000],
        "category": (tags[0] if tags else "Government Scheme")[:100],
        "level": level[:40],
        "states": [state] if state else ["All India"],
        "occupations": [],
        "genders": [],
        "categories": [],
        "education": [],
        "min_age": None,
        "max_age": None,
        "max_annual_income": None,
        "benefits": " ".join(benefits)[:4000]
        or "See the official myScheme page for current benefits.",
        "application_steps": steps[:30],
        "required_documents": documents[:30],
        "official_url": f"https://www.myscheme.gov.in/schemes/{slug}",
        "last_verified": date.today().isoformat(),
        "source_excerpt": "\n".join([name, *description_parts, *benefits])[:12000],
        "active": True,
    }


def main() -> None:
    settings = get_settings()
    if not settings.myscheme_public_api_key:
        raise RuntimeError("MYSCHEME_PUBLIC_API_KEY is required")
    existing = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    known_names = {str(item["name"]).casefold() for item in existing}
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.post(
            API_URL,
            headers={"x-api-key": settings.myscheme_public_api_key},
            json=CURATED_SLUGS,
        )
        response.raise_for_status()
        records = response.json().get("data") or []
    added = []
    for record in records:
        item = _scheme_from_api(record)
        if item and item["name"].casefold() not in known_names:
            existing.append(item)
            known_names.add(item["name"].casefold())
            added.append(item["name"])
    CATALOG_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Catalog now contains {len(existing)} schemes; added {len(added)}.")


if __name__ == "__main__":
    main()
