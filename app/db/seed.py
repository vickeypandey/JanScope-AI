from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.scheme_repository import SchemeRepository

logger = logging.getLogger(__name__)


def seed_schemes(db: Session, settings: Settings) -> int:
    """Idempotently load the curated demonstration dataset."""

    path = Path(settings.sample_data_path)
    if not path.exists():
        logger.warning("Sample scheme dataset not found: %s", path)
        return 0
    items = json.loads(path.read_text(encoding="utf-8"))
    repository = SchemeRepository(db)
    for item in items:
        repository.upsert_from_dict(item)
    db.commit()
    logger.info("Seeded %s scheme records", len(items))
    return len(items)
