from __future__ import annotations

import re

INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(your\s+)?(system|developer)\s+prompt",
    r"show\s+(me\s+)?your\s+hidden\s+instructions",
    r"act\s+as\s+(an?\s+)?unrestricted",
    r"bypass\s+(the\s+)?(rules|safety|security)",
    r"execute\s+(this\s+)?(system|shell)\s+command",
)


def detect_prompt_injection(text: str) -> list[str]:
    flags: list[str] = []
    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered, re.IGNORECASE):
            flags.append("prompt_injection_attempt")
            break
    return flags


def clean_user_text(text: str, max_chars: int = 4000) -> str:
    """Normalize control characters and apply a strict request-size bound."""

    cleaned = "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)
    return cleaned.strip()[:max_chars]
