from __future__ import annotations

"""Compose housing + care into one governed decision solution.

A facility is not rejected merely because personal care is not delivered in-house.
When the resident prefers a more independent/home-like setting or care is temporary,
OPTIME may compose the housing choice with a verified external home-care agency.

Safety invariant: permission to use outside care is NOT the same as having a verified
agency match. Until both are known, the care pathway stays PENDING_VERIFICATION.
UNKNOWN is never promoted to PASS.
"""

from typing import Any, Dict, Iterable, List


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    out: List[Dict[str, Any]] = []
    for item in evidence:
        payload = item.get("payload") if isinstance(item, dict) else None
        if isinstance(payload, dict):
            out.append(payload)
    provider = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
    provider_evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else None
    if provider_evidence:
        out.append(provider_evidence)
    life_plan = row.get("life_plan_primary_evidence") if isinstance(row.get("life_plan_primary_evidence"), dict) else {}
    if life_plan:
        out.append(life_plan)
    return out


def _query_signals(questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    text = str(natural_language_query or "").lower()
    assistance = str(questionnaire_state.get("assistanceLevel") or "").lower()
    combined = f"{text} {assistance}"
    temporary = any(token in combined for token in ("temporary", "temporarily", "3 months", "three months", "short term", "short-term", "post surgery", "after surgery", "recovery", "recovering"))
    home_like = any(token in combined for token in ("intimate", "home-like", "homelike", "home like", "small community", "less institutional", "not institutional", "independent living", "independent senior living"))
    part_time = any(token in combined for token in ("few hours", "a few hours", "couple hours", "part time", "part-time", "morning and evening", "morning/evening"))
    adl = any(token in combined for token in ("bathing", "dressing", "adl", "personal care", "caregiver", "care giver"))
    return {
        "temporary_care_need": temporary,
        "home_like_or_independent_preference": home_like,
        "part_time_care_pattern": part_time,
        "adl_support_needed": adl,
        "external_care_strategy_material": adl and (temporary or home_like or part_time),
    }


def _agency_match_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    direct = row.get("external_care_agency_match") if isinstance(row.get("external_care_agency_match"), dict) else {}
    matches = row.get("external_care_agency_matches") if isinstance(row.get("external_care_agency_matches"), list) else []
    candidates: List[Dict[str, Any]] = []
    if direct:
        candidates.append(direct)
    candidates.extend(item for item in matches if isinstance(item, dict))
    for item in candidates:
        if _upper(item.get("verification_status")) != "VERIFIED":
            continue
        if item.get("can_cover_required_services") is not True:
            continue
        if item.get("service_area_match") is not True:
            continue
        return {
            "status": "VERIFIED_MATCH",
            "agency_id": item.get("agency_id") or item.get("canonical_agency_id"),
            "agency_name": item.get("agency_name") or item.get("name"),
            "services": item.get("services") or [],
            "minimum_hours": item.get("minimum_hours", "UNKNOWN"),
            "estimated_hourly_rate": item.get("estimated_hourly_rate", "UNKNOWN"),
            "source": item.get("source") or "AGENCY_UNIVERSE",
        }
    return {
        "status": "NO_VERIFIED_MATCH_YET",
        "agency_id": None,
        "agency_name": None,
        "services": [],
        "minimum_hours": "UNKNOWN",
        "estimated_hourly_rate": "UNKNOWN",
        "source": "UNKNOWN",
    }


def build_combined_care_solution(
    row: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
) -> Dict[str, Any]:
    signals = _query_signals(questionnaire_state, natural_language_query)
    payloads = _payloads(row)
    canonical_type = _upper(row.get("canonical_type"))
    modalities = {_upper(item) for item in row.get("housing_modalities") or []}

    in_house_adl = canonical_type == "ASSISTED_LIVING_RFG" or any(p.get("adl_support_verified") is True for p in payloads)
    outside_allowed_true = any(p.get("outside_care_allowed_verified") is True for p in payloads)
    outside_allowed_false = any(p.get("outside_care_allowed_verified") is False for p in payloads)
    agency = _agency_match_from_row(row)
    agency_verified = agency["status"] == "VERIFIED_MATCH"

    independent_setting = bool(modalities & {"INDEPENDENT_LIVING", "ACTIVE_ADULT", "LIFE_PLAN_CCRC"}) or canonical_type in {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}

    if in_house_adl:
        coverage = "PASS"
        delivery_model = "FACILITY_IN_HOUSE"
        reason = "Required personal care is verified in-house."
    elif outside_allowed_true and agency_verified:
        coverage = "PASS"
        delivery_model = "FACILITY_PLUS_EXTERNAL_AGENCY"
        reason = "Housing allows outside care and a verified agency match covers the required services."
    elif outside_allowed_false:
        coverage = "FAIL"
        delivery_model = "NO_VALID_EXTERNAL_PATH"
        reason = "The facility is verified not to allow the external care pathway and required care is not verified in-house."
    elif outside_allowed_true:
        coverage = "PENDING_VERIFICATION"
        delivery_model = "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"
        reason = "Outside care is allowed, but no verified agency match has been attached yet."
    else:
        coverage = "PENDING_VERIFICATION"
        delivery_model = "CARE_DELIVERY_UNKNOWN"
        reason = "Care delivery is material but neither in-house coverage nor an external-care pathway is fully verified."

    strategy_fit = "STANDARD"
    if signals["external_care_strategy_material"] and independent_setting:
        strategy_fit = "PREFERRED_COMPOSITE_CANDIDATE"
    elif signals["external_care_strategy_material"] and outside_allowed_true:
        strategy_fit = "COMPOSITE_CANDIDATE"

    return {
        "version": "combined-care-solution-v1",
        "strategy_fit": strategy_fit,
        "housing_component": {
            "canonical_facility_id": row.get("canonical_facility_id"),
            "facility_name": row.get("facility_name"),
            "canonical_type": row.get("canonical_type"),
            "housing_modalities": sorted(modalities),
            "independent_or_home_like_setting": independent_setting,
        },
        "care_component": {
            "adl_required": signals["adl_support_needed"],
            "temporary_care_need": signals["temporary_care_need"],
            "part_time_care_pattern": signals["part_time_care_pattern"],
            "in_house_adl_verified": in_house_adl,
            "external_care_allowed": True if outside_allowed_true else False if outside_allowed_false else "UNKNOWN",
            "external_agency_match": agency,
        },
        "combined_must_coverage": coverage,
        "delivery_model": delivery_model,
        "reason": reason,
        "policy": "Facility fit and care delivery are evaluated separately; external-care permission alone never proves care coverage. A verified agency match is required before an external pathway can satisfy a care MUST.",
    }


def attach_combined_care_solutions(
    rows: Iterable[Dict[str, Any]],
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
) -> Dict[str, Any]:
    signals = _query_signals(questionnaire_state, natural_language_query)
    counts = {"FACILITY_IN_HOUSE": 0, "FACILITY_PLUS_EXTERNAL_AGENCY": 0, "PENDING": 0, "FAIL": 0}
    for row in rows:
        solution = build_combined_care_solution(row, questionnaire_state, natural_language_query)
        row["combined_care_solution"] = solution
        model = solution["delivery_model"]
        if model == "FACILITY_IN_HOUSE":
            counts["FACILITY_IN_HOUSE"] += 1
        elif model == "FACILITY_PLUS_EXTERNAL_AGENCY":
            counts["FACILITY_PLUS_EXTERNAL_AGENCY"] += 1
        elif solution["combined_must_coverage"] == "FAIL":
            counts["FAIL"] += 1
        else:
            counts["PENDING"] += 1
    return {
        "version": "combined-care-solution-v1",
        "signals": signals,
        "counts": counts,
        "agency_universe_contract": {
            "required_fields": [
                "canonical_agency_id",
                "agency_name",
                "verification_status",
                "service_area_match",
                "can_cover_required_services",
                "services",
                "minimum_hours",
                "estimated_hourly_rate",
                "source",
            ],
            "rule": "Only VERIFIED agency matches may convert an external-care pathway from PENDING_VERIFICATION to PASS.",
        },
    }


__all__ = ["attach_combined_care_solutions", "build_combined_care_solution"]
