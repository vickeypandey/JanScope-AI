from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-driven application settings.

    All defaults are safe for a local student demo. Secrets belong in `.env`,
    which is ignored by Git.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "JanScope AI"
    app_version: str = "1.0.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_port: int = 8501
    frontend_url: str = "http://127.0.0.1:8501"

    database_url: str = f"sqlite:///{(PROJECT_ROOT / 'data' / 'janscope.db').as_posix()}"
    sample_data_path: Path = PROJECT_ROOT / "data" / "schemes.json"
    sample_documents_path: Path = PROJECT_ROOT / "sample_documents"
    seed_sample_data: bool = False
    chroma_path: Path = PROJECT_ROOT / "data" / "chroma"
    vector_collection: str = "janscope_scheme_documents"
    vector_backend: str = "chroma"
    embedding_dimensions: int = 384
    retrieval_top_k: int = Field(default=4, ge=1, le=10)

    ai_enabled: bool = False
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.7-flash"
    gemini_temperature: float = Field(default=0.15, ge=0.0, le=1.0)
    gemini_max_output_tokens: int = Field(default=1400, ge=128, le=8192)
    gemini_request_timeout_seconds: int = Field(default=12, ge=3, le=40)

    log_level: str = "INFO"
    demo_user_id: str = "demo-user"
    allow_origins: str = "http://127.0.0.1:8501,http://localhost:8501"
    max_user_message_chars: int = 4000
    max_document_chars: int = 120000
    max_request_bytes: int = Field(default=131072, ge=1024, le=10_000_000)
    chat_rate_limit_per_minute: int = Field(default=10, ge=1, le=1000)
    grievance_rate_limit_per_minute: int = Field(default=3, ge=1, le=1000)
    trust_proxy_headers: bool = False
    ingestion_enabled: bool = False
    admin_api_key: str = ""
    conversation_access_secret: str = "development-only-change-me"
    project_github_url: str = ""
    api_docs_enabled: bool = True
    live_source_sync_enabled: bool = False
    live_sync_interval_hours: int = Field(default=24, ge=1, le=720)
    live_sync_max_pages: int = Field(default=25, ge=1, le=250)
    official_fetch_timeout_seconds: int = Field(default=15, ge=5, le=60)
    official_fetch_delay_seconds: float = Field(default=0.25, ge=0.0, le=5.0)
    official_source_domains_csv: str = "myscheme.gov.in,india.gov.in"
    official_bootstrap_urls_csv: str = "https://www.myscheme.gov.in/schemes/aaby"
    myscheme_public_api_key: str = ""
    auth_enabled: bool = True
    otp_delivery_mode: str = "development"
    otp_secret: str = "development-only-otp-secret-change-me"
    otp_expiry_minutes: int = Field(default=10, ge=2, le=30)
    otp_max_attempts: int = Field(default=5, ge=3, le=10)
    auth_session_days: int = Field(default=7, ge=1, le=30)
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    brevo_api_key: str = ""

    @property
    def official_source_domains(self) -> list[str]:
        return [item.strip().casefold() for item in self.official_source_domains_csv.split(",") if item.strip()]

    @property
    def official_bootstrap_urls(self) -> list[str]:
        return [item.strip() for item in self.official_bootstrap_urls_csv.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate_production(self) -> None:
        if not self.is_production:
            return
        errors = []
        if len(self.conversation_access_secret) < 32 or self.conversation_access_secret == "development-only-change-me":
            errors.append("CONVERSATION_ACCESS_SECRET must be a unique value of at least 32 characters")
        if (self.ingestion_enabled or self.live_source_sync_enabled) and len(self.admin_api_key) < 24:
            errors.append("ADMIN_API_KEY must contain at least 24 characters when ingestion or live sync is enabled")
        if "localhost" in self.allow_origins or "127.0.0.1" in self.allow_origins:
            errors.append("ALLOW_ORIGINS must contain only the deployed frontend origin")
        if self.auth_enabled:
            if self.otp_delivery_mode not in {"smtp", "brevo_api"}:
                errors.append("OTP_DELIVERY_MODE must be smtp or brevo_api in production")
            if len(self.otp_secret) < 32 or "development-only" in self.otp_secret:
                errors.append("OTP_SECRET must be a unique value of at least 32 characters")
            if self.otp_delivery_mode == "smtp" and not all(
                (self.smtp_host, self.smtp_username, self.smtp_password, self.smtp_from_email)
            ):
                errors.append("SMTP settings are required when OTP_DELIVERY_MODE is smtp")
            if self.otp_delivery_mode == "brevo_api" and not all(
                (self.brevo_api_key, self.smtp_from_email)
            ):
                errors.append("BREVO_API_KEY and SMTP_FROM_EMAIL are required for Brevo API delivery")
        if errors:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allow_origins.split(",") if item.strip()]

    @property
    def effective_ai_enabled(self) -> bool:
        return self.ai_enabled and bool(self.gemini_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
