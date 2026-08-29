from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import Settings


class SlidingWindowRateLimiter:
    """Small single-process limiter. Use a shared gateway/Redis for multi-instance deployments."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, bucket: str, identity: str, limit: int, window_seconds: int = 60) -> int | None:
        now = time.monotonic()
        cutoff = now - window_seconds
        key = (bucket, identity)
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(window_seconds - (now - hits[0])))
            hits.append(now)
        return None


def client_identity(request: Request, settings: Settings) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def conversation_token(conversation_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), conversation_id.encode(), hashlib.sha256).hexdigest()


def valid_conversation_token(conversation_id: str, supplied: str | None, secret: str) -> bool:
    if not supplied or not secret:
        return False
    return hmac.compare_digest(supplied, conversation_token(conversation_id, secret))


def require_admin(request: Request) -> None:
    settings: Settings = request.app.state.services.settings
    if not settings.ingestion_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    supplied = request.headers.get("x-admin-key", "")
    if not settings.admin_api_key or not hmac.compare_digest(supplied, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authorization required")


def require_source_sync_admin(request: Request) -> None:
    settings: Settings = request.app.state.services.settings
    if not settings.live_source_sync_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    supplied = request.headers.get("x-admin-key", "")
    if not settings.admin_api_key or not hmac.compare_digest(supplied, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authorization required")
