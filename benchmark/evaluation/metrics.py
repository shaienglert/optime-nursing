from __future__ import annotations

from typing import Any


def _as_set(values: list[str]) -> set[str]:
    return {str(v).strip().lower() for v in values if str(v).strip()}


def score_dimensions(case_def: dict[str, Any], normalized: dict[str, Any], source_audit: list[dict[str, Any]], hallucination: dict[str, Any]) -> dict[str, Any]:
    explicit_expected = _as_set(case_def.get("explicit_needs", []))
    explicit_found = _as_set(normalized.get("EXPLICIT_NEEDS", []))

    must_expected = _as_set(case_def.get("explicit_non_negotiables", []))
    must_found = _as_set(normalized.get("MUST_REQUIREMENTS", []))

    unknown_expected = _as_set(case_def.get("known_unknowns", []))
    unknown_found = _as_set(normalized.get("MISSING_INFORMATION", []))

    top5 = normalized.get("TOP_5", [])
    must_failure_rate = 0.0
    must_unknown_transparency = 0.0
    if top5:
        must_failure_rate = sum(1 for item in top5 if item.get("must_failed")) / len(top5)
        must_unknown_transparency = sum(1 for item in top5 if item.get("must_unknown")) / len(top5)

    citation_coverage = sum(1 for row in source_audit if row.get("source_url")) / max(1, len(source_audit))
    citation_correctness = sum(1 for row in source_audit if row.get("supports_claim")) / max(1, len(source_audit))
    official_coverage = sum(
        1
        for row in source_audit
        if row.get("source_type") in {"GOVERNMENT_REGULATORY", "CMS_OFFICIAL_QUALITY_DATA"}
    ) / max(1, len(source_audit))

    invented_certainty = 1.0 if not unknown_found and unknown_expected else 0.0

    return {
        "A_PERSON_UNDERSTANDING": {
            "explicit_need_recall": len(explicit_expected & explicit_found) / max(1, len(explicit_expected)),
            "unsupported_inferred_need_rate": max(0, len(explicit_found - explicit_expected)) / max(1, len(explicit_found)),
            "critical_omission_rate": max(0, len(explicit_expected - explicit_found)) / max(1, len(explicit_expected)),
        },
        "B_MUST_QUALITY": {
            "explicit_must_preservation": len(must_expected & must_found) / max(1, len(must_expected)),
            "unsupported_must_creation": max(0, len(must_found - must_expected)) / max(1, len(must_found)),
            "critical_must_omission": max(0, len(must_expected - must_found)) / max(1, len(must_expected)),
        },
        "C_UNKNOWN_DISCIPLINE": {
            "unknown_preservation": len(unknown_expected & unknown_found) / max(1, len(unknown_expected)),
            "invented_certainty_rate": invented_certainty,
            "appropriate_clarification_rate": len(normalized.get("CLARIFYING_QUESTIONS", [])) / max(1, len(unknown_expected)),
        },
        "D_FACILITY_SELECTION": {
            "valid_facility_rate": 1.0,
            "must_failure_rate": must_failure_rate,
            "must_unknown_transparency": must_unknown_transparency,
            "geographic_fit": 1.0,
        },
        "E_EVIDENCE_QUALITY": {
            "citation_coverage": citation_coverage,
            "official_source_coverage": official_coverage,
            "citation_correctness": citation_correctness,
            "freshness": sum(1 for row in source_audit if row.get("freshness") == "FRESH") / max(1, len(source_audit)),
            "traceability": citation_coverage,
        },
        "F_HALLUCINATION": {
            "unsupported_factual_claim_rate": hallucination.get("unsupported_factual_claim_rate", 0.0),
            "fabricated_facility_rate": hallucination.get("fabricated_facility_rate", 0.0),
            "unsupported_professional_claim_rate": hallucination.get("unsupported_professional_claim_rate", 0.0),
        },
        "G_DECISION_USEFULNESS": {
            "tradeoff_clarity": 1.0 if any(item.get("tradeoffs") for item in top5) else 0.0,
            "actionability": 1.0 if normalized.get("NEXT_STEPS_FOR_FAMILY") else 0.0,
            "explanation_completeness": 1.0 if top5 else 0.0,
            "family_decision_support": 1.0 if normalized.get("UNDERSTOOD_PERSON_PROFILE") else 0.0,
        },
        "H_COMMUNICATION": {
            "clarity": 1.0 if normalized.get("UNDERSTOOD_PERSON_PROFILE") else 0.0,
            "structure": 1.0 if isinstance(normalized, dict) else 0.0,
            "readability": 1.0,
            "excessive_verbosity": 0.0,
            "overconfidence": hallucination.get("counts", {}).get("OVERCONFIDENT_UNKNOWN", 0),
        },
    }
