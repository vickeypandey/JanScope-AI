from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import GrievanceDraft
from app.schemas.models import GrievanceDraftRequest, GrievanceDraftResponse
from app.services.llm_service import LLMService


class GrievanceService:
    def __init__(self, settings: Settings, llm: LLMService):
        self.settings = settings
        self.llm = llm

    def draft(
        self, db: Session, request: GrievanceDraftRequest, user_id: str | None = None
    ) -> GrievanceDraftResponse:
        missing = [
            label
            for label, value in (
                ("applicant_name", request.applicant_name),
                ("address", request.address),
                ("relevant_dates", request.relevant_dates),
                ("requested_resolution", request.requested_resolution),
            )
            if not value
        ]
        generated = self._ai_draft(request) if self.llm.available else None
        draft = generated or self._template_draft(request)
        draft_id = str(uuid.uuid4())
        db.add(
            GrievanceDraft(
                id=draft_id,
                user_id=user_id or self.settings.demo_user_id,
                subject=request.subject,
                department=request.department,
                draft_text=draft,
                language=request.language,
            )
        )
        db.commit()
        return GrievanceDraftResponse(
            draft_id=draft_id,
            draft=draft,
            missing_information=missing,
            ai_mode="gemini" if generated else "demo",
        )

    def _ai_draft(self, request: GrievanceDraftRequest) -> str | None:
        facts = request.model_dump_json(indent=2)
        language_instruction = "Hindi" if request.language == "hi" else "simple formal English"
        prompt = (
            f"Draft a grievance in {language_instruction} using only the facts below. "
            "Use placeholders in square brackets for missing facts. Do not invent names, dates, laws, "
            f"reference numbers, accusations, or outcomes.\n\nFacts:\n{facts}"
        )
        return self.llm.generate_text(
            prompt,
            system_instruction=(
                "You draft neutral citizen grievances. You never submit them and never add unsupported facts."
            ),
            temperature=0.1,
        )

    @staticmethod
    def _template_draft(request: GrievanceDraftRequest) -> str:
        if request.language == "hi":
            return (
                f"विषय: {request.subject}\n\nसेवा में,\n{request.department}\n\n"
                f"आवेदक का नाम: {request.applicant_name or '[अपना नाम लिखें]'}\n"
                f"पता: {request.address or '[पूरा पता लिखें]'}\n\nमहोदय/महोदया,\n\n"
                f"मैं निम्न समस्या आपके संज्ञान में लाना चाहता/चाहती हूँ:\n{request.problem_summary}\n\n"
                f"संबंधित तिथियाँ: {request.relevant_dates or '[तिथियाँ सत्यापित करके लिखें]'}\n"
                f"पहले की गई कार्रवाई: {request.previous_action or '[यदि कोई हो तो लिखें]'}\n\n"
                f"अनुरोधित समाधान: {request.requested_resolution or '[अपेक्षित समाधान लिखें]'}\n\n"
                f"संलग्नक: {', '.join(request.attachments) if request.attachments else '[संलग्न दस्तावेज़ लिखें]'}\n\n"
                "भवदीय,\n[हस्ताक्षर]\n[दिनांक]\n\n"
                "समीक्षा नोट: जमा करने से पहले प्रत्येक तथ्य और व्यक्तिगत विवरण जाँचें।"
            )
        return (
            f"Subject: {request.subject}\n\nTo,\n{request.department}\n\n"
            f"Applicant: {request.applicant_name or '[Enter full name]'}\n"
            f"Address: {request.address or '[Enter complete address]'}\n\nSir/Madam,\n\n"
            f"I wish to bring the following matter to your attention:\n{request.problem_summary}\n\n"
            f"Relevant dates: {request.relevant_dates or '[Add verified dates]'}\n"
            f"Previous action taken: {request.previous_action or '[Add previous action, if any]'}\n\n"
            f"Requested resolution: {request.requested_resolution or '[State the requested resolution]'}\n\n"
            f"Attachments: {', '.join(request.attachments) if request.attachments else '[List supporting documents]'}\n\n"
            "Yours faithfully,\n[Signature]\n[Date]\n\n"
            "Review note: Verify every fact and personal detail before submission."
        )
