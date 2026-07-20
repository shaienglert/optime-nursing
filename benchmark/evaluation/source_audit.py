from __future__ import annotations

from datetime import datetime
from typing import Any


SOURCE_ORDER = {
    "GOVERNMENT_REGULATORY": 5,
    "CMS_OFFICIAL_QUALITY_DATA": 5,
    "PROFESSIONAL_CLINICAL_AUTHORITY": 4,
    "FACILITY_SELF_REPORTED": 3,
    "THIRD_PARTY_DIRECTORY": 2,
    "REVIEW_USER_GENERATED": 1,
    "SEARCH_SNIPPET_ONLY": 1,
    "UNKNOWN": 0,
}


def classify_source_type(source: dict[str, Any]) -> str:
    source_type = str(source.get("source_type", "UNKNOWN")).upper()
    if source_type in SOURCE_ORDER:
        return source_type
    return "UNKNOWN"


def freshness_bucket(source_date: str | None, retrieval_date: str | None) -> str:
    if not source_date or not retrieval_date:
        return "UNKNOWN"
    try:
        src = datetime.fromisoformat(source_date.replace("Z", "+00:00"))
        ret = datetime.fromisoformat(retrieval_date.replace("Z", "+00:00"))
        age_days = (ret - src).days
    except ValueError:
        return "UNKNOWN"

    if age_days <= 30:
        return "FRESH"
    if age_days <= 180:
        return "STALE_RISK"
    return "STALE"


def audit_claim_sources(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audited: list[dict[str, Any]] = []
    for claim in claims:
        source = claim.get("source", {})
        source_type = classify_source_type(source)
        support = bool(claim.get("supported_by_source", False))
        audited.append(
            {
                "claim": claim.get("claim"),
                "facility": claim.get("facility"),
                "source_url": source.get("url"),
                "source_type": source_type,
                "source_authority_score": SOURCE_ORDER[source_type],
                "source_date": source.get("source_date"),
                "retrieval_date": source.get("retrieval_date"),
                "freshness": freshness_bucket(source.get("source_date"), source.get("retrieval_date")),
                "supports_claim": support,
                "conflict_status": claim.get("conflict_status", "UNKNOWN"),
            }
        )
    return audited
