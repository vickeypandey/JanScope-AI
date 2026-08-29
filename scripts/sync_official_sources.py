from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.database import SessionLocal, create_tables  # noqa: E402
from app.services.container import ServiceContainer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize official government scheme pages")
    parser.add_argument("--max-pages", type=int, default=None, help="Bounded number of pages to process")
    args = parser.parse_args()
    settings = get_settings()
    create_tables()
    services = ServiceContainer(settings)
    with SessionLocal() as db:
        result = services.official_sources.sync_myscheme(db, args.max_pages)
    print(
        f"Discovered {result.discovered}; attempted {result.attempted}; "
        f"imported {result.imported}; skipped {result.skipped}; failed {result.failed}."
    )


if __name__ == "__main__":
    main()
