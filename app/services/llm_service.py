from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMService:
    """Small provider boundary around the official Google GenAI SDK.

    The rest of JanScope does not import a provider SDK, so Gemini can be
    replaced later without rewriting the domain services.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._types = None
        if settings.effective_ai_enabled:
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options=types.HttpOptions(
                        timeout=settings.gemini_request_timeout_seconds * 1000,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                )
                self._types = types
            except Exception as exc:  # pragma: no cover - depends on optional runtime
                logger.warning("Gemini SDK unavailable; using demo mode: %s", type(exc).__name__)

    @property
    def available(self) -> bool:
        return self._client is not None and self._types is not None

    @property
    def mode(self) -> str:
        return "gemini" if self.available else "demo"

    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str | None:
        if not self.available:
            return None
        try:
            config = self._types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=self.settings.gemini_temperature if temperature is None else temperature,
                max_output_tokens=max_output_tokens or self.settings.gemini_max_output_tokens,
            )
            response = self._client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=config,
            )
            text = getattr(response, "text", None)
            return text.strip() if text else None
        except Exception as exc:  # pragma: no cover - requires live API
            logger.error("Gemini request failed: %s", type(exc).__name__)
            return None

    def generate_json(
        self, prompt: str, *, system_instruction: str, schema_hint: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not self.available:
            return None
        full_prompt = (
            f"{prompt}\n\nReturn only valid JSON matching this shape:\n"
            f"{json.dumps(schema_hint, ensure_ascii=False)}"
        )
        try:
            config = self._types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                max_output_tokens=900,
                response_mime_type="application/json",
            )
            response = self._client.models.generate_content(
                model=self.settings.gemini_model,
                contents=full_prompt,
                config=config,
            )
            raw = (getattr(response, "text", "") or "").strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception as exc:  # pragma: no cover - requires live API
            logger.error("Gemini JSON request failed: %s", type(exc).__name__)
            return None
