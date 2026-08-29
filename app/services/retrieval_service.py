from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import DocumentChunk, Scheme
from app.repositories.scheme_repository import SchemeRepository

logger = logging.getLogger(__name__)
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9₹]+|[\u0900-\u097F]+")


@dataclass(slots=True)
class RetrievedChunk:
    chunk_key: str
    scheme_id: int
    scheme_slug: str
    scheme_name: str
    title: str
    content: str
    source_url: str
    last_verified: str
    score: float


class HashingEmbedder:
    """No-download embedding fallback suitable for a reproducible student demo.

    It hashes word unigrams and bigrams into a normalized numeric vector. This
    is intentionally simpler than a neural embedding model, but it demonstrates
    vector storage and cosine retrieval without downloading a large model.
    """

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        tokens = [token.casefold() for token in TOKEN_PATTERN.findall(text)]
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimensions
            sign = 1.0 if (number >> 8) & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class RetrievalService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.embedder = HashingEmbedder(settings.embedding_dimensions)
        self.backend_name = "memory"
        self._collection = None
        self._memory: dict[str, RetrievedChunk] = {}
        if settings.vector_backend.casefold() == "chroma":
            self._configure_chroma()

    def _configure_chroma(self) -> None:
        try:
            import chromadb

            Path(self.settings.chroma_path).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
            self._collection = client.get_or_create_collection(
                name=self.settings.vector_collection,
                metadata={"hnsw:space": "cosine"},
            )
            self.backend_name = "chroma"
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("Chroma unavailable; using in-memory retrieval: %s", type(exc).__name__)

    @staticmethod
    def _scheme_document(scheme: Scheme) -> str:
        def values(raw: str) -> str:
            try:
                return ", ".join(json.loads(raw or "[]"))
            except Exception:
                return ""

        age = ""
        if scheme.min_age is not None or scheme.max_age is not None:
            age = f"Age rule: minimum {scheme.min_age or 'not specified'}, maximum {scheme.max_age or 'not specified'}."
        income = (
            f"Maximum annual income encoded for preliminary checking: ₹{scheme.max_annual_income:,.0f}."
            if scheme.max_annual_income is not None
            else ""
        )
        return "\n".join(
            part
            for part in (
                f"Scheme: {scheme.name} ({scheme.short_name})",
                f"Category: {scheme.category}. Level: {scheme.level}.",
                f"Available states: {values(scheme.states_json)}.",
                scheme.description,
                f"Benefits: {scheme.benefits}",
                age,
                income,
                f"Relevant occupations: {values(scheme.occupations_json)}.",
                f"Relevant genders: {values(scheme.genders_json)}.",
                f"Relevant categories: {values(scheme.categories_json)}.",
                f"Education: {values(scheme.education_json)}.",
                f"Application steps: {values(scheme.application_steps_json)}.",
                f"Documents: {values(scheme.required_documents_json)}.",
                f"Official source summary: {scheme.source_excerpt}",
                f"Official URL: {scheme.official_url}",
                f"Last verified for this demo dataset: {scheme.last_verified}",
            )
            if part
        )

    def _split_text(self, text: str) -> list[str]:
        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            splitter = RecursiveCharacterTextSplitter(chunk_size=850, chunk_overlap=120)
            documents = splitter.split_documents([Document(page_content=text)])
            return [item.page_content for item in documents if item.page_content.strip()]
        except Exception:
            # Keeps demo mode operational even before the optional stack is installed.
            size, overlap = 850, 120
            chunks: list[str] = []
            start = 0
            while start < len(text):
                end = min(start + size, len(text))
                chunks.append(text[start:end].strip())
                if end == len(text):
                    break
                start = end - overlap
            return [item for item in chunks if item]

    def initialize_from_database(self, db: Session, force_rebuild: bool = False) -> int:
        repository = SchemeRepository(db)
        chunks = repository.all_chunks()
        if force_rebuild or not chunks:
            for scheme in repository.list():
                text = self._scheme_document(scheme)
                repository.replace_chunks(
                    scheme=scheme,
                    title=f"{scheme.name} official-information summary",
                    chunks=self._split_text(text),
                    source_url=scheme.official_url,
                )
            db.commit()
            chunks = repository.all_chunks()
        self._index_chunks(chunks)
        return len(chunks)

    def ingest_document(self, db: Session, scheme: Scheme, title: str, text: str, source_url: str) -> int:
        chunks = self._split_text(text)
        created = SchemeRepository(db).replace_chunks(scheme, title, chunks, source_url)
        db.commit()
        self._index_chunks(created)
        return len(created)

    def _index_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict] = []
        embeddings: list[list[float]] = []
        for chunk in chunks:
            scheme = chunk.scheme
            record = RetrievedChunk(
                chunk_key=chunk.chunk_key,
                scheme_id=scheme.id,
                scheme_slug=scheme.slug,
                scheme_name=scheme.name,
                title=chunk.title,
                content=chunk.content,
                source_url=chunk.source_url,
                last_verified=scheme.last_verified,
                score=0.0,
            )
            self._memory[chunk.chunk_key] = record
            ids.append(chunk.chunk_key)
            documents.append(chunk.content)
            metadatas.append(
                {
                    "scheme_id": scheme.id,
                    "scheme_slug": scheme.slug,
                    "scheme_name": scheme.name,
                    "title": chunk.title,
                    "source_url": chunk.source_url,
                    "last_verified": scheme.last_verified,
                }
            )
            embeddings.append(self.embedder.embed(chunk.content))
        if self._collection is not None:
            try:
                self._collection.upsert(
                    ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
                )
            except Exception as exc:  # pragma: no cover - environment dependent
                logger.error("Chroma indexing failed; memory index remains available: %s", type(exc).__name__)
                self.backend_name = "memory"

    @staticmethod
    def _token_set(text: str) -> set[str]:
        return {token.casefold() for token in TOKEN_PATTERN.findall(text) if len(token) > 1}

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        state: str | None = None,
        category: str | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k or self.settings.retrieval_top_k
        candidates: dict[str, tuple[RetrievedChunk, float]] = {}
        if self._collection is not None and self.backend_name == "chroma":
            try:
                count = self._collection.count()
                if count:
                    response = self._collection.query(
                        query_embeddings=[self.embedder.embed(query)],
                        n_results=min(max(k * 4, k), count),
                        include=["documents", "metadatas", "distances"],
                    )
                    for key, document, metadata, distance in zip(
                        response["ids"][0],
                        response["documents"][0],
                        response["metadatas"][0],
                        response["distances"][0],
                    ):
                        record = self._memory.get(key) or RetrievedChunk(
                            chunk_key=key,
                            scheme_id=int(metadata["scheme_id"]),
                            scheme_slug=str(metadata["scheme_slug"]),
                            scheme_name=str(metadata["scheme_name"]),
                            title=str(metadata["title"]),
                            content=document,
                            source_url=str(metadata["source_url"]),
                            last_verified=str(metadata.get("last_verified", "")),
                            score=0.0,
                        )
                        candidates[key] = (record, max(0.0, 1.0 - float(distance)))
            except Exception as exc:  # pragma: no cover - environment dependent
                logger.warning("Chroma query failed; using memory retrieval: %s", type(exc).__name__)

        query_tokens = self._token_set(query)
        pool = candidates or {key: (record, 0.0) for key, record in self._memory.items()}
        ranked: list[RetrievedChunk] = []
        state_lower = state.casefold() if state else None
        category_lower = category.casefold() if category else None
        for record, vector_score in pool.values():
            haystack = f"{record.scheme_name} {record.title} {record.content}"
            tokens = self._token_set(haystack)
            lexical = len(query_tokens & tokens) / max(len(query_tokens), 1)
            name_bonus = (
                0.18 if any(token in record.scheme_name.casefold() for token in query_tokens) else 0.0
            )
            state_bonus = 0.08 if state_lower and state_lower in haystack.casefold() else 0.0
            if category_lower and category_lower not in haystack.casefold():
                continue
            score = min(1.0, 0.58 * vector_score + 0.42 * lexical + name_bonus + state_bonus)
            ranked.append(
                RetrievedChunk(
                    chunk_key=record.chunk_key,
                    scheme_id=record.scheme_id,
                    scheme_slug=record.scheme_slug,
                    scheme_name=record.scheme_name,
                    title=record.title,
                    content=record.content,
                    source_url=record.source_url,
                    last_verified=record.last_verified,
                    score=score,
                )
            )
        ranked.sort(key=lambda item: (-item.score, item.scheme_name, item.chunk_key))
        # At most one highest-scoring chunk per scheme keeps citations diverse.
        unique: list[RetrievedChunk] = []
        seen: set[str] = set()
        for item in ranked:
            if item.scheme_slug in seen:
                continue
            seen.add(item.scheme_slug)
            unique.append(item)
            if len(unique) >= k:
                break
        return unique
