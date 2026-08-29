from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Conversation, Message
from app.schemas.models import CitizenProfile, ConversationView, MessageView


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(
        self, conversation_id: str | None, user_id: str, language: str, profile: CitizenProfile
    ) -> Conversation:
        conversation = self.get(conversation_id) if conversation_id else None
        if conversation is None:
            conversation = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                language=language,
                profile_json=profile.model_dump_json(),
            )
            self.db.add(conversation)
            self.db.flush()
        return conversation

    def get(self, conversation_id: str | None) -> Conversation | None:
        if not conversation_id:
            return None
        return self.db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )

    def update_profile(self, conversation: Conversation, profile: CitizenProfile, language: str) -> None:
        conversation.profile_json = profile.model_dump_json()
        conversation.language = language

    def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        intent: str = "",
        sources: list[dict] | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            intent=intent,
            sources_json=json.dumps(sources or [], ensure_ascii=False),
        )
        self.db.add(message)
        self.db.flush()
        return message

    def recent_messages(self, conversation: Conversation, limit: int = 8) -> list[dict[str, str]]:
        items = conversation.messages[-limit:]
        return [{"role": item.role, "content": item.content} for item in items]

    def to_view(self, conversation: Conversation) -> ConversationView:
        try:
            profile = CitizenProfile.model_validate_json(conversation.profile_json)
        except Exception:
            profile = CitizenProfile()
        return ConversationView(
            id=conversation.id,
            language=conversation.language,
            profile=profile,
            summary=conversation.summary,
            messages=[
                MessageView(
                    role=item.role,
                    content=item.content,
                    intent=item.intent,
                    sources=json.loads(item.sources_json or "[]"),
                    created_at=item.created_at,
                )
                for item in conversation.messages
            ],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
