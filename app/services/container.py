from __future__ import annotations

from app.core.config import Settings
from app.services.document_service import DocumentService
from app.services.auth_service import AuthService
from app.services.eligibility_service import EligibilityService
from app.services.grievance_service import GrievanceService
from app.services.intent_service import IntentService
from app.services.llm_service import LLMService
from app.services.official_source_service import OfficialSourceService
from app.services.profile_service import ProfileService
from app.services.retrieval_service import RetrievalService
from app.services.workflow_service import WorkflowService


class ServiceContainer:
    """Explicit service wiring keeps FastAPI routes thin and testable."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth = AuthService(settings)
        self.llm = LLMService(settings)
        self.profile = ProfileService(self.llm)
        self.intent = IntentService()
        self.eligibility = EligibilityService()
        self.documents = DocumentService(settings)
        self.retrieval = RetrievalService(settings)
        self.official_sources = OfficialSourceService(settings, self.retrieval)
        self.grievance = GrievanceService(settings, self.llm)
        self.workflow = WorkflowService(
            settings=settings,
            llm=self.llm,
            profile_service=self.profile,
            intent_service=self.intent,
            eligibility_service=self.eligibility,
            retrieval_service=self.retrieval,
        )
