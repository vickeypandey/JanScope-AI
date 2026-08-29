from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import require_admin, require_source_sync_admin, valid_conversation_token
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.scheme_repository import SchemeRepository, scheme_to_detail, scheme_to_summary
from app.schemas.models import (
    ChatRequest,
    ChatResponse,
    AuthSessionResponse,
    ConversationView,
    EligibilityRequest,
    EligibilityResponse,
    GrievanceDraftRequest,
    GrievanceDraftResponse,
    HealthResponse,
    IngestDocumentRequest,
    IngestDocumentResponse,
    OfficialSourceSyncRequest,
    OfficialSourceSyncResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    ProfileExtractionRequest,
    ProfileExtractionResponse,
    SchemeDetail,
    SchemeSummary,
)
from app.services.container import ServiceContainer

router = APIRouter()


def services(request: Request) -> ServiceContainer:
    return request.app.state.services


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.casefold().startswith("bearer "):
        return header[7:].strip()
    return None


@router.post("/auth/request-otp", response_model=OtpRequestResponse, tags=["Authentication"])
def request_otp(payload: OtpRequest, request: Request, db: Session = Depends(get_db)) -> OtpRequestResponse:
    if not services(request).settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        challenge, development_code = services(request).auth.request_otp(
            db, payload.email, payload.purpose
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Email delivery is temporarily unavailable") from exc
    return OtpRequestResponse(
        challenge_id=challenge.id,
        message="A 6-digit verification code has been sent. It expires soon.",
        development_code=development_code,
    )


@router.post("/auth/verify-otp", response_model=AuthSessionResponse, tags=["Authentication"])
def verify_otp(
    payload: OtpVerifyRequest, request: Request, db: Session = Depends(get_db)
) -> AuthSessionResponse:
    try:
        token, user, seconds = services(request).auth.verify(db, payload.challenge_id, payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AuthSessionResponse(access_token=token, expires_in=seconds, email=user.email)


@router.post("/auth/logout", status_code=204, tags=["Authentication"])
def logout(request: Request, db: Session = Depends(get_db)) -> None:
    token = bearer_token(request)
    if token:
        services(request).auth.revoke(db, token)


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health(request: Request) -> HealthResponse:
    container = services(request)
    settings = container.settings
    return HealthResponse(
        status="healthy",
        app=settings.app_name,
        version=settings.app_version,
        ai_mode="gemini" if container.llm.available else "demo",
        vector_backend=container.retrieval.backend_name,
        database="sqlite" if settings.database_url.startswith("sqlite") else "configured",
    )


@router.get("/schemes", response_model=list[SchemeSummary], tags=["Schemes"])
def list_schemes(
    state: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[SchemeSummary]:
    return [scheme_to_summary(item) for item in SchemeRepository(db).list(state, category)]


@router.get("/schemes/{scheme_slug}", response_model=SchemeDetail, tags=["Schemes"])
def scheme_detail(scheme_slug: str, db: Session = Depends(get_db)) -> SchemeDetail:
    scheme = SchemeRepository(db).get_by_slug(scheme_slug)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme_to_detail(scheme)


@router.post("/profile/extract", response_model=ProfileExtractionResponse, tags=["Citizen Profile"])
def extract_profile(payload: ProfileExtractionRequest, request: Request) -> ProfileExtractionResponse:
    return services(request).profile.extract(payload.message, payload.existing_profile)


@router.post("/eligibility/check", response_model=EligibilityResponse, tags=["Eligibility"])
def check_eligibility(
    payload: EligibilityRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> EligibilityResponse:
    repository = SchemeRepository(db)
    if payload.scheme_slug:
        scheme = repository.get_by_slug(payload.scheme_slug)
        if not scheme:
            raise HTTPException(status_code=404, detail="Scheme not found")
        schemes = [scheme]
    else:
        schemes = repository.list(state=payload.profile.state)
    results = services(request).eligibility.evaluate_many(payload.profile, schemes)
    return EligibilityResponse(results=results, profile=payload.profile)


@router.post(
    "/documents/ingest",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["RAG Documents"],
)
def ingest_document(
    payload: IngestDocumentRequest,
    request: Request,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IngestDocumentResponse:
    scheme = SchemeRepository(db).get_by_slug(payload.scheme_slug)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    count = services(request).retrieval.ingest_document(
        db, scheme, payload.title, payload.text, payload.source_url
    )
    return IngestDocumentResponse(
        scheme_slug=payload.scheme_slug,
        chunks_created=count,
        vector_backend=services(request).retrieval.backend_name,
    )


@router.post(
    "/admin/sources/myscheme/sync",
    response_model=OfficialSourceSyncResponse,
    tags=["Administration"],
)
def sync_myscheme(
    payload: OfficialSourceSyncRequest,
    request: Request,
    _: None = Depends(require_source_sync_admin),
    db: Session = Depends(get_db),
) -> OfficialSourceSyncResponse:
    result = services(request).official_sources.sync_myscheme(db, payload.max_pages)
    return OfficialSourceSyncResponse(
        discovered=result.discovered,
        attempted=result.attempted,
        imported=result.imported,
        skipped=result.skipped,
        failed=result.failed,
        source=result.source,
    )


@router.post(
    "/documents/ingest-file",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["RAG Documents"],
)
async def ingest_document_file(
    request: Request,
    scheme_slug: str = Form(...),
    title: str = Form(..., min_length=3, max_length=250),
    source_url: str = Form(...),
    document: UploadFile = File(...),
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> IngestDocumentResponse:
    container = services(request)
    scheme = SchemeRepository(db).get_by_slug(scheme_slug)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    data = await document.read()
    try:
        text = container.documents.extract(document.filename or "document", document.content_type, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    count = container.retrieval.ingest_document(db, scheme, title, text, source_url)
    return IngestDocumentResponse(
        scheme_slug=scheme_slug,
        chunks_created=count,
        vector_backend=container.retrieval.backend_name,
    )


@router.post("/chat", response_model=ChatResponse, tags=["AI Assistant"])
def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ChatResponse:
    if payload.conversation_id and not valid_conversation_token(
        payload.conversation_id,
        payload.conversation_token,
        services(request).settings.conversation_access_secret,
    ):
        raise HTTPException(status_code=403, detail="Conversation access denied")
    user = services(request).auth.user_for_token(db, bearer_token(request))
    return services(request).workflow.run(db, payload, user.id if user else None)


@router.post("/grievances/draft", response_model=GrievanceDraftResponse, tags=["Grievances"])
def draft_grievance(
    payload: GrievanceDraftRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GrievanceDraftResponse:
    user = services(request).auth.user_for_token(db, bearer_token(request))
    return services(request).grievance.draft(db, payload, user.id if user else None)


@router.get("/conversations/{conversation_id}", response_model=ConversationView, tags=["Conversations"])
def conversation(
    conversation_id: str,
    request: Request,
    x_conversation_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ConversationView:
    if not valid_conversation_token(
        conversation_id, x_conversation_token, services(request).settings.conversation_access_secret
    ):
        raise HTTPException(status_code=403, detail="Conversation access denied")
    repository = ConversationRepository(db)
    item = repository.get(conversation_id)
    if not item:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return repository.to_view(item)
