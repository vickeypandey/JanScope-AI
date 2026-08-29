from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IntentResult:
    intent: str
    confidence: float


class IntentService:
    INTENT_KEYWORDS = {
        "GRIEVANCE_DRAFT": (
            "grievance",
            "complaint",
            "shikayat",
            "शिकायत",
            "draft letter",
            "application letter",
        ),
        "ELIGIBILITY_CHECK": (
            "eligible",
            "eligibility",
            "qualify",
            "पात्र",
            "योग्य",
            "can i get",
            "am i eligible",
        ),
        "APPLICATION_GUIDANCE": (
            "how to apply",
            "apply for",
            "documents required",
            "application steps",
            "आवेदन",
            "कैसे अप्लाई",
        ),
        "SCHEME_SEARCH": (
            "scheme",
            "schemes",
            "yojana",
            "योजना",
            "benefit",
            "support",
            "madad",
            "help me find",
        ),
        "SCHEME_EXPLANATION": ("explain", "what is", "tell me about", "समझाओ", "क्या है"),
    }
    UNSUPPORTED = ("diagnose", "medicine dose", "legal verdict", "stock tip", "password", "hack")
    GREETINGS = ("hi", "hello", "hey", "namaste", "नमस्ते", "good morning", "good evening")

    def classify(self, message: str) -> IntentResult:
        lowered = " ".join(message.casefold().split())
        if lowered in self.GREETINGS or any(lowered.startswith(f"{item} ") for item in self.GREETINGS):
            return IntentResult("GENERAL_GREETING", 0.98)
        if any(keyword in lowered for keyword in self.UNSUPPORTED):
            return IntentResult("UNSUPPORTED", 0.90)
        for intent in ("GRIEVANCE_DRAFT", "ELIGIBILITY_CHECK", "APPLICATION_GUIDANCE"):
            matches = sum(1 for keyword in self.INTENT_KEYWORDS[intent] if keyword in lowered)
            if matches:
                return IntentResult(intent, min(0.72 + 0.08 * matches, 0.96))
        # Specific explanation phrasing wins only after action-oriented intents.
        explanation_hits = sum(
            1 for keyword in self.INTENT_KEYWORDS["SCHEME_EXPLANATION"] if keyword in lowered
        )
        scheme_hits = sum(1 for keyword in self.INTENT_KEYWORDS["SCHEME_SEARCH"] if keyword in lowered)
        if explanation_hits and scheme_hits:
            return IntentResult("SCHEME_EXPLANATION", 0.86)
        if scheme_hits:
            return IntentResult("SCHEME_SEARCH", min(0.72 + 0.06 * scheme_hits, 0.94))
        return IntentResult("SCHEME_SEARCH", 0.46)
