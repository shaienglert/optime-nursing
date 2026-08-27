from __future__ import annotations

"""Compose housing, meals and personal care into one governed decision solution."""

from typing import Any, Dict, Iterable, List

from app.services.facility_service_delivery_runtime import get_facility_service_delivery_evidence

UNKNOWN = "UNKNOWN"


def _upper(value: Any) -> str:
    return str(value or UNKNOWN).strip().upper()


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
    part_time = any(token in combined for token in ("few hours", "a few hours", "couple hours", "part time", "part-time", "morning and evening", "morning/evening", "one hour", "1 hour"))
    adl = any(token in combined for token in ("bathing", "dressing", "adl", "personal care", "caregiver", "care giver", "shower"))
    medication = any(token in combined for token in ("medication", "meds", "med management", "pills", "prescription"))
    meals_material = any(token in combined for token in ("meal", "meals", "food", "dining", "breakfast", "lunch", "dinner", "ארוחות", "אוכל"))
    in_house_only_requested = any(token in combined for token in (
        "everything in house", "everything in-house", "all in house", "all in-house",
        "only in house", "only in-house", "in house only", "in-house only",
        "no outside care", "no outside caregiver", "no external care", "no external agency",
        "no outside agency", "not okay with outside caregivers", "not comfortable with outside caregivers",
        "don't want outside caregivers", "do not want outside caregivers",
    ))
    return {
        "temporary_care_need": temporary,
        "home_like_or_independent_preference": home_like,
        "part_time_care_pattern": part_time,
        "adl_support_needed": adl,
        "medication_support_needed": medication,
        "meals_material": meals_material,
        "in_house_only_requested": in_house_only_requested,
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
        if item.get("can_cover_required_services") is not True or item.get("service_area_match") is not True:
            continue
        return {
            "status": "VERIFIED_MATCH",
            "agency_id": item.get("agency_id") or item.get("canonical_agency_id"),
            "agency_name": item.get("agency_name") or item.get("name"),
            "services": item.get("services") or [],
            "minimum_hours": item.get("minimum_hours", UNKNOWN),
            "estimated_hourly_rate": item.get("estimated_hourly_rate", UNKNOWN),
            "source": item.get("source") or "AGENCY_UNIVERSE",
        }
    return {
        "status": "NO_VERIFIED_MATCH_YET",
        "agency_id": None,
        "agency_name": None,
        "services": [],
        "minimum_hours": UNKNOWN,
        "estimated_hourly_rate": UNKNOWN,
        "source": UNKNOWN,
    }


def _meal_component(service: Dict[str, Any]) -> Dict[str, Any]:
    meal = dict(service.get("meal_delivery") or {})
    return {
        "dining_available": meal.get("dining_available", UNKNOWN),
        "meals_per_day": meal.get("meals_per_day", UNKNOWN),
        "meal_plan_model": meal.get("meal_plan_model", UNKNOWN),
        "meal_plan_included": meal.get("meal_plan_included", UNKNOWN),
        "meal_delivery_to_apartment": meal.get("meal_delivery_to_apartment", UNKNOWN),
        "between_meal_food_available": meal.get("between_meal_food_available", UNKNOWN),
        "evidence_status": meal.get("evidence_status", UNKNOWN),
        "source": service.get("primary_source_url", UNKNOWN),
    }


def build_combined_care_solution(row: Dict[str, Any], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    signals = _query_signals(questionnaire_state, natural_language_query)
    payloads = _payloads(row)
    canonical_type = _upper(row.get("canonical_type"))
    modalities = {_upper(item) for item in row.get("housing_modalities") or []}
    service = get_facility_service_delivery_evidence(row)
    row["facility_service_delivery_evidence"] = service
    care_delivery = dict(service.get("personal_care_delivery") or {})

    explicit_in_house = care_delivery.get("personal_care_in_house") is True
    in_house_adl = canonical_type == "ASSISTED_LIVING_RFG" or explicit_in_house or any(p.get("adl_support_verified") is True for p in payloads)
    outside_allowed_true = care_delivery.get("outside_care_allowed") is True or any(p.get("outside_care_allowed_verified") is True for p in payloads)
    outside_allowed_false = care_delivery.get("outside_care_allowed") is False or any(p.get("outside_care_allowed_verified") is False for p in payloads)
    agency = _agency_match_from_row(row)
    agency_verified = agency["status"] == "VERIFIED_MATCH"
    in_house_only = bool(signals.get("in_house_only_requested"))

    in_house_medication = any(p.get("medication_support_verified") is True for p in payloads)
    medication_verified_false = any(p.get("medication_support_verified") is False for p in payloads)
    if in_house_medication:
        medication_coverage, medication_delivery_model = "PASS", "FACILITY_IN_HOUSE"
        medication_reason = "Required medication management is verified in-house at the facility."
    elif not in_house_only and outside_allowed_true and agency_verified:
        medication_coverage, medication_delivery_model = "PASS", "FACILITY_PLUS_EXTERNAL_AGENCY"
        medication_reason = "Facility housing allows outside care and a verified agency match covers medication management."
    elif medication_verified_false and (in_house_only or outside_allowed_false):
        medication_coverage, medication_delivery_model = "FAIL", "NO_VALID_EXTERNAL_PATH"
        medication_reason = "Medication management is verified not offered in-house, and no external pathway is available or the client requested in-house-only care."
    elif not in_house_only and outside_allowed_true:
        medication_coverage, medication_delivery_model = "PENDING_VERIFICATION", "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"
        medication_reason = "Outside care is allowed, but no verified agency match for medication management has been attached yet."
    else:
        medication_coverage, medication_delivery_model = "PENDING_VERIFICATION", "CARE_DELIVERY_UNKNOWN"
        medication_reason = "Medication management delivery is material but neither in-house coverage nor an external-care pathway is fully verified."

    independent_setting = bool(modalities & {"INDEPENDENT_LIVING", "ACTIVE_ADULT", "ACTIVE_ADULT_55_PLUS_APARTMENTS", "LIFE_PLAN_CCRC"}) or canonical_type in {"INDEPENDENT_LIVING", "LIFE_PLAN_CCRC"}

    if in_house_adl:
        coverage, delivery_model = "PASS", "FACILITY_IN_HOUSE"
        reason = "Required personal care is verified in-house or supplied by the licensed assisted-living component."
    elif outside_allowed_true and agency_verified:
        coverage, delivery_model = "PASS", "FACILITY_PLUS_EXTERNAL_AGENCY"
        reason = "Housing allows outside care and a verified agency match covers the required services."
    elif outside_allowed_false:
        coverage, delivery_model = "FAIL", "NO_VALID_EXTERNAL_PATH"
        reason = "The facility is verified not to allow the external care pathway and required care is not verified in-house."
    elif outside_allowed_true:
        coverage, delivery_model = "PENDING_VERIFICATION", "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"
        reason = "Outside care is allowed, but no verified agency match has been attached yet."
    else:
        coverage, delivery_model = "PENDING_VERIFICATION", "CARE_DELIVERY_UNKNOWN"
        reason = "Care delivery is material but neither in-house coverage nor an external-care pathway is fully verified."

    strategy_fit = "STANDARD"
    if signals["external_care_strategy_material"] and independent_setting:
        strategy_fit = "PREFERRED_COMPOSITE_CANDIDATE"
    elif signals["external_care_strategy_material"] and outside_allowed_true:
        strategy_fit = "COMPOSITE_CANDIDATE"

    return {
        "version": "combined-care-solution-v2",
        "strategy_fit": strategy_fit,
        "housing_component": {
            "canonical_facility_id": row.get("canonical_facility_id"),
            "facility_name": row.get("facility_name"),
            "canonical_type": row.get("canonical_type"),
            "housing_modalities": sorted(modalities),
            "independent_or_home_like_setting": independent_setting,
        },
        "meal_component": _meal_component(service),
        "care_component": {
            "adl_required": signals["adl_support_needed"],
            "temporary_care_need": signals["temporary_care_need"],
            "part_time_care_pattern": signals["part_time_care_pattern"],
            "in_house_adl_verified": in_house_adl,
            "facility_declared_care_delivery_model": care_delivery.get("care_delivery_model", UNKNOWN),
            "external_care_allowed": True if outside_allowed_true else False if outside_allowed_false else UNKNOWN,
            "agency_relationship_type": care_delivery.get("agency_relationship_type", UNKNOWN),
            "partner_agency_name": care_delivery.get("partner_agency_name", UNKNOWN),
            "partner_agency_license_id": care_delivery.get("partner_agency_license_id", UNKNOWN),
            "external_agency_match": agency,
        },
        "medication_component": {
            "medication_required": signals["medication_support_needed"],
            "in_house_only_requested": in_house_only,
            "in_house_medication_verified": in_house_medication,
            "external_care_allowed": True if outside_allowed_true else False if outside_allowed_false else UNKNOWN,
            "external_agency_match": agency,
            "combined_must_coverage": medication_coverage,
            "delivery_model": medication_delivery_model,
            "reason": medication_reason,
        },
        "support_services": service.get("support_services") or {},
        "combined_must_coverage": coverage,
        "delivery_model": delivery_model,
        "reason": reason,
        "policy": "Rank the complete solution. Housing, meals, personal care and medication management are separate evidence domains. Dining never implies three meals/day; outside-care permission never implies a verified agency; UNKNOWN remains UNKNOWN. An external-agency pathway is a valid complementary product for a care-delivery MUST unless the client explicitly requested in-house-only care.",
    }


def attach_combined_care_solutions(rows: Iterable[Dict[str, Any]], questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
    signals = _query_signals(questionnaire_state, natural_language_query)
    counts = {"FACILITY_IN_HOUSE": 0, "FACILITY_PLUS_EXTERNAL_AGENCY": 0, "PENDING": 0, "FAIL": 0}
    meal_counts = {"THREE_MEALS_VERIFIED": 0, "MEAL_PLAN_OTHER": 0, "MEALS_UNKNOWN": 0}
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
        meals = solution["meal_component"].get("meals_per_day", UNKNOWN)
        if meals == 3:
            meal_counts["THREE_MEALS_VERIFIED"] += 1
        elif meals == UNKNOWN:
            meal_counts["MEALS_UNKNOWN"] += 1
        else:
            meal_counts["MEAL_PLAN_OTHER"] += 1
    return {
        "version": "combined-care-solution-v2",
        "signals": signals,
        "counts": counts,
        "meal_evidence_counts": meal_counts,
        "agency_universe_contract": {
            "required_fields": ["canonical_agency_id", "agency_name", "verification_status", "service_area_match", "can_cover_required_services", "services", "minimum_hours", "estimated_hourly_rate", "source"],
            "rule": "Only VERIFIED agency matches may convert an external-care pathway from PENDING_VERIFICATION to PASS.",
        },
        "meal_contract": {
            "rule": "Dining availability alone never proves a fixed meal count or inclusion. A three-meal requirement passes only with explicit facility/operator evidence.",
        },
    }


__all__ = ["attach_combined_care_solutions", "build_combined_care_solution"]
