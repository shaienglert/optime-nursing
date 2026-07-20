from __future__ import annotations

from typing import Any


def _normalize_name(name: str) -> str:
    cleaned = "".join(ch.lower() for ch in name if ch.isalnum() or ch.isspace())
    return " ".join(cleaned.split())


def resolve_identities(recommended_names: list[str], canonical_facilities: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {_normalize_name(item.get("name", "")): item for item in canonical_facilities}
    matches: list[dict[str, Any]] = []

    for rec_name in recommended_names:
        key = _normalize_name(rec_name)
        if key in lookup:
            item = lookup[key]
            matches.append(
                {
                    "recommended_name": rec_name,
                    "canonical_facility_id": item.get("id"),
                    "canonical_name": item.get("name"),
                    "match_status": "CONFIRMED_MATCH",
                }
            )
            continue

        probable = [value for norm, value in lookup.items() if key and (key in norm or norm in key)]
        if len(probable) == 1:
            matches.append(
                {
                    "recommended_name": rec_name,
                    "canonical_facility_id": probable[0].get("id"),
                    "canonical_name": probable[0].get("name"),
                    "match_status": "PROBABLE_MATCH_REVIEW_REQUIRED",
                }
            )
        elif len(probable) > 1:
            matches.append(
                {
                    "recommended_name": rec_name,
                    "canonical_facility_id": None,
                    "canonical_name": None,
                    "match_status": "AMBIGUOUS",
                }
            )
        else:
            matches.append(
                {
                    "recommended_name": rec_name,
                    "canonical_facility_id": None,
                    "canonical_name": None,
                    "match_status": "NO_MATCH",
                }
            )

    return {
        "matches": matches,
        "summary": {
            "confirmed": sum(1 for m in matches if m["match_status"] == "CONFIRMED_MATCH"),
            "probable_review": sum(1 for m in matches if m["match_status"] == "PROBABLE_MATCH_REVIEW_REQUIRED"),
            "ambiguous": sum(1 for m in matches if m["match_status"] == "AMBIGUOUS"),
            "no_match": sum(1 for m in matches if m["match_status"] == "NO_MATCH"),
        },
    }
