from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk, Scheme
from app.schemas.models import SchemeDetail, SchemeSummary

JSON_FIELDS = (
    "states",
    "occupations",
    "genders",
    "categories",
    "education",
    "application_steps",
    "required_documents",
)


def _loads(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def scheme_to_summary(scheme: Scheme) -> SchemeSummary:
    return SchemeSummary(
        id=scheme.id,
        slug=scheme.slug,
        name=scheme.name,
        short_name=scheme.short_name,
        description=scheme.description,
        category=scheme.category,
        level=scheme.level,
        states=_loads(scheme.states_json),
        benefits=scheme.benefits,
        official_url=scheme.official_url,
        last_verified=scheme.last_verified,
    )


def scheme_to_detail(scheme: Scheme) -> SchemeDetail:
    return SchemeDetail(
        **scheme_to_summary(scheme).model_dump(),
        min_age=scheme.min_age,
        max_age=scheme.max_age,
        max_annual_income=scheme.max_annual_income,
        occupations=_loads(scheme.occupations_json),
        genders=_loads(scheme.genders_json),
        categories=_loads(scheme.categories_json),
        education=_loads(scheme.education_json),
        application_steps=_loads(scheme.application_steps_json),
        required_documents=_loads(scheme.required_documents_json),
        source_excerpt=scheme.source_excerpt,
    )


class SchemeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, state: str | None = None, category: str | None = None) -> list[Scheme]:
        statement = select(Scheme).where(Scheme.active.is_(True)).order_by(Scheme.name)
        if category:
            statement = statement.where(Scheme.category.ilike(f"%{category}%"))
        schemes = list(self.db.scalars(statement).all())
        if state:
            state_lower = state.casefold()
            schemes = [
                item
                for item in schemes
                if "all india" in {x.casefold() for x in _loads(item.states_json)}
                or state_lower in {x.casefold() for x in _loads(item.states_json)}
            ]
        return schemes

    def get_by_slug(self, slug: str) -> Scheme | None:
        return self.db.scalar(select(Scheme).where(Scheme.slug == slug, Scheme.active.is_(True)))

    def get_by_id(self, scheme_id: int) -> Scheme | None:
        return self.db.get(Scheme, scheme_id)

    def count(self) -> int:
        return len(self.db.scalars(select(Scheme.id)).all())

    def upsert_from_dict(self, item: dict[str, Any]) -> Scheme:
        scheme = self.db.scalar(select(Scheme).where(Scheme.slug == item["slug"]))
        if scheme is None:
            scheme = Scheme(
                slug=item["slug"],
                name=item["name"],
                description=item["description"],
                category=item["category"],
                benefits=item["benefits"],
                official_url=item["official_url"],
            )
            self.db.add(scheme)

        scalar_fields = (
            "name",
            "short_name",
            "description",
            "category",
            "level",
            "min_age",
            "max_age",
            "max_annual_income",
            "benefits",
            "official_url",
            "last_verified",
            "source_excerpt",
            "active",
        )
        for field in scalar_fields:
            if field in item:
                setattr(scheme, field, item[field])
        for field in JSON_FIELDS:
            key = f"{field}_json"
            setattr(scheme, key, json.dumps(item.get(field, []), ensure_ascii=False))
        self.db.flush()
        return scheme

    def replace_chunks(
        self, scheme: Scheme, title: str, chunks: list[str], source_url: str
    ) -> list[DocumentChunk]:
        existing = list(
            self.db.scalars(select(DocumentChunk).where(DocumentChunk.scheme_id == scheme.id)).all()
        )
        for item in existing:
            self.db.delete(item)
        self.db.flush()
        created: list[DocumentChunk] = []
        for index, content in enumerate(chunks):
            chunk = DocumentChunk(
                chunk_key=f"{scheme.slug}:{index}",
                scheme_id=scheme.id,
                title=title,
                content=content,
                source_url=source_url,
                chunk_index=index,
            )
            self.db.add(chunk)
            created.append(chunk)
        self.db.flush()
        return created

    def all_chunks(self) -> list[DocumentChunk]:
        return list(self.db.scalars(select(DocumentChunk).order_by(DocumentChunk.id)).all())
