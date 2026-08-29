from __future__ import annotations

import logging
import asyncio
from contextlib import suppress
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import SlidingWindowRateLimiter, client_identity
from app.db.database import SessionLocal, create_tables
from app.db.seed import seed_schemes
from app.services.container import ServiceContainer

settings = get_settings()
settings.validate_production()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.sample_documents_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    create_tables()
    with SessionLocal() as db:
        if settings.seed_sample_data:
            seed_schemes(db, settings)
        else:
            logger.info("Bundled sample-data seeding is disabled")
        count = app.state.services.retrieval.initialize_from_database(db)
        logger.info("Retrieval index ready with %s chunks", count)
    sync_task = None
    if settings.live_source_sync_enabled:
        async def scheduled_sync() -> None:
            while True:
                try:
                    def run_sync() -> None:
                        with SessionLocal() as sync_db:
                            result = app.state.services.official_sources.sync_myscheme(sync_db)
                            logger.info(
                                "Official source sync imported=%s skipped=%s failed=%s",
                                result.imported,
                                result.skipped,
                                result.failed,
                            )
                    await asyncio.to_thread(run_sync)
                except Exception as exc:
                    logger.warning("Official source sync failed error=%s", type(exc).__name__)
                await asyncio.sleep(settings.live_sync_interval_hours * 3600)
        sync_task = asyncio.create_task(scheduled_sync())
    yield
    if sync_task:
        sync_task.cancel()
        with suppress(asyncio.CancelledError):
            await sync_task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Citizen-focused government scheme discovery, provisional eligibility and grievance drafting. "
        "All eligibility output is provisional and must be verified on official portals."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.api_docs_enabled else None,
    redoc_url="/redoc" if settings.api_docs_enabled else None,
)
app.state.services = ServiceContainer(settings)
app.state.rate_limiter = SlidingWindowRateLimiter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    content_length = request.headers.get("content-length")
    if content_length and (not content_length.isdigit() or int(content_length) > settings.max_request_bytes):
        response = JSONResponse(status_code=413, content={"detail": "Request is too large"})
    else:
        response = None

    limits = {
        f"{settings.api_prefix}/chat": settings.chat_rate_limit_per_minute,
        f"{settings.api_prefix}/grievances/draft": settings.grievance_rate_limit_per_minute,
        f"{settings.api_prefix}/auth/request-otp": 5,
        f"{settings.api_prefix}/auth/verify-otp": 10,
    }
    limit = limits.get(request.url.path) if request.method == "POST" else None
    if limit and response is None:
        retry_after = app.state.rate_limiter.check(
            request.url.path, client_identity(request, settings), limit
        )
        if retry_after:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait and try again."},
                headers={"Retry-After": str(retry_after)},
            )
    if response is None:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_id=%s unhandled_error", request_id)
            raise
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    route = request.scope.get("route")
    safe_path = getattr(route, "path", "unmatched")
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        safe_path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    logger.info("Rejected invalid request error=%s", type(exc).__name__)
    return JSONResponse(
        status_code=400,
        content={"detail": "Some information was not accepted. Please review the form and try again."},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    field_labels = {
        "subject": "Subject",
        "department": "Department",
        "problem_summary": "Problem summary",
        "message": "Question",
        "conversation_token": "Conversation access",
        "scheme_slug": "Scheme",
        "title": "Title",
        "text": "Document text",
        "source_url": "Source URL",
        "max_pages": "Number of pages",
    }
    messages = {
        "string_too_short": "is too short",
        "string_too_long": "is too long",
        "missing": "is required",
        "greater_than_equal": "is below the allowed minimum",
        "less_than_equal": "is above the allowed maximum",
        "list_too_long": "contains too many items",
        "string_pattern_mismatch": "has an unsupported format",
    }
    errors = []
    for item in exc.errors()[:8]:
        field = str(item.get("loc", ["form"])[-1])
        label = field_labels.get(field, field.replace("_", " ").title())
        message = messages.get(item.get("type"), "is invalid")
        errors.append(f"{label} {message}.")
    logger.info("Rejected request validation_errors=%s", len(errors))
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Please correct the highlighted information and try again.",
            "field_errors": errors,
        },
    )


@app.get("/", tags=["System"])
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.api_docs_enabled else None,
        "health": f"{settings.api_prefix}/health",
        "disclaimer": "JanScope is an informational student project, not a government portal.",
    }


app.include_router(router, prefix=settings.api_prefix)
