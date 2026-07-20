from __future__ import annotations

import json
from typing import Any

from benchmark.contracts import NormalizedResponse


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def normalize_raw_response(raw_text: str, raw_json: dict[str, Any] | None) -> dict[str, Any]:
    payload: dict[str, Any] = raw_json or {}
    if not payload:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = {}

    top5 = _safe_list(payload.get("TOP_5") or payload.get("top_5"))
    normalized = NormalizedResponse(
        understood_person_profile=payload.get("UNDERSTOOD_PERSON_PROFILE", {}),
        explicit_needs=_safe_list(payload.get("EXPLICIT_NEEDS")),
        missing_information=_safe_list(payload.get("MISSING_INFORMATION")),
        clarifying_questions=_safe_list(payload.get("CLARIFYING_QUESTIONS")),
        must_requirements=_safe_list(payload.get("MUST_REQUIREMENTS")),
        professional_recommendations=_safe_list(payload.get("PROFESSIONAL_RECOMMENDATIONS")),
        nice_to_have=_safe_list(payload.get("NICE_TO_HAVE")),
        facilities_considered=_safe_list(payload.get("FACILITIES_CONSIDERED")),
        top_5=top5,
        unsupported_or_unverified_claims=_safe_list(payload.get("UNSUPPORTED_OR_UNVERIFIED_CLAIMS")),
        next_steps_for_family=_safe_list(payload.get("NEXT_STEPS_FOR_FAMILY")),
    )

    return {
        "UNDERSTOOD_PERSON_PROFILE": normalized.understood_person_profile,
        "EXPLICIT_NEEDS": normalized.explicit_needs,
        "MISSING_INFORMATION": normalized.missing_information,
        "CLARIFYING_QUESTIONS": normalized.clarifying_questions,
        "MUST_REQUIREMENTS": normalized.must_requirements,
        "PROFESSIONAL_RECOMMENDATIONS": normalized.professional_recommendations,
        "NICE_TO_HAVE": normalized.nice_to_have,
        "FACILITIES_CONSIDERED": normalized.facilities_considered,
        "TOP_5": normalized.top_5,
        "UNSUPPORTED_OR_UNVERIFIED_CLAIMS": normalized.unsupported_or_unverified_claims,
        "NEXT_STEPS_FOR_FAMILY": normalized.next_steps_for_family,
    }
