from __future__ import annotations

import json

from app.db.models import Scheme
from app.schemas.models import CitizenProfile, EligibilityResult


def _list(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _matches(value: str, options: list[str]) -> bool:
    value_norm = value.casefold().strip()
    return any(
        value_norm == option.casefold().strip()
        or value_norm in option.casefold().strip()
        or option.casefold().strip() in value_norm
        for option in options
    )


class EligibilityService:
    """Deterministic, explainable checks over the machine-readable rule subset."""

    def evaluate(self, profile: CitizenProfile, scheme: Scheme) -> EligibilityResult:
        matched: list[str] = []
        failed: list[str] = []
        missing: list[str] = []

        states = _list(scheme.states_json)
        state_specific = states and not any(item.casefold() == "all india" for item in states)
        if state_specific:
            if not profile.state:
                missing.append("state")
            elif _matches(profile.state, states):
                matched.append(f"State requirement satisfied ({profile.state})")
            else:
                failed.append(f"Scheme is available in {', '.join(states)}, not {profile.state}")
        elif states:
            matched.append("Scheme is available across India")

        if scheme.min_age is not None or scheme.max_age is not None:
            if profile.age is None:
                missing.append("age")
            else:
                if scheme.min_age is not None and profile.age < scheme.min_age:
                    failed.append(f"Minimum age is {scheme.min_age}")
                elif scheme.max_age is not None and profile.age > scheme.max_age:
                    failed.append(f"Maximum entry age is {scheme.max_age}")
                else:
                    matched.append("Age requirement satisfied")

        if scheme.max_annual_income is not None:
            if profile.annual_income is None:
                missing.append("annual_income")
            elif profile.annual_income <= scheme.max_annual_income:
                matched.append("Income requirement satisfied")
            else:
                failed.append(f"Annual income exceeds ₹{scheme.max_annual_income:,.0f}")

        occupations = _list(scheme.occupations_json)
        if occupations:
            if not profile.occupation:
                missing.append("occupation")
            elif _matches(profile.occupation, occupations):
                matched.append("Occupation requirement satisfied")
            else:
                failed.append("Occupation does not match the encoded scheme occupations")

        genders = _list(scheme.genders_json)
        categories = _list(scheme.categories_json)
        if scheme.slug == "stand-up-india":
            gender_ok = bool(profile.gender and _matches(profile.gender, genders))
            category_ok = bool(profile.category and _matches(profile.category, categories))
            if gender_ok or category_ok:
                matched.append("Woman or SC/ST promoter condition satisfied")
            elif profile.gender is None and profile.category is None:
                missing.extend(["gender", "category"])
            else:
                failed.append("Encoded promoter condition requires a woman or SC/ST entrepreneur")
        else:
            if genders:
                if not profile.gender:
                    missing.append("gender")
                elif _matches(profile.gender, genders):
                    matched.append("Gender requirement satisfied")
                else:
                    failed.append("Gender requirement not satisfied")
            if categories:
                if not profile.category:
                    missing.append("category")
                elif _matches(profile.category, categories):
                    matched.append("Category requirement satisfied")
                else:
                    failed.append("Category requirement not satisfied")

        education = _list(scheme.education_json)
        if education:
            if not profile.education:
                missing.append("education")
            elif _matches(profile.education, education):
                matched.append("Education level matches this opportunity group")
            else:
                failed.append("Education level does not match the encoded opportunity group")

        missing = list(dict.fromkeys(missing))
        denominator = max(len(matched) + len(failed) + len(missing), 1)
        score = round(100 * len(matched) / denominator)
        if failed:
            status = "not_eligible"
        elif missing:
            status = "potentially_eligible"
        else:
            status = "eligible"
        return EligibilityResult(
            scheme_id=scheme.id,
            scheme_slug=scheme.slug,
            scheme_name=scheme.name,
            status=status,
            score=score,
            matched_rules=matched,
            failed_rules=failed,
            missing_information=missing,
            official_url=scheme.official_url,
        )

    def evaluate_many(self, profile: CitizenProfile, schemes: list[Scheme]) -> list[EligibilityResult]:
        order = {"eligible": 0, "potentially_eligible": 1, "not_eligible": 2}
        results = [self.evaluate(profile, scheme) for scheme in schemes]
        return sorted(results, key=lambda item: (order[item.status], -item.score, item.scheme_name))
