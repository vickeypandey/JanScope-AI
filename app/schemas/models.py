from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CitizenProfile(BaseModel):
    age: int | None = Field(default=None, ge=0, le=125)
    annual_income: float | None = Field(default=None, ge=0)
    state: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=100)
    gender: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=50)
    education: str | None = Field(default=None, max_length=100)

    @field_validator("state", "occupation", "gender", "category", "education")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    def supplied_fields(self) -> set[str]:
        return {key for key, value in self.model_dump().items() if value is not None}


class ProfileExtractionRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    existing_profile: CitizenProfile | None = None


class ProfileExtractionResponse(BaseModel):
    profile: CitizenProfile
    extracted_fields: list[str]
    missing_information: list[str]
    language: str
    method: Literal["rules", "gemini", "rules_with_gemini"]


class SchemeSummary(BaseModel):
    id: int
    slug: str
    name: str
    short_name: str
    description: str
    category: str
    level: str
    states: list[str]
    benefits: str
    official_url: str
    last_verified: str

    model_config = ConfigDict(from_attributes=True)


class SchemeDetail(SchemeSummary):
    min_age: int | None = None
    max_age: int | None = None
    max_annual_income: float | None = None
    occupations: list[str] = []
    genders: list[str] = []
    categories: list[str] = []
    education: list[str] = []
    application_steps: list[str] = []
    required_documents: list[str] = []
    source_excerpt: str = ""


class EligibilityRequest(BaseModel):
    profile: CitizenProfile
    scheme_slug: str | None = None


class EligibilityResult(BaseModel):
    scheme_id: int
    scheme_slug: str
    scheme_name: str
    status: Literal["eligible", "potentially_eligible", "not_eligible"]
    score: int = Field(ge=0, le=100)
    matched_rules: list[str]
    failed_rules: list[str]
    missing_information: list[str]
    official_url: str
    disclaimer: str = (
        "This is a provisional, machine-assisted assessment. Verify eligibility on the official portal."
    )


class EligibilityResponse(BaseModel):
    results: list[EligibilityResult]
    profile: CitizenProfile


class SourceCitation(BaseModel):
    number: int
    scheme_name: str
    title: str
    url: str
    excerpt: str
    last_verified: str = ""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    profile: CitizenProfile | None = None
    language: Literal["auto", "en", "hi", "hi-en"] = "auto"
    conversation_token: str | None = Field(default=None, min_length=64, max_length=64)


class ChatResponse(BaseModel):
    conversation_id: str
    conversation_token: str
    intent: str
    answer: str
    language: str
    profile: CitizenProfile
    needs_clarification: bool = False
    clarification_question: str | None = None
    recommended_schemes: list[SchemeSummary] = []
    eligibility: list[EligibilityResult] = []
    sources: list[SourceCitation] = []
    workflow_steps: list[str] = []
    safety_flags: list[str] = []
    ai_mode: Literal["demo", "gemini"] = "demo"


class IngestDocumentRequest(BaseModel):
    scheme_slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=3, max_length=250)
    text: str = Field(min_length=20, max_length=120000)
    source_url: str


class IngestDocumentResponse(BaseModel):
    scheme_slug: str
    chunks_created: int
    vector_backend: str


class OfficialSourceSyncRequest(BaseModel):
    max_pages: int = Field(default=25, ge=1, le=250)


class OfficialSourceSyncResponse(BaseModel):
    discovered: int
    attempted: int
    imported: int
    skipped: int
    failed: int
    source: str


class GrievanceDraftRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=250)
    department: str = Field(min_length=2, max_length=250)
    applicant_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=500)
    problem_summary: str = Field(min_length=10, max_length=4000)
    relevant_dates: str | None = Field(default=None, max_length=1000)
    previous_action: str | None = Field(default=None, max_length=2000)
    requested_resolution: str | None = Field(default=None, max_length=2000)
    attachments: list[str] = Field(default_factory=list, max_length=10)
    language: Literal["en", "hi"] = "en"


class GrievanceDraftResponse(BaseModel):
    draft_id: str
    draft: str
    missing_information: list[str]
    review_required: bool = True
    warning: str = "Verify every fact and personal detail before submitting this draft."
    ai_mode: Literal["demo", "gemini"] = "demo"


class MessageView(BaseModel):
    role: str
    content: str
    intent: str
    sources: list[dict[str, Any]]
    created_at: datetime


class ConversationView(BaseModel):
    id: str
    language: str
    profile: CitizenProfile
    summary: str
    messages: list[MessageView]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    ai_mode: Literal["demo", "gemini"]
    vector_backend: str
    database: str


class ErrorResponse(BaseModel):
    detail: str


class OtpRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    purpose: Literal["login", "register"]


class OtpRequestResponse(BaseModel):
    challenge_id: str
    message: str
    development_code: str | None = None


class OtpVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=36, max_length=36)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class AuthSessionResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    email: str
