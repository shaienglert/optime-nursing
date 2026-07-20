from __future__ import annotations

from typing import Any


def audit_hallucinations(items: list[dict[str, Any]]) -> dict[str, Any]:
    counters = {
        "FABRICATED_FACILITY": 0,
        "WRONG_LOCATION": 0,
        "WRONG_CARE_CAPABILITY": 0,
        "UNSUPPORTED_MEDICAL_PROFESSIONAL_CLAIM": 0,
        "UNSUPPORTED_AMENITY": 0,
        "STALE_FACT": 0,
        "SOURCE_DOES_NOT_SUPPORT_CLAIM": 0,
        "CITATION_MISSING": 0,
        "OVERCONFIDENT_UNKNOWN": 0,
        "UNVERIFIED": 0,
    }

    for item in items:
        key = str(item.get("type", "UNVERIFIED")).upper()
        if key in counters:
            counters[key] += 1
        else:
            counters["UNVERIFIED"] += 1

    total = sum(counters.values())
    unsupported = (
        counters["UNSUPPORTED_MEDICAL_PROFESSIONAL_CLAIM"]
        + counters["SOURCE_DOES_NOT_SUPPORT_CLAIM"]
        + counters["CITATION_MISSING"]
    )

    return {
        "total_flagged": total,
        "unsupported_factual_claim_rate": unsupported / max(1, total),
        "fabricated_facility_rate": counters["FABRICATED_FACILITY"] / max(1, total),
        "unsupported_professional_claim_rate": counters["UNSUPPORTED_MEDICAL_PROFESSIONAL_CLAIM"] / max(1, total),
        "counts": counters,
    }
