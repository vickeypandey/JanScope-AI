from __future__ import annotations

import re

HINGLISH_MARKERS = {
    "mera",
    "meri",
    "mere",
    "mujhe",
    "kya",
    "kaun",
    "kaunsi",
    "yojana",
    "scheme",
    "pita",
    "mata",
    "saal",
    "kisan",
    "madad",
    "chahiye",
    "hai",
    "hain",
    "bihar se",
}


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    lowered = text.casefold()
    hits = sum(1 for marker in HINGLISH_MARKERS if marker in lowered)
    return "hi-en" if hits >= 2 else "en"


def is_hindi_like(language: str) -> bool:
    return language in {"hi", "hi-en"}
