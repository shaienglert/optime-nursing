from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from app.services.patient_decision_engine import run_patient_decision_engine


FIXTURE_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "realistic_synthetic_facilities.json"
KNOWN_STATES = {
    "GOVERNMENT_VERIFIED",
    "FACILITY_DOCUMENTED",
    "FACILITY_CLAIMED",
    "THIRD_PARTY_DOCUMENTED",
    "PROXY_SUPPORTED",
    "STALE_OFFICIAL",
    "CONTRADICTED",
    "NOT_APPLICABLE",
}
ALLOWED_STATES = KNOWN_STATES | {"UNKNOWN"}


def load_synthetic_dataset(path: Path = FIXTURE_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _missing_reasons(facility: Dict[str, Any]) -> Dict[str, str]:
    reasons: Dict[str, str] = {}
    for group in facility.get("missing_source_coverage", []):
        for parameter_id in group.get("parameter_ids", []):
            reasons[parameter_id] = str(group.get("reason") or "")
    return reasons


def validate_synthetic_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    parameters = dataset.get("decision_critical_parameter_ids") or []
    parameter_set = set(parameters)
    facilities = dataset.get("facilities") or []
    coverage_rows = []
    signatures = set()
    contradiction_count = 0
    source_states = set()

    if dataset.get("synthetic_only") is not True:
        errors.append("Dataset must be explicitly marked synthetic_only.")
    if len(parameters) != len(parameter_set):
        errors.append("Decision-critical parameter IDs must be unique.")
    if len(facilities) != 10:
        errors.append("Dataset must contain exactly ten facilities.")

    for facility in facilities:
        facility_id = facility.get("facility_id")
        evidence = facility.get("evidence") or []
        by_parameter = {row.get("parameter_id"): row for row in evidence if row.get("parameter_id") in parameter_set}
        missing = _missing_reasons(facility)
        not_applicable = {row.get("parameter_id"): row for row in facility.get("not_applicable", [])}
        signatures.add(tuple(sorted(by_parameter)))

        overlap = set(by_parameter) & set(missing)
        if overlap:
            errors.append(f"{facility_id}: parameters cannot be both evidenced and missing: {sorted(overlap)}")

        accounted_for = set(by_parameter) | set(missing) | set(not_applicable)
        unaccounted = parameter_set - accounted_for
        if unaccounted:
            errors.append(f"{facility_id}: missing reasons for {sorted(unaccounted)}")

        for parameter_id, reason in missing.items():
            if parameter_id not in parameter_set:
                errors.append(f"{facility_id}: unknown missing parameter {parameter_id}")
            if not reason:
                errors.append(f"{facility_id}: missing source reason required for {parameter_id}")

        for row in evidence:
            state = str(row.get("evidence_state") or "")
            source_states.add(state)
            if state not in ALLOWED_STATES:
                errors.append(f"{facility_id}: unsupported evidence state {state}")
            if state == "UNKNOWN" and not row.get("unknown_reason"):
                errors.append(f"{facility_id}: UNKNOWN reason required for {row.get('parameter_id')}")
            if state in {"CONTRADICTED", "STALE_OFFICIAL", "NOT_APPLICABLE"} and not row.get("state_reason"):
                errors.append(f"{facility_id}: state reason required for {row.get('parameter_id')} ({state})")
            if state == "CONTRADICTED":
                contradiction_count += 1

        for row in facility.get("not_applicable", []):
            parameter_id = row.get("parameter_id")
            if parameter_id in by_parameter or parameter_id in missing:
                errors.append(f"{facility_id}: {parameter_id} has overlapping NOT_APPLICABLE coverage")
            if not row.get("reason"):
                errors.append(f"{facility_id}: NOT_APPLICABLE reason required for {parameter_id}")

        known_count = sum(1 for row in by_parameter.values() if row.get("evidence_state") in KNOWN_STATES)
        known_count += len(not_applicable)
        coverage_pct = round((known_count / len(parameters)) * 100, 1)
        lower, upper = facility.get("target_coverage_range_pct", [0, 100])
        if not lower <= coverage_pct <= upper:
            errors.append(f"{facility_id}: coverage {coverage_pct}% outside target {lower}-{upper}%")
        if len(by_parameter) + len(not_applicable) >= len(parameters):
            errors.append(f"{facility_id}: fixture must retain at least one omitted parameter")
        coverage_rows.append({
            "facility_id": facility_id,
            "facility_name": facility.get("facility_name"),
            "coverage_pct": coverage_pct,
            "known_count": known_count,
            "unknown_count": sum(1 for row in by_parameter.values() if row.get("evidence_state") == "UNKNOWN"),
            "missing_count": len(missing),
            "stale_count": sum(1 for row in by_parameter.values() if row.get("evidence_state") == "STALE_OFFICIAL"),
            "contradiction_count": sum(1 for row in by_parameter.values() if row.get("evidence_state") == "CONTRADICTED"),
            "not_applicable_count": len(not_applicable) + sum(1 for row in by_parameter.values() if row.get("evidence_state") == "NOT_APPLICABLE"),
        })

    if len(signatures) != len(facilities):
        errors.append("Every facility must have a distinct parameter-coverage signature.")
    if contradiction_count < 3:
        errors.append("At least three contradiction scenarios are required.")
    missing_states = ALLOWED_STATES - source_states
    if missing_states:
        errors.append(f"Dataset is missing required evidence states: {sorted(missing_states)}")

    return {
        "valid": not errors,
        "errors": errors,
        "facility_coverage": coverage_rows,
        "contradiction_count": contradiction_count,
        "evidence_states": sorted(source_states),
    }


def _table_for(facility: Dict[str, Any]) -> Dict[str, Any]:
    rows = list(facility.get("evidence") or [])
    for parameter_id, reason in _missing_reasons(facility).items():
        rows.append({
            "parameter_id": parameter_id,
            "raw_value": "UNKNOWN",
            "evidence_state": "UNKNOWN",
            "source": "No source coverage",
            "unknown_reason": reason,
            "detail_scope": "FACILITY",
        })
    for item in facility.get("not_applicable", []):
        rows.append({
            "parameter_id": item["parameter_id"],
            "raw_value": "NOT_APPLICABLE",
            "evidence_state": "NOT_APPLICABLE",
            "source": "Synthetic facility scope",
            "state_reason": item["reason"],
            "detail_scope": "PROGRAM",
        })
    return {
        "canonical_facility_id": facility["facility_id"],
        "facility_name": facility["facility_name"],
        "city": facility["city"],
        "state": "FL",
        "county": "MIAMI-DADE",
        "zip": "33100",
        "canonical_type": facility["canonical_type"],
        "role_classification": facility["canonical_type"],
        "rows": rows,
    }


def run_synthetic_decision_simulation(dataset: Dict[str, Any]) -> Dict[str, Any]:
    validation = validate_synthetic_dataset(dataset)
    if not validation["valid"]:
        raise ValueError("Invalid synthetic dataset: " + "; ".join(validation["errors"]))

    facilities = dataset["facilities"]
    by_id = {facility["facility_id"]: facility for facility in facilities}
    parameter_ids = list(dataset["decision_critical_parameter_ids"])
    parameter_ids.extend(["sanctions_final_orders", "deficiency_count", "deficiency_severity"])
    ordered_parameters = [
        {"parameter_id": parameter_id, "family": "SIMULATION", "display_name": parameter_id, "applicable_scope": "FACILITY"}
        for parameter_id in parameter_ids
    ]

    questionnaire = {
        "assistanceLevel": "Bathing and dressing assistance",
        "budget": 7000,
        "paymentMethod": ["PRIVATE_PAY"],
        "memoryStatus": "No current concerns",
        "humanIntelligenceV2": {
            "foodProfile": {"dietaryPreferences": ["Medically required gluten-free"]},
            "transitionRiskProfile": {"postHospitalRehabNeed": "yes"},
            "languageProfile": {"preferredSpokenLanguage": "Hebrew"},
        },
    }
    natural_language_query = (
        "82-year-old mother in Miami after a recent stroke. She needs medication management, "
        "transfer assistance, physical therapy, occupational therapy, and speech therapy. "
        "She is mentally alert with no dementia."
    )

    with (
        patch("app.services.patient_decision_engine.get_personalized_parameter_order", return_value={"ordered_parameters": ordered_parameters}),
        patch("app.services.patient_decision_engine.get_all_canonical_facility_ids", return_value=list(by_id)),
        patch("app.services.patient_decision_engine.get_canonical_facility_index", return_value={facility_id: {"source_identity_ids": {"synthetic_id": facility_id}} for facility_id in by_id}),
        patch("app.services.patient_decision_engine.get_facility_parameter_table", side_effect=lambda facility_id, **_: _table_for(by_id[facility_id])),
    ):
        output = run_patient_decision_engine(questionnaire, natural_language_query, limit=10)

    ranking = []
    coverage_by_id = {row["facility_id"]: row for row in validation["facility_coverage"]}
    for result in output["results"]:
        coverage = coverage_by_id[result["canonical_facility_id"]]
        ranking.append({
            "rank": result["rank_display"],
            "facility_id": result["canonical_facility_id"],
            "facility_name": result["facility_name"],
            "archetype": by_id[result["canonical_facility_id"]]["test_archetype"],
            "eligibility": result["eligibility_status"],
            "match_score": result["match_score"],
            "evidence_certainty": result["evidence_certainty"],
            "evidence_confidence": result["evidence_confidence"],
            "quality_safety_score": result["quality_safety_score"],
            "staffing_score": result["staffing_score"],
            "coverage_pct": coverage["coverage_pct"],
            "unknown_critical_count": len(result["unknown_critical_needs"]),
            "contradictions": result["contradicted_needs"],
            "stale_needs": result["stale_needs"],
            "not_applicable_needs": result["not_applicable_needs"],
            "evidence_state_notes": result["evidence_state_notes"],
            "concerns": result["explanation"]["concerns"],
            "verification": result["explanation"]["needs_verification"],
        })

    rank_by_id = {row["facility_id"]: index + 1 for index, row in enumerate(ranking)}
    row_by_id = {row["facility_id"]: row for row in ranking}
    assertions = {
        "strong_verified_beats_marketing_rich": rank_by_id["SYN-A"] < rank_by_id["SYN-F"],
        "lower_coverage_can_outrank_higher_coverage_on_relevance": rank_by_id["SYN-H"] < rank_by_id["SYN-B"],
        "many_unknowns_gain_no_false_negative": row_by_id["SYN-G"]["eligibility"] != "INELIGIBLE",
        "stale_evidence_not_counted_as_proven": bool(row_by_id["SYN-I"]["stale_needs"]),
        "contradictions_preserved": sum(bool(row["contradictions"]) for row in ranking) >= 3,
        "specialized_mismatch_detected": row_by_id["SYN-J"]["eligibility"] == "INELIGIBLE",
        "regulatory_negatives_reduce_quality": row_by_id["SYN-E"]["quality_safety_score"] < row_by_id["SYN-A"]["quality_safety_score"],
        "coverage_not_used_as_generic_score": all("coverage_pct" not in decision.get("decision_dimension", "") for decision in output["tie_break_decisions"]),
    }

    return {
        "dataset_id": dataset["dataset_id"],
        "synthetic_only": True,
        "validation": validation,
        "assertions": assertions,
        "pass": validation["valid"] and all(assertions.values()),
        "ranking": ranking,
        "tie_break_decisions": output["tie_break_decisions"],
    }