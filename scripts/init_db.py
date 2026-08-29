from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.database import SessionLocal, create_tables  # noqa: E402
from app.db.seed import seed_schemes  # noqa: E402
from app.services.container import ServiceContainer  # noqa: E402


def main() -> None:
    settings = get_settings()
    create_tables()
    services = ServiceContainer(settings)
    with SessionLocal() as db:
        schemes = seed_schemes(db, settings)
        chunks = services.retrieval.initialize_from_database(db, force_rebuild=True)
    print(
        f"JanScope database ready: {schemes} schemes, {chunks} indexed chunks ({services.retrieval.backend_name})."
    )


if __name__ == "__main__":
    main()
