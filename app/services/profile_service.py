from __future__ import annotations

import re
from typing import Any

from app.schemas.models import CitizenProfile, ProfileExtractionResponse
from app.services.language_service import detect_language
from app.services.llm_service import LLMService

INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Chandigarh",
    "Puducherry",
]

STATE_ALIASES = {
    "jharkhand": "Jharkhand",
    "ranchi": "Jharkhand",
    "bihar": "Bihar",
    "दिल्ली": "Delhi",
    "बिहार": "Bihar",
    "झारखंड": "Jharkhand",
    "राजस्थान": "Rajasthan",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "महाराष्ट्र": "Maharashtra",
    "पंजाब": "Punjab",
}

OCCUPATION_ALIASES = {
    "farmer": "farmer",
    "farming": "farmer",
    "kisan": "farmer",
    "किसान": "farmer",
    "student": "student",
    "छात्र": "student",
    "labourer": "labourer",
    "laborer": "labourer",
    "mazdoor": "labourer",
    "मजदूर": "labourer",
    "street vendor": "street vendor",
    "hawker": "street vendor",
    "artisan": "artisan",
    "कारीगर": "artisan",
    "tailor": "tailor",
    "barber": "barber",
    "carpenter": "carpenter",
    "potter": "potter",
    "entrepreneur": "entrepreneur",
    "business owner": "entrepreneur",
}

CATEGORY_ALIASES = {
    "general": "General",
    "ur": "General",
    "obc": "OBC",
    "sc": "SC",
    "st": "ST",
    "ews": "EWS",
    "अनुसूचित जाति": "SC",
    "अनुसूचित जनजाति": "ST",
}

EDUCATION_ALIASES = {
    "btech": "BTech",
    "b.tech": "BTech",
    "engineering": "BTech",
    "undergraduate": "undergraduate",
    "graduation": "undergraduate",
    "college": "undergraduate",
    "class 12": "class 12",
    "12th": "class 12",
    "postgraduate": "postgraduate",
    "diploma": "diploma",
}


class ProfileService:
    IMPORTANT_FIELDS = ["age", "annual_income", "state", "occupation", "gender", "category", "education"]

    def __init__(self, llm: LLMService):
        self.llm = llm

    def extract(
        self, message: str, existing: CitizenProfile | None = None, use_ai: bool = True
    ) -> ProfileExtractionResponse:
        language = detect_language(message)
        base = (existing or CitizenProfile()).model_dump()
        rules = self._extract_rules(message)
        merged = {**base, **{key: value for key, value in rules.items() if value is not None}}
        method = "rules"

        # Rules already capture common age/state/occupation/income phrasing. Avoid a
        # second provider round-trip when two or more useful fields are known.
        if use_ai and self.llm.available and len(rules) < 2:
            ai_values = self._extract_with_ai(message)
            if ai_values:
                for key, value in ai_values.items():
                    if key in merged and merged.get(key) is None and value not in (None, ""):
                        merged[key] = value
                method = "rules_with_gemini"

        profile = CitizenProfile.model_validate(merged)
        extracted_fields = [key for key in self.IMPORTANT_FIELDS if key in rules and rules[key] is not None]
        missing = [key for key in self.IMPORTANT_FIELDS if getattr(profile, key) is None]
        return ProfileExtractionResponse(
            profile=profile,
            extracted_fields=extracted_fields,
            missing_information=missing,
            language=language,
            method=method,
        )

    def _extract_rules(self, text: str) -> dict[str, Any]:
        lowered = text.casefold()
        result: dict[str, Any] = {}

        age_patterns = (
            r"(?:age(?:\s+is)?|aged)\s*[:=-]?\s*(\d{1,3})",
            r"(\d{1,3})\s*(?:years?\s*old|years?|yrs?|saal|साल|वर्ष)",
        )
        for pattern in age_patterns:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 0 <= age <= 125:
                    result["age"] = age
                    break

        income_patterns = (
            r"(?:annual\s+income|yearly\s+income|income)\s*(?:is|of|=|:)?\s*[₹rs. ]*([\d,]+)(?:\s*(lakh|lac|k))?",
            r"[₹]\s*([\d,]+)(?:\s*(lakh|lac|k))?",
            r"([\d,.]+)\s*(lakh|lac)\s*(?:per\s+year|yearly|annual|income)",
        )
        for pattern in income_patterns:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match:
                raw = float(match.group(1).replace(",", ""))
                unit = (match.group(2) or "").lower() if match.lastindex and match.lastindex >= 2 else ""
                if unit in {"lakh", "lac"}:
                    raw *= 100000
                elif unit == "k":
                    raw *= 1000
                result["annual_income"] = raw
                break

        for alias, canonical in STATE_ALIASES.items():
            if alias.casefold() in lowered:
                result["state"] = canonical
                break
        if "state" not in result:
            for state in INDIAN_STATES:
                if state.casefold() in lowered:
                    result["state"] = state
                    break

        for alias, canonical in sorted(OCCUPATION_ALIASES.items(), key=lambda item: -len(item[0])):
            if alias.casefold() in lowered:
                result["occupation"] = canonical
                break

        if re.search(r"\b(female|woman|girl|mahila)\b|महिला|लड़की", lowered):
            result["gender"] = "female"
        elif re.search(r"\b(male|man|boy|purush)\b|पुरुष|लड़का", lowered):
            result["gender"] = "male"

        for alias, canonical in CATEGORY_ALIASES.items():
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered, re.IGNORECASE):
                result["category"] = canonical
                break

        for alias, canonical in EDUCATION_ALIASES.items():
            if alias in lowered:
                result["education"] = canonical
                break
        return result

    def _extract_with_ai(self, message: str) -> dict[str, Any] | None:
        schema = {field: None for field in self.IMPORTANT_FIELDS}
        prompt = (
            "Extract only explicitly stated citizen attributes from the message. "
            "Do not infer caste, gender, income, age, education, occupation, or state. "
            f"Message: {message}"
        )
        return self.llm.generate_json(
            prompt,
            system_instruction="You are a precise Indian citizen-profile extraction component.",
            schema_hint=schema,
        )
