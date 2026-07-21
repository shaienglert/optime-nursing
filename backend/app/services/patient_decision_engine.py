from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.services.facility_parameter_service import (
    compare_facility_parameter_tables,
    get_all_canonical_facility_ids,
    get_canonical_facility_index,
    get_facility_parameter_table,
    get_personalized_parameter_order,
)


REQUIREMENT_WEIGHTS = {
    "REQUIRED": 5.0,
    "HIGH": 3.0,
    "MEDIUM": 2.0,
    "PREFERENCE": 1.0,
}

ELIGIBILITY_ORDER = {
    "ELIGIBLE": 0,
    "POTENTIALLY_ELIGIBLE": 1,
    "INSUFFICIENT_EVIDENCE": 2,
    "INELIGIBLE": 3,
}


@dataclass
class NeedItem:
    parameter_id: str
    requirement_level: str
    desired_value: Any
    acceptable_values: List[Any]
    applicable_scope: str
    user_evidence_source: str
    confidence: float
    need_text: str


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _add_need(
    needs_by_id: Dict[str, NeedItem],
    parameter_id: str,
    requirement_level: str,
    desired_value: Any,
    acceptable_values: List[Any],
    applicable_scope: str,
    user_evidence_source: str,
    confidence: float,
    need_text: str,
) -> None:
    existing = needs_by_id.get(parameter_id)
    if existing is None:
        needs_by_id[parameter_id] = NeedItem(
            parameter_id=parameter_id,
            requirement_level=requirement_level,
            desired_value=desired_value,
            acceptable_values=acceptable_values,
            applicable_scope=applicable_scope,
            user_evidence_source=user_evidence_source,
            confidence=confidence,
            need_text=need_text,
        )
        return

    if REQUIREMENT_WEIGHTS[requirement_level] > REQUIREMENT_WEIGHTS[existing.requirement_level]:
        existing.requirement_level = requirement_level
        existing.desired_value = desired_value
        existing.acceptable_values = acceptable_values
        existing.applicable_scope = applicable_scope
        existing.need_text = need_text

    existing.confidence = max(existing.confidence, confidence)
    if user_evidence_source not in existing.user_evidence_source:
        existing.user_evidence_source = f"{existing.user_evidence_source}; {user_evidence_source}"


def _map_assistance_level(questionnaire: Dict[str, Any], needs_by_id: Dict[str, NeedItem]) -> None:
    level = _normalize(questionnaire.get("assistanceLevel"))
    if "skilled nursing" in level or "complex" in level:
        _add_need(needs_by_id, "skilled_nursing_capabilities", "REQUIRED", "YES", ["YES"], "FACILITY", "questionnaire.assistanceLevel", 1.0, "Needs skilled nursing capability")
        _add_need(needs_by_id, "nursing_24_7", "REQUIRED", "YES", ["YES"], "FACILITY", "questionnaire.assistanceLevel", 1.0, "Needs 24/7 nursing")
        _add_need(needs_by_id, "transfer_assistance", "HIGH", "YES", ["YES"], "SERVICE", "questionnaire.assistanceLevel", 0.9, "Needs transfer assistance")
        _add_need(needs_by_id, "medication_support", "HIGH", "YES", ["YES"], "SERVICE", "questionnaire.assistanceLevel", 0.9, "Needs medication support")
    elif "bathing" in level or "light" in level or "assistance" in level:
        _add_need(needs_by_id, "adl_support", "HIGH", "YES", ["YES"], "SERVICE", "questionnaire.assistanceLevel", 1.0, "Needs ADL support")
        _add_need(needs_by_id, "transfer_assistance", "MEDIUM", "YES", ["YES"], "SERVICE", "questionnaire.assistanceLevel", 0.8, "May need transfer help")


def _map_memory(questionnaire: Dict[str, Any], needs_by_id: Dict[str, NeedItem]) -> None:
    memory_status = _normalize(questionnaire.get("memoryStatus"))
    if "significant" in memory_status:
        _add_need(needs_by_id, "memory_care", "REQUIRED", "YES", ["YES"], "PROGRAM", "questionnaire.memoryStatus", 1.0, "Requires memory care")
        _add_need(needs_by_id, "dementia_alz_programs", "HIGH", "YES", ["YES"], "PROGRAM", "questionnaire.memoryStatus", 1.0, "Requires dementia program")
    elif "mild" in memory_status:
        _add_need(needs_by_id, "memory_care", "MEDIUM", "YES", ["YES", "UNKNOWN"], "PROGRAM", "questionnaire.memoryStatus", 0.8, "Mild memory support preferred")


def _map_rehab(questionnaire: Dict[str, Any], needs_by_id: Dict[str, NeedItem]) -> None:
    transition = questionnaire.get("humanIntelligenceV2", {}).get("transitionRiskProfile", {})
    rehab_need = _normalize(transition.get("postHospitalRehabNeed"))
    if rehab_need in {"yes", "required", "high"}:
        _add_need(needs_by_id, "pt", "HIGH", "YES", ["YES"], "SERVICE", "questionnaire.transitionRiskProfile.postHospitalRehabNeed", 1.0, "Needs physical therapy")
        _add_need(needs_by_id, "ot", "HIGH", "YES", ["YES"], "SERVICE", "questionnaire.transitionRiskProfile.postHospitalRehabNeed", 1.0, "Needs occupational therapy")
        _add_need(needs_by_id, "speech_therapy", "MEDIUM", "YES", ["YES", "UNKNOWN"], "SERVICE", "questionnaire.transitionRiskProfile.postHospitalRehabNeed", 0.9, "Speech therapy may be needed")
        _add_need(needs_by_id, "post_stroke_neuro_evidence", "HIGH", "YES", ["YES"], "PROGRAM", "questionnaire.transitionRiskProfile.postHospitalRehabNeed", 0.9, "Needs neurological/stroke rehab support")


def _map_personal_preferences(questionnaire: Dict[str, Any], needs_by_id: Dict[str, NeedItem]) -> None:
    language = questionnaire.get("humanIntelligenceV2", {}).get("languageProfile", {})
    preferred_language = _normalize(language.get("preferredSpokenLanguage"))
    if preferred_language:
        _add_need(needs_by_id, "languages", "MEDIUM", preferred_language, [preferred_language, "UNKNOWN"], "FACILITY", "questionnaire.languageProfile.preferredSpokenLanguage", 1.0, "Preferred spoken language support")

    food = questionnaire.get("humanIntelligenceV2", {}).get("foodProfile", {})
    dietary = [item for item in (food.get("dietaryPreferences") or []) if str(item).strip()]
    if any("gluten" in _normalize(item) for item in dietary):
        _add_need(needs_by_id, "gluten_free", "PREFERENCE", "YES", ["YES", "UNKNOWN"], "SERVICE", "questionnaire.foodProfile.dietaryPreferences", 1.0, "Gluten-free option preferred")
    if any("kosher" in _normalize(item) for item in dietary):
        _add_need(needs_by_id, "kosher", "PREFERENCE", "YES", ["YES", "UNKNOWN"], "SERVICE", "questionnaire.foodProfile.dietaryPreferences", 1.0, "Kosher option preferred")

    distance = _normalize(questionnaire.get("distanceFromFamily"))
    if distance:
        _add_need(needs_by_id, "transportation", "PREFERENCE", "YES", ["YES", "UNKNOWN"], "SERVICE", "questionnaire.distanceFromFamily", 0.8, "Transportation support preferred")


def _map_financial(questionnaire: Dict[str, Any], needs_by_id: Dict[str, NeedItem]) -> None:
    budget = questionnaire.get("budget")
    if budget not in (None, "", 0):
        _add_need(needs_by_id, "published_rates", "PREFERENCE", "KNOWN", ["KNOWN", "UNKNOWN"], "FACILITY", "questionnaire.budget", 1.0, "Prefer transparent pricing")
    _add_need(needs_by_id, "medicare_attributes", "MEDIUM", "YES", ["YES", "UNKNOWN"], "FACILITY", "governed default", 0.7, "Medicare acceptance often relevant for skilled needs")


def _map_natural_language(text: str, needs_by_id: Dict[str, NeedItem]) -> Dict[str, Any]:
    normalized = _normalize(text)
    extraction_meta = {
        "text": text,
        "recognized_tokens": [],
        "unrecognized_segments": [],
    }

    keyword_rules = [
        (["stroke", "neurolog"], ("post_stroke_neuro_evidence", "HIGH", "YES", ["YES"], "PROGRAM", "natural_language", 0.95, "Post-stroke/neurological rehabilitation support")),
        (["24/7 nursing", "24x7 nursing", "round the clock nursing", "skilled nursing"], ("nursing_24_7", "REQUIRED", "YES", ["YES"], "FACILITY", "natural_language", 0.98, "24/7 nursing required")),
        (["physical therapy", "pt"], ("pt", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.95, "Physical therapy support")),
        (["occupational therapy", "ot"], ("ot", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.95, "Occupational therapy support")),
        (["speech therapy", "speech"], ("speech_therapy", "HIGH", "YES", ["YES", "UNKNOWN"], "SERVICE", "natural_language", 0.9, "Speech therapy support")),
        (["transfer", "mobility", "lift"], ("transfer_assistance", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.9, "Transfer assistance support")),
        (["bathing", "dressing", "adl"], ("adl_support", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.9, "ADL support")),
        (["medication"], ("medication_support", "HIGH", "YES", ["YES"], "SERVICE", "natural_language", 0.92, "Medication management support")),
        (["dementia", "alzheimer", "memory care"], ("memory_care", "HIGH", "YES", ["YES"], "PROGRAM", "natural_language", 0.95, "Memory care capability")),
        (["no dementia", "mentally alert"], ("memory_care", "PREFERENCE", "NO", ["NO", "UNKNOWN"], "PROGRAM", "natural_language", 0.85, "No dementia-focused unit specifically required")),
    ]

    for keywords, need_tuple in keyword_rules:
        if any(keyword in normalized for keyword in keywords):
            _add_need(needs_by_id, *need_tuple)
            extraction_meta["recognized_tokens"].append(keywords[0])

    location_city = None
    for city in ["miami", "hialeah", "doral", "aventura", "homestead", "coral gables", "north miami"]:
        if city in normalized:
            location_city = city.upper()
            extraction_meta["recognized_tokens"].append(city)
            break

    return {
        "extraction": extraction_meta,
        "location_city": location_city,
    }


def build_patient_needs_profile(questionnaire_state: Dict[str, Any], natural_language_query: str = "") -> Dict[str, Any]:
    needs_by_id: Dict[str, NeedItem] = {}

    _map_assistance_level(questionnaire_state, needs_by_id)
    _map_memory(questionnaire_state, needs_by_id)
    _map_rehab(questionnaire_state, needs_by_id)
    _map_personal_preferences(questionnaire_state, needs_by_id)
    _map_financial(questionnaire_state, needs_by_id)

    nl_meta = _map_natural_language(natural_language_query or "", needs_by_id)

    needs = [
        {
            "parameter_id": item.parameter_id,
            "requirement_level": item.requirement_level,
            "desired_value": item.desired_value,
            "acceptable_values": item.acceptable_values,
            "applicable_scope": item.applicable_scope,
            "user_evidence_source": item.user_evidence_source,
            "confidence": round(item.confidence, 2),
            "need_text": item.need_text,
        }
        for item in sorted(needs_by_id.values(), key=lambda value: (-REQUIREMENT_WEIGHTS[value.requirement_level], value.parameter_id))
    ]

    need_tags = sorted({item["parameter_id"].replace("_", " ") for item in needs if item["requirement_level"] in {"REQUIRED", "HIGH"}})
    priority_parameter_ids = [item["parameter_id"] for item in needs if item["requirement_level"] in {"REQUIRED", "HIGH"}]
    profile_key = "stroke" if any("stroke" in item["need_text"].lower() for item in needs) else ("memory" if any(item["parameter_id"] in {"memory_care", "dementia_alz_programs"} for item in needs) else None)

    return {
        "generated_from": {
            "questionnaire": True,
            "natural_language": bool((natural_language_query or "").strip()),
        },
        "needs": needs,
        "need_tags": need_tags,
        "priority_parameter_ids": priority_parameter_ids,
        "profile_key": profile_key,
        "location_city": nl_meta.get("location_city"),
        "natural_language_mapping": nl_meta,
    }


def _evaluate_need(need: Dict[str, Any], row_by_param: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    row = row_by_param.get(need["parameter_id"])
    if not row:
        return "UNKNOWN", "No evidence row available for this parameter."

    raw = row.get("raw_value")
    if need.get("desired_value") == "NO":
        if raw == "NO":
            return "MATCH", "Verified as NO and aligned with requested absence."
        if raw == "YES":
            return "GAP", "Verified as YES but user requested NO."
        return "UNKNOWN", "Not verified."

    if raw == "YES":
        return "MATCH", "Verified as YES."
    if raw == "NO":
        return "GAP", "Verified as NO."
    if raw in {"UNKNOWN", None}:
        return "UNKNOWN", "Not verified."
    return "MATCH", "Typed value exists and is considered acceptable for current rules."


def _eligibility_from_needs(
    needs: List[Dict[str, Any]],
    row_by_param: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    required_or_high = [item for item in needs if item["requirement_level"] in {"REQUIRED", "HIGH"}]
    matched_needs = []
    unmet_verified_needs = []
    unknown_critical_needs = []
    preference_matches = []

    for need in needs:
        status, reason = _evaluate_need(need, row_by_param)
        entry = {
            "parameter_id": need["parameter_id"],
            "requirement_level": need["requirement_level"],
            "status": status,
            "reason": reason,
        }
        if status == "MATCH":
            matched_needs.append(entry)
            if need["requirement_level"] == "PREFERENCE":
                preference_matches.append(entry)
        elif status == "GAP":
            unmet_verified_needs.append(entry)
        else:
            if need["requirement_level"] in {"REQUIRED", "HIGH"}:
                unknown_critical_needs.append(entry)

    required_high_failures = [entry for entry in unmet_verified_needs if entry["requirement_level"] in {"REQUIRED", "HIGH"}]
    required_high_unknown = [entry for entry in unknown_critical_needs if entry["requirement_level"] in {"REQUIRED", "HIGH"}]
    required_high_matches = [entry for entry in matched_needs if entry["requirement_level"] in {"REQUIRED", "HIGH"}]

    if required_high_failures:
        eligibility = "INELIGIBLE"
    elif required_high_unknown and required_high_matches:
        eligibility = "POTENTIALLY_ELIGIBLE"
    elif required_high_unknown and not required_high_matches:
        eligibility = "INSUFFICIENT_EVIDENCE"
    else:
        eligibility = "ELIGIBLE"

    reasons = []
    if required_high_failures:
        reasons.append("Verified incompatible evidence exists for one or more required/high needs.")
    if required_high_unknown:
        reasons.append("Some required/high needs are not yet verified and need direct confirmation.")
    if not reasons:
        reasons.append("Required and high-priority needs are currently supported by verified evidence.")

    return {
        "eligibility_status": eligibility,
        "matched_needs": matched_needs,
        "unmet_verified_needs": unmet_verified_needs,
        "unknown_critical_needs": unknown_critical_needs,
        "preference_matches": preference_matches,
        "reasons": reasons,
    }


def _domain_breakdown(needs: List[Dict[str, Any]], matched: List[Dict[str, Any]], unmet: List[Dict[str, Any]]) -> Dict[str, float]:
    domain_weights: Dict[str, float] = defaultdict(float)
    matched_weights: Dict[str, float] = defaultdict(float)
    unmet_weights: Dict[str, float] = defaultdict(float)

    def domain_for_parameter(parameter_id: str) -> str:
        if parameter_id in {"pt", "ot", "speech_therapy", "post_stroke_neuro_evidence", "therapy_staffing", "short_term_rehab"}:
            return "rehabilitation_fit"
        if parameter_id in {"memory_care", "dementia_alz_programs", "dialysis_arrangements", "respiratory_trach_vent", "wound_care", "limited_mental_health", "secured_units", "hospice_palliative_arrangements"}:
            return "specialized_care_fit"
        if parameter_id in {"languages", "activities", "religious_cultural_services", "transportation", "gluten_free", "kosher"}:
            return "personal_social_fit"
        if parameter_id in {"medicare_attributes", "medicaid_attributes", "published_rates", "fees", "payer_information"}:
            return "financial_access_fit"
        if parameter_id in {"current_availability", "earliest_admission_date", "waiting_list"}:
            return "availability_readiness"
        return "clinical_care_fit"

    by_id = {item["parameter_id"]: item for item in needs}
    for need in needs:
        domain = domain_for_parameter(need["parameter_id"])
        domain_weights[domain] += REQUIREMENT_WEIGHTS[need["requirement_level"]]
    for item in matched:
        need = by_id[item["parameter_id"]]
        domain = domain_for_parameter(item["parameter_id"])
        matched_weights[domain] += REQUIREMENT_WEIGHTS[need["requirement_level"]]
    for item in unmet:
        need = by_id[item["parameter_id"]]
        domain = domain_for_parameter(item["parameter_id"])
        unmet_weights[domain] += REQUIREMENT_WEIGHTS[need["requirement_level"]]

    breakdown = {}
    for domain, total in domain_weights.items():
        known = matched_weights[domain] + unmet_weights[domain]
        if known <= 0:
            breakdown[domain] = 0.0
        else:
            breakdown[domain] = round((matched_weights[domain] / known) * 100.0, 2)
    return breakdown


def _score_result(needs: List[Dict[str, Any]], eligibility: Dict[str, Any]) -> Dict[str, Any]:
    by_id = {item["parameter_id"]: item for item in needs}

    matched_weight = 0.0
    unmet_weight = 0.0
    known_weight = 0.0
    total_weight = 0.0

    for need in needs:
        total_weight += REQUIREMENT_WEIGHTS[need["requirement_level"]]

    for item in eligibility["matched_needs"]:
        weight = REQUIREMENT_WEIGHTS[by_id[item["parameter_id"]]["requirement_level"]]
        matched_weight += weight
        known_weight += weight

    for item in eligibility["unmet_verified_needs"]:
        weight = REQUIREMENT_WEIGHTS[by_id[item["parameter_id"]]["requirement_level"]]
        unmet_weight += weight
        known_weight += weight

    if matched_weight + unmet_weight <= 0:
        match_score = 0.0
    else:
        match_score = round((matched_weight / (matched_weight + unmet_weight)) * 100.0, 2)

    evidence_certainty = round((known_weight / total_weight) * 100.0, 2) if total_weight > 0 else 0.0

    if match_score >= 85:
        band = "STRONG_MATCH"
    elif match_score >= 70:
        band = "GOOD_MATCH"
    elif match_score >= 50:
        band = "PARTIAL_MATCH"
    else:
        band = "LIMITED_MATCH"

    return {
        "match_score": match_score,
        "match_band": band,
        "evidence_certainty": evidence_certainty,
        "domain_breakdown": _domain_breakdown(needs, eligibility["matched_needs"], eligibility["unmet_verified_needs"]),
    }


def _facility_geo_match(facility: Dict[str, Any], requested_city: Optional[str]) -> Tuple[str, float]:
    if not requested_city:
        return "No city constraint provided.", 0.0
    city = _normalize(facility.get("city"))
    if city == _normalize(requested_city):
        return f"Located in requested city ({requested_city.title()}).", 5.0
    return f"Not in requested city ({requested_city.title()}); location may still be acceptable by broader radius.", 0.0


def _top_reasons(eligibility: Dict[str, Any], table_rows: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[str]]:
    row_by_param = {row["parameter_id"]: row for row in table_rows}

    strong = []
    for item in eligibility["matched_needs"][:5]:
        row = row_by_param.get(item["parameter_id"], {})
        strong.append(f"{item['parameter_id']} matched ({row.get('source', 'source unknown')})")

    verify = []
    for item in eligibility["unknown_critical_needs"][:5]:
        verify.append(f"{item['parameter_id']} not verified")

    concerns = []
    for item in eligibility["unmet_verified_needs"][:5]:
        concerns.append(f"{item['parameter_id']} verified gap")

    if any(row["parameter_id"] == "current_availability" for row in table_rows):
        verify.append("Current availability must be confirmed directly with the facility")

    return strong, verify, concerns


def run_patient_decision_engine(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    profile = build_patient_needs_profile(questionnaire_state, natural_language_query)
    needs = profile["needs"]

    order_payload = get_personalized_parameter_order(
        need_tags=profile["need_tags"],
        priority_parameter_ids=profile["priority_parameter_ids"],
        profile_key=profile["profile_key"],
    )
    ordered_parameter_ids = [row["parameter_id"] for row in order_payload.get("ordered_parameters", [])]

    canonical_index = get_canonical_facility_index()
    discovered_ids = get_all_canonical_facility_ids()

    results = []
    requested_city = profile.get("location_city")

    for canonical_id in discovered_ids:
        table = get_facility_parameter_table(
            canonical_id,
            need_tags=profile["need_tags"],
            priority_parameter_ids=profile["priority_parameter_ids"],
            profile_key=profile["profile_key"],
        )
        canonical_meta = canonical_index.get(canonical_id, {})
        row_by_param = {row["parameter_id"]: row for row in table["rows"]}

        eligibility = _eligibility_from_needs(needs, row_by_param)
        scoring = _score_result(needs, eligibility)
        geo_note, geo_bonus = _facility_geo_match({"city": table.get("city")}, requested_city)
        strong, verify, concerns = _top_reasons(eligibility, table["rows"])

        results.append(
            {
                "canonical_facility_id": canonical_id,
                "facility_name": table["facility_name"],
                "city": table.get("city"),
                "state": table.get("state"),
                "county": table.get("county"),
                "zip": table.get("zip"),
                "canonical_type": table.get("canonical_type"),
                "role_classification": table.get("role_classification"),
                "source_identity_ids": canonical_meta.get("source_identity_ids") or {},
                "eligibility_status": eligibility["eligibility_status"],
                "match_score": min(100.0, round(scoring["match_score"] + geo_bonus, 2)),
                "match_band": scoring["match_band"],
                "matched_needs": eligibility["matched_needs"],
                "unmet_verified_needs": eligibility["unmet_verified_needs"],
                "unknown_critical_needs": eligibility["unknown_critical_needs"],
                "preference_matches": eligibility["preference_matches"],
                "evidence_certainty": scoring["evidence_certainty"],
                "domain_breakdown": scoring["domain_breakdown"],
                "explanation": {
                    "why_matches": strong,
                    "needs_verification": verify,
                    "concerns": concerns,
                    "eligibility_reasons": eligibility["reasons"],
                    "availability_note": "Current availability must be confirmed directly with the facility.",
                    "location_note": geo_note,
                },
                "parameter_badges": [item["parameter_id"] for item in eligibility["matched_needs"][:6]],
                "comparison_parameter_ids": ordered_parameter_ids,
            }
        )

    results.sort(
        key=lambda item: (
            ELIGIBILITY_ORDER[item["eligibility_status"]],
            -item["match_score"],
            item["facility_name"],
        )
    )

    top = results[: max(10, limit)]
    return {
        "patient_needs_profile": profile,
        "results": top[:limit],
        "result_count": len(top[:limit]),
        "total_candidates_scored": len(results),
        "availability_policy": "Current availability must be confirmed directly with the facility.",
    }


def build_patient_comparison_context(canonical_facility_ids: List[str], patient_needs_profile: Dict[str, Any]) -> Dict[str, Any]:
    comparison = compare_facility_parameter_tables(
        canonical_facility_ids,
        need_tags=patient_needs_profile.get("need_tags") or [],
        priority_parameter_ids=patient_needs_profile.get("priority_parameter_ids") or [],
        profile_key=patient_needs_profile.get("profile_key"),
    )

    needs_by_parameter = {item["parameter_id"]: item for item in patient_needs_profile.get("needs") or []}
    facilities = []
    for facility in comparison.get("facilities", []):
        context_rows = []
        for row in facility.get("rows", []):
            need = needs_by_parameter.get(row["parameter_id"])
            if not need:
                continue
            raw = row.get("raw_value")
            if raw == "YES":
                status = "MATCH"
            elif raw == "NO":
                status = "VERIFIED_GAP"
            else:
                status = "NOT_VERIFIED"
            context_rows.append(
                {
                    "parameter_id": row["parameter_id"],
                    "requirement_level": need["requirement_level"],
                    "status": status,
                    "source": row.get("source"),
                    "scope": row.get("detail_scope"),
                    "scope_name": row.get("scope_name"),
                }
            )
        facilities.append(
            {
                "canonical_facility_id": facility["canonical_facility_id"],
                "facility_name": facility["facility_name"],
                "need_rows": context_rows,
            }
        )

    return {
        "required_needs": [item for item in patient_needs_profile.get("needs", []) if item["requirement_level"] == "REQUIRED"],
        "high_priority_needs": [item for item in patient_needs_profile.get("needs", []) if item["requirement_level"] == "HIGH"],
        "preferences": [item for item in patient_needs_profile.get("needs", []) if item["requirement_level"] in {"MEDIUM", "PREFERENCE"}],
        "comparison_parameter_ids": comparison.get("parameter_ids", []),
        "facilities": facilities,
    }