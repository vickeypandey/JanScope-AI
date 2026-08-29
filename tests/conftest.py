from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("AI_ENABLED", "false")
os.environ.setdefault("VECTOR_BACKEND", "memory")
os.environ.setdefault("SEED_SAMPLE_DATA", "true")
os.environ.setdefault("INGESTION_ENABLED", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-not-for-production")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(ROOT / 'data' / 'test_janscope.db').as_posix()}")
os.environ["LIVE_SOURCE_SYNC_ENABLED"] = "false"
os.environ["OTP_DELIVERY_MODE"] = "development"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
