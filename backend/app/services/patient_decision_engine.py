from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import cmp_to_key
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

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

TIE_THRESHOLD_POLICY = {
    "patient_match": 1.0,
    "quality_safety": 2.0,
    "staffing": 2.0,
    "capability_depth": 1.5,
    "patient_relevant_outcomes": 1.5,
    "practical_fit": 1.5,
}

MATCH_EVIDENCE_MULTIPLIER = {
    "REGULATORY_VERIFIED": 1.0,
    "VERIFIED": 0.95,
    "FACILITY_REPORTED": 0.8,
    "TAXONOMY_INFERRED": 0.55,
    "UNKNOWN": 0.0,
}

QUALITY_SAFETY_PARAMETER_IDS = {
    "inspection_rating",
    "deficiency_count",
    "deficiency_severity",
    "complaint_related_findings",
    "fire_safety_deficiencies",
    "infection_control_findings",
    "penalties_fines",
    "payment_denials",
    "sanctions_final_orders",
    "quality_measures",
    "hospital_claims_outcomes",
}

STAFFING_PARAMETER_IDS = {
    "rn_hours_per_resident_day",
    "total_nurse_hours_per_resident_day",
    "staffing_turnover",
    "therapy_staffing",
}

OUTCOME_PARAMETER_IDS = {
    "quality_measures",
    "hospital_claims_outcomes",
}

PRACTICAL_FIT_PARAMETER_IDS = {
    "languages",
    "transportation",
    "medicare_attributes",
    "medicaid_attributes",
    "payer_information",
    "published_rates",
    "fees",
    "gluten_free",
    "kosher",
    "religious_cultural_services",
    "activities",
}

DISPLAY_PARAMETER_LABELS = {
    "nursing_24_7": "24/7 nursing support",
    "skilled_nursing_capabilities": "Skilled nursing",
    "transfer_assistance": "Transfer assistance",
    "medication_support": "Medication management",
    "adl_support": "Help with daily activities",
    "pt": "Physical therapy",
    "ot": "Occupational therapy",
    "speech_therapy": "Speech therapy",
    "post_stroke_neuro_evidence": "Stroke and neuro rehabilitation",
    "memory_care": "Memory care",
    "dementia_alz_programs": "Memory and dementia support",
    "languages": "Language support",
    "published_rates": "Transparent pricing",
    "transportation": "Transportation support",
    "medicare_attributes": "Medicare acceptance",
}

_DECISION_RESULT_CACHE: Dict[str, Dict[str, Any]] = {}
_DECISION_RESULT_CACHE_ORDER: List[str] = []
_DECISION_RESULT_CACHE_LIMIT = 12


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


def _display_parameter_label(parameter_id: str) -> str:
    return DISPLAY_PARAMETER_LABELS.get(parameter_id, parameter_id.replace("_", " ").strip().title())


def _display_source_label(source: Any) -> str:
    text = _normalize(source)
    if not text:
        return "verified evidence"
    if "cms" in text or "medicare" in text or "survey" in text or "claims" in text:
        return "CMS-verified evidence"
    if "nppes" in text or "taxonomy" in text:
        return "provider taxonomy evidence"
    if "facility" in text or "provider" in text:
        return "facility-reported evidence"
    return "verified evidence"


def _to_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip().replace(",", "")
    if not raw or raw.upper() == "UNKNOWN":
        return None
    if raw.startswith("$"):
        raw = raw[1:]
    if raw.endswith("%"):
        raw = raw[:-1]
    try:
        return float(raw)
    except ValueError:
        return None


def _is_verified_row(row: Dict[str, Any]) -> bool:
    raw = row.get("raw_value")
    source = _normalize(row.get("source"))
    if raw in {None, "UNKNOWN"}:
        return False
    if source in {"", "not verified"}:
        return False
    return True


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


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
    if "24/7" in level or "24x7" in level or "round the clock" in level or "skilled nursing" in level or "complex" in level:
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
    extraction_meta = {"text": text, "recognized_tokens": [], "unrecognized_segments": []}

    def present(token: str) -> bool:
        token = token.lower()
        if token in {"pt", "ot"}:
            return re.search(rf"\b{re.escape(token)}\b", normalized) is not None
        return token in normalized

    explicit_independence = any(phrase in normalized for phrase in (
        "fully independent", "completely independent", "independent with bathing",
        "independent with dressing", "independent with toileting", "independent with transfers",
    ))
    no_adl_support = explicit_independence or any(phrase in normalized for phrase in (
        "no adl support", "no help with daily activities", "does not need help with daily activities",
        "doesn't need help with daily activities", "no personal care support",
    ))
    no_medication_support = ((explicit_independence and present("medication")) or any(phrase in normalized for phrase in (
        "no medication support", "no medication assistance", "does not need medication support", "doesn't need medication support",
    )))
    no_transfer_support = explicit_independence or any(phrase in normalized for phrase in (
        "no mobility limitation", "no mobility limitations", "walks independently", "no transfer assistance", "does not need transfer assistance",
    ))
    no_memory_support = any(phrase in normalized for phrase in (
        "no dementia", "without dementia", "mentally alert", "cognitively intact", "no memory concerns", "no memory concern",
        "does not need cognitive support", "doesn't need cognitive support", "no cognitive support",
    ))
    no_clinical_support = any(phrase in normalized for phrase in (
        "no special medical or nursing needs", "no medical or nursing needs", "does not need nursing support", "doesn't need nursing support",
    ))

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
        (["no dementia", "mentally alert", "no memory concerns", "no cognitive support"], ("memory_care", "PREFERENCE", "NO", ["NO", "UNKNOWN"], "PROGRAM", "natural_language", 0.85, "No dementia-focused unit specifically required")),
    ]
    suppressed_positive = {
        "adl_support": no_adl_support,
        "medication_support": no_medication_support,
        "transfer_assistance": no_transfer_support,
        "memory_care": no_memory_support,
        "nursing_24_7": no_clinical_support,
    }
    for keywords, need_tuple in keyword_rules:
        parameter_id = need_tuple[0]
        desired_value = need_tuple[2]
        if desired_value == "YES" and suppressed_positive.get(parameter_id, False):
            continue
        if any(present(keyword) for keyword in keywords):
            _add_need(needs_by_id, *need_tuple)
            if parameter_id == "nursing_24_7" and not no_clinical_support:
                _add_need(needs_by_id, "skilled_nursing_capabilities", "REQUIRED", "YES", ["YES"], "FACILITY", "natural_language", 0.95, "Skilled nursing capability required")
            extraction_meta["recognized_tokens"].append(keywords[0])

    location_city = None
    for city in ["north las vegas", "las vegas", "henderson", "miami", "hialeah", "doral", "aventura", "homestead", "coral gables", "north miami"]:
        if city in normalized:
            location_city = city.upper()
            extraction_meta["recognized_tokens"].append(city)
            break
    return {"extraction": extraction_meta, "location_city": location_city}

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


def _classify_match_evidence(row: Dict[str, Any]) -> Tuple[str, float]:
    if not _is_verified_row(row):
        return "UNKNOWN", MATCH_EVIDENCE_MULTIPLIER["UNKNOWN"]

    source = _normalize(row.get("source"))
    if "nppes" in source or "taxonomy" in source:
        return "TAXONOMY_INFERRED", MATCH_EVIDENCE_MULTIPLIER["TAXONOMY_INFERRED"]

    if any(token in source for token in ["facility", "self-report", "self report", "provider"]):
        return "FACILITY_REPORTED", MATCH_EVIDENCE_MULTIPLIER["FACILITY_REPORTED"]

    if any(token in source for token in ["cms", "ahca", "medicare", "medicaid", "inspection", "survey", "claims"]):
        return "REGULATORY_VERIFIED", MATCH_EVIDENCE_MULTIPLIER["REGULATORY_VERIFIED"]

    return "VERIFIED", MATCH_EVIDENCE_MULTIPLIER["VERIFIED"]


def _has_taxonomy_only_critical_support(required_or_high_matches: List[Dict[str, Any]]) -> bool:
    if not required_or_high_matches:
        return False
    return any(item.get("evidence_strength") == "TAXONOMY_INFERRED" for item in required_or_high_matches)


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
        row = row_by_param.get(need["parameter_id"]) or {}
        evidence_strength, evidence_multiplier = _classify_match_evidence(row) if status == "MATCH" else ("UNKNOWN", MATCH_EVIDENCE_MULTIPLIER["UNKNOWN"])
        entry = {
            "parameter_id": need["parameter_id"],
            "requirement_level": need["requirement_level"],
            "status": status,
            "reason": reason,
            "evidence_strength": evidence_strength,
            "evidence_multiplier": evidence_multiplier,
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
    required_failures = [entry for entry in unmet_verified_needs if entry["requirement_level"] == "REQUIRED"]
    required_unknown = [entry for entry in unknown_critical_needs if entry["requirement_level"] == "REQUIRED"]
    required_matches = [entry for entry in matched_needs if entry["requirement_level"] == "REQUIRED"]
    required_or_high_matches = [entry for entry in matched_needs if entry["requirement_level"] in {"REQUIRED", "HIGH"}]

    if required_high_failures:
        eligibility = "INELIGIBLE"
    elif required_failures:
        eligibility = "INELIGIBLE"
    elif required_unknown and not required_matches:
        eligibility = "INSUFFICIENT_EVIDENCE"
    elif required_high_unknown and required_high_matches:
        eligibility = "POTENTIALLY_ELIGIBLE"
    elif required_high_unknown and not required_high_matches:
        eligibility = "INSUFFICIENT_EVIDENCE"
    elif _has_taxonomy_only_critical_support(required_or_high_matches):
        eligibility = "POTENTIALLY_ELIGIBLE"
    else:
        eligibility = "ELIGIBLE"

    reasons = []
    if required_high_failures:
        reasons.append("Verified incompatible evidence exists for one or more required/high needs.")
    if required_high_unknown:
        reasons.append("Some required/high needs are not yet verified and need direct confirmation.")
    if _has_taxonomy_only_critical_support(required_or_high_matches):
        reasons.append("One or more required/high needs are supported by taxonomy-level evidence and still need direct capability verification.")
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
    discounted_weight = 0.0
    known_weight = 0.0
    total_weight = 0.0

    for need in needs:
        total_weight += REQUIREMENT_WEIGHTS[need["requirement_level"]]

    proven_critical_matches = 0
    taxonomy_critical_matches = 0
    for item in eligibility["matched_needs"]:
        weight = REQUIREMENT_WEIGHTS[by_id[item["parameter_id"]]["requirement_level"]]
        multiplier = float(item.get("evidence_multiplier", 1.0))
        matched_weight += weight * multiplier
        discounted_weight += weight * (1.0 - multiplier)
        known_weight += weight
        if by_id[item["parameter_id"]]["requirement_level"] in {"REQUIRED", "HIGH"}:
            if item.get("evidence_strength") == "TAXONOMY_INFERRED":
                taxonomy_critical_matches += 1
            else:
                proven_critical_matches += 1

    for item in eligibility["unmet_verified_needs"]:
        weight = REQUIREMENT_WEIGHTS[by_id[item["parameter_id"]]["requirement_level"]]
        unmet_weight += weight
        known_weight += weight

    if matched_weight + unmet_weight + discounted_weight <= 0:
        match_score = 0.0
    else:
        match_score = round((matched_weight / (matched_weight + unmet_weight + discounted_weight)) * 100.0, 2)

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
        "match_evidence_profile": {
            "proven_critical_matches": proven_critical_matches,
            "taxonomy_supported_critical_matches": taxonomy_critical_matches,
            "unknown_critical_needs": len([item for item in eligibility["unknown_critical_needs"] if item["requirement_level"] in {"REQUIRED", "HIGH"}]),
            "verified_gap_critical_needs": len([item for item in eligibility["unmet_verified_needs"] if item["requirement_level"] in {"REQUIRED", "HIGH"}]),
        },
    }


def _build_need_status_map(eligibility: Dict[str, Any]) -> Dict[str, str]:
    statuses: Dict[str, str] = {}
    for item in eligibility.get("matched_needs", []):
        statuses[item["parameter_id"]] = "MATCH"
    for item in eligibility.get("unmet_verified_needs", []):
        statuses[item["parameter_id"]] = "GAP"
    for item in eligibility.get("unknown_critical_needs", []):
        statuses[item["parameter_id"]] = "UNKNOWN"
    return statuses


def _dimension_quality_safety(table_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = {row["parameter_id"]: row for row in table_rows}
    known_signals: List[str] = []
    unknown_signals: List[str] = []
    score = 50.0
    known = 0

    inspection = _to_number((rows.get("inspection_rating") or {}).get("raw_value"))
    if inspection is not None and _is_verified_row(rows["inspection_rating"]):
        known += 1
        score += (inspection - 2.5) * 8.0
        known_signals.append(f"inspection_rating={inspection}")
    else:
        unknown_signals.append("inspection_rating")

    quality_measures = _to_number((rows.get("quality_measures") or {}).get("raw_value"))
    if quality_measures is not None and _is_verified_row(rows["quality_measures"]):
        known += 1
        score += (quality_measures - 10.0) * 1.5
        known_signals.append(f"quality_measures={quality_measures}")
    else:
        unknown_signals.append("quality_measures")

    deficiency_count = _to_number((rows.get("deficiency_count") or {}).get("raw_value"))
    if deficiency_count is not None and _is_verified_row(rows["deficiency_count"]):
        known += 1
        score -= min(deficiency_count * 1.2, 35.0)
        known_signals.append(f"deficiency_count={deficiency_count}")
    else:
        unknown_signals.append("deficiency_count")

    deficiency_severity = _to_number((rows.get("deficiency_severity") or {}).get("raw_value"))
    if deficiency_severity is not None and _is_verified_row(rows["deficiency_severity"]):
        known += 1
        score -= min(deficiency_severity * 8.0, 45.0)
        known_signals.append(f"deficiency_severity={deficiency_severity}")
    else:
        unknown_signals.append("deficiency_severity")

    complaint_related = _to_number((rows.get("complaint_related_findings") or {}).get("raw_value"))
    if complaint_related is not None and _is_verified_row(rows["complaint_related_findings"]):
        known += 1
        score -= min(complaint_related * 2.5, 25.0)
        known_signals.append(f"complaint_related_findings={complaint_related}")
    else:
        unknown_signals.append("complaint_related_findings")

    infection_control = _to_number((rows.get("infection_control_findings") or {}).get("raw_value"))
    if infection_control is not None and _is_verified_row(rows["infection_control_findings"]):
        known += 1
        score -= min(infection_control * 3.0, 30.0)
        known_signals.append(f"infection_control_findings={infection_control}")
    else:
        unknown_signals.append("infection_control_findings")

    fire_safety = _to_number((rows.get("fire_safety_deficiencies") or {}).get("raw_value"))
    if fire_safety is not None and _is_verified_row(rows["fire_safety_deficiencies"]):
        known += 1
        score -= min(fire_safety * 2.0, 20.0)
        known_signals.append(f"fire_safety_deficiencies={fire_safety}")
    else:
        unknown_signals.append("fire_safety_deficiencies")

    penalties_fines = _to_number((rows.get("penalties_fines") or {}).get("raw_value"))
    if penalties_fines is not None and _is_verified_row(rows["penalties_fines"]):
        known += 1
        score -= min(penalties_fines / 5000.0, 20.0)
        known_signals.append(f"penalties_fines={penalties_fines}")
    else:
        unknown_signals.append("penalties_fines")

    payment_denials = _to_number((rows.get("payment_denials") or {}).get("raw_value"))
    if payment_denials is not None and _is_verified_row(rows["payment_denials"]):
        known += 1
        score -= min(payment_denials * 4.0, 20.0)
        known_signals.append(f"payment_denials={payment_denials}")
    else:
        unknown_signals.append("payment_denials")

    sanctions_value = _normalize((rows.get("sanctions_final_orders") or {}).get("raw_value"))
    if sanctions_value and sanctions_value != "unknown" and _is_verified_row(rows["sanctions_final_orders"]):
        known += 1
        if sanctions_value not in {"no", "none", "0"}:
            score -= 35.0
            known_signals.append("sanctions_final_orders=adverse")
        else:
            known_signals.append("sanctions_final_orders=none")
    else:
        unknown_signals.append("sanctions_final_orders")

    if known == 0:
        return {
            "score": None,
            "known_signals": known_signals,
            "unknown_signals": unknown_signals,
        }
    return {
        "score": _clamp_score(score),
        "known_signals": known_signals,
        "unknown_signals": unknown_signals,
    }


def _dimension_staffing(table_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = {row["parameter_id"]: row for row in table_rows}
    known_signals: List[str] = []
    unknown_signals: List[str] = []
    score = 50.0
    known = 0

    rn_hours = _to_number((rows.get("rn_hours_per_resident_day") or {}).get("raw_value"))
    if rn_hours is not None and _is_verified_row(rows["rn_hours_per_resident_day"]):
        known += 1
        score += min(rn_hours * 8.0, 20.0)
        known_signals.append(f"rn_hours_per_resident_day={rn_hours}")
    else:
        unknown_signals.append("rn_hours_per_resident_day")

    total_nurse_hours = _to_number((rows.get("total_nurse_hours_per_resident_day") or {}).get("raw_value"))
    if total_nurse_hours is not None and _is_verified_row(rows["total_nurse_hours_per_resident_day"]):
        known += 1
        score += min(total_nurse_hours * 5.0, 20.0)
        known_signals.append(f"total_nurse_hours_per_resident_day={total_nurse_hours}")
    else:
        unknown_signals.append("total_nurse_hours_per_resident_day")

    turnover = _to_number((rows.get("staffing_turnover") or {}).get("raw_value"))
    if turnover is not None and _is_verified_row(rows["staffing_turnover"]):
        known += 1
        score -= min(turnover * 0.35, 25.0)
        known_signals.append(f"staffing_turnover={turnover}")
    else:
        unknown_signals.append("staffing_turnover")

    therapy_staffing_row = rows.get("therapy_staffing")
    if therapy_staffing_row and _is_verified_row(therapy_staffing_row):
        known += 1
        raw = therapy_staffing_row.get("raw_value")
        if raw == "YES":
            score += 8.0
            known_signals.append("therapy_staffing=YES")
        elif raw == "NO":
            score -= 8.0
            known_signals.append("therapy_staffing=NO")
    else:
        unknown_signals.append("therapy_staffing")

    if known == 0:
        return {
            "score": None,
            "known_signals": known_signals,
            "unknown_signals": unknown_signals,
        }
    return {
        "score": _clamp_score(score),
        "known_signals": known_signals,
        "unknown_signals": unknown_signals,
    }


def _dimension_capability_depth(
    needs: List[Dict[str, Any]],
    eligibility: Dict[str, Any],
    row_by_param: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    need_by_id = {need["parameter_id"]: need for need in needs}
    matched_ids = {item["parameter_id"] for item in eligibility.get("matched_needs", [])}
    known_signals: List[str] = []
    unknown_signals: List[str] = []

    scope_weight = {
        "FACILITY": 1.0,
        "SERVICE": 1.1,
        "PROGRAM": 1.25,
        "UNIT": 1.35,
    }

    points = 0.0
    max_points = 0.0
    known = 0
    for parameter_id in matched_ids:
        need = need_by_id.get(parameter_id)
        row = row_by_param.get(parameter_id)
        if not need or not row or row.get("raw_value") != "YES" or not _is_verified_row(row):
            continue
        req_weight = REQUIREMENT_WEIGHTS.get(need["requirement_level"], 1.0)
        scope = str(row.get("detail_scope") or "FACILITY")
        multiplier = scope_weight.get(scope, 1.0)
        known += 1
        points += req_weight * multiplier
        max_points += req_weight * 1.35
        known_signals.append(f"{parameter_id}@{scope}")

    for need in needs:
        if need["parameter_id"] not in matched_ids and need["parameter_id"] in row_by_param:
            row = row_by_param[need["parameter_id"]]
            if row.get("raw_value") in {"UNKNOWN", None}:
                unknown_signals.append(need["parameter_id"])

    if known == 0 or max_points <= 0:
        return {
            "score": None,
            "known_signals": known_signals,
            "unknown_signals": unknown_signals,
        }
    return {
        "score": _clamp_score((points / max_points) * 100.0),
        "known_signals": known_signals,
        "unknown_signals": unknown_signals,
    }


def _dimension_outcomes(table_rows: List[Dict[str, Any]], needs: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = {row["parameter_id"]: row for row in table_rows}
    known_signals: List[str] = []
    unknown_signals: List[str] = []
    score = 50.0
    known = 0

    quality_measures = _to_number((rows.get("quality_measures") or {}).get("raw_value"))
    if quality_measures is not None and _is_verified_row(rows["quality_measures"]):
        known += 1
        score += (quality_measures - 10.0) * 2.0
        known_signals.append(f"quality_measures={quality_measures}")
    else:
        unknown_signals.append("quality_measures")

    hospital_outcomes = _to_number((rows.get("hospital_claims_outcomes") or {}).get("raw_value"))
    if hospital_outcomes is not None and _is_verified_row(rows["hospital_claims_outcomes"]):
        known += 1
        score -= min(hospital_outcomes * 1.5, 20.0)
        known_signals.append(f"hospital_claims_outcomes={hospital_outcomes}")
    else:
        unknown_signals.append("hospital_claims_outcomes")

    needs_requiring_outcomes = any(
        need["parameter_id"] in {"post_stroke_neuro_evidence", "pt", "ot", "speech_therapy", "nursing_24_7"}
        for need in needs
    )
    if not needs_requiring_outcomes:
        return {
            "score": None,
            "known_signals": known_signals,
            "unknown_signals": unknown_signals,
        }

    if known == 0:
        return {
            "score": None,
            "known_signals": known_signals,
            "unknown_signals": unknown_signals,
        }
    return {
        "score": _clamp_score(score),
        "known_signals": known_signals,
        "unknown_signals": unknown_signals,
    }


def _dimension_practical_fit(
    needs: List[Dict[str, Any]],
    need_statuses: Dict[str, str],
    requested_city: Optional[str],
    facility_city: Optional[str],
) -> Dict[str, Any]:
    known_signals: List[str] = []
    unknown_signals: List[str] = []
    matched = 0.0
    known = 0.0

    for need in needs:
        parameter_id = need["parameter_id"]
        if parameter_id not in PRACTICAL_FIT_PARAMETER_IDS:
            continue
        status = need_statuses.get(parameter_id, "UNKNOWN")
        if status == "MATCH":
            known += 1.0
            matched += 1.0
            known_signals.append(f"{parameter_id}=MATCH")
        elif status == "GAP":
            known += 1.0
            known_signals.append(f"{parameter_id}=GAP")
        else:
            unknown_signals.append(parameter_id)

    if requested_city:
        known += 1.0
        if _normalize(facility_city) == _normalize(requested_city):
            matched += 1.0
            known_signals.append("location_city=MATCH")
        else:
            known_signals.append("location_city=MISMATCH")

    if known <= 0:
        return {
            "score": None,
            "known_signals": known_signals,
            "unknown_signals": unknown_signals,
        }

    return {
        "score": _clamp_score((matched / known) * 100.0),
        "known_signals": known_signals,
        "unknown_signals": unknown_signals,
    }


def _compute_dimensions(
    *,
    needs: List[Dict[str, Any]],
    eligibility: Dict[str, Any],
    table_rows: List[Dict[str, Any]],
    row_by_param: Dict[str, Dict[str, Any]],
    requested_city: Optional[str],
    facility_city: Optional[str],
    match_evidence_certainty: float,
) -> Dict[str, Any]:
    need_statuses = _build_need_status_map(eligibility)
    quality_safety = _dimension_quality_safety(table_rows)
    staffing = _dimension_staffing(table_rows)
    capability_depth = _dimension_capability_depth(needs, eligibility, row_by_param)
    outcomes = _dimension_outcomes(table_rows, needs)
    practical_fit = _dimension_practical_fit(needs, need_statuses, requested_city, facility_city)

    scored_dimensions = [quality_safety, staffing, capability_depth, outcomes, practical_fit]
    available_dimension_count = sum(1 for item in scored_dimensions if item["score"] is not None)
    coverage_ratio = (available_dimension_count / len(scored_dimensions)) * 100.0 if scored_dimensions else 0.0
    evidence_confidence = round((match_evidence_certainty * 0.7) + (coverage_ratio * 0.3), 2)

    return {
        "quality_safety": quality_safety,
        "staffing": staffing,
        "capability_depth": capability_depth,
        "patient_relevant_outcomes": outcomes,
        "practical_fit": practical_fit,
        "evidence_confidence": _clamp_score(evidence_confidence),
    }


def _compare_ranked_facilities(left: Dict[str, Any], right: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    left_eligibility = ELIGIBILITY_ORDER[left["eligibility_status"]]
    right_eligibility = ELIGIBILITY_ORDER[right["eligibility_status"]]
    if left_eligibility != right_eligibility:
        winner = left if left_eligibility < right_eligibility else right
        loser = right if winner is left else left
        return (
            -1 if winner is left else 1,
            {
                "decision_dimension": "eligibility_status",
                    "reason": f"{winner['facility_name']} ranked above {loser['facility_name']} because it has a stronger fit for the current critical needs.",
                "equal_dimensions": [],
                "unknown_dimensions": [],
            },
        )

    comparisons = [
        ("patient_match", "patient_match_score"),
        ("quality_safety", "quality_safety_score"),
        ("staffing", "staffing_score"),
        ("capability_depth", "capability_depth_score"),
        ("patient_relevant_outcomes", "patient_relevant_outcomes_score"),
        ("practical_fit", "practical_fit_score"),
    ]

    equal_dimensions: List[str] = []
    unknown_dimensions: List[str] = []
    for dimension_name, field_name in comparisons:
        left_value = left.get(field_name)
        right_value = right.get(field_name)

        if left_value is None or right_value is None:
            unknown_dimensions.append(dimension_name)
            continue

        threshold = TIE_THRESHOLD_POLICY[dimension_name]
        delta = float(left_value) - float(right_value)
        if abs(delta) <= threshold:
            equal_dimensions.append(dimension_name)
            continue

        winner = left if delta > 0 else right
        loser = right if winner is left else left
        winner_value = left_value if winner is left else right_value
        loser_value = right_value if winner is left else left_value
        return (
            -1 if winner is left else 1,
            {
                "decision_dimension": dimension_name,
                "reason": (
                    f"{winner['facility_name']} ranked above {loser['facility_name']} on verified {dimension_name.replace('_', ' ')} evidence."
                ),
                "equal_dimensions": equal_dimensions,
                "unknown_dimensions": unknown_dimensions,
            },
        )

    if left["facility_name"] < right["facility_name"]:
        deterministic = -1
    elif left["facility_name"] > right["facility_name"]:
        deterministic = 1
    else:
        deterministic = 0

    return (
        0,
        {
            "decision_dimension": "true_tie",
            "reason": "Materially equal across patient match and all governed tie-breaker dimensions with available evidence.",
            "equal_dimensions": equal_dimensions,
            "unknown_dimensions": unknown_dimensions,
            "deterministic_display_order": deterministic,
        },
    )


def _rank_with_true_ties(
    results: List[Dict[str, Any]],
    decision_limit: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    def sort_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
        return (
            ELIGIBILITY_ORDER[item["eligibility_status"]],
            -(item.get("patient_match_score") or 0.0),
            -(item.get("quality_safety_score") or 0.0),
            -(item.get("staffing_score") or 0.0),
            -(item.get("capability_depth_score") or 0.0),
            -(item.get("patient_relevant_outcomes_score") or 0.0),
            -(item.get("practical_fit_score") or 0.0),
            item["facility_name"],
        )

    ranked = sorted(results, key=sort_key)

    if not ranked:
        return ranked, []

    pairwise_decisions: List[Dict[str, Any]] = []
    current_rank = 1
    ranked[0]["rank_position"] = current_rank
    ranked[0]["rank_tie_status"] = "UNIQUE"

    limit = len(ranked) if decision_limit is None else min(len(ranked), max(1, decision_limit))

    for index in range(1, limit):
        previous = ranked[index - 1]
        current = ranked[index]
        compare_result, details = _compare_ranked_facilities(previous, current)
        decision_record = {
            "higher_canonical_facility_id": previous["canonical_facility_id"],
            "lower_canonical_facility_id": current["canonical_facility_id"],
            **details,
        }
        pairwise_decisions.append(decision_record)

        if compare_result == 0:
            current["rank_position"] = previous["rank_position"]
            previous["rank_tie_status"] = "JOINT_RANK"
            current["rank_tie_status"] = "JOINT_RANK"
        else:
            current_rank = index + 1
            current["rank_position"] = current_rank
            current["rank_tie_status"] = "UNIQUE"

    if limit < len(ranked):
        current_rank = ranked[limit - 1]["rank_position"]
        for index in range(limit, len(ranked)):
            current_rank = index + 1
            ranked[index]["rank_position"] = current_rank
            ranked[index]["rank_tie_status"] = "UNIQUE"

    groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for item in ranked:
        groups[item["rank_position"]].append(item)

    for rank_position, items in groups.items():
        if len(items) > 1:
            group_ids = [item["canonical_facility_id"] for item in items]
            for item in items:
                item["rank_tie_status"] = "JOINT_RANK"
                item["rank_display"] = f"Joint #{rank_position}"
                item["tied_with"] = [facility_id for facility_id in group_ids if facility_id != item["canonical_facility_id"]]
        else:
            items[0]["rank_display"] = f"#{rank_position}"
            items[0]["tied_with"] = []

    return ranked, pairwise_decisions


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
        strong.append(f"{_display_parameter_label(item['parameter_id'])} is supported by {_display_source_label(row.get('source'))}")

    verify = []
    for item in eligibility["unknown_critical_needs"][:5]:
        verify.append(f"{_display_parameter_label(item['parameter_id'])} is not yet verified")

    concerns = []
    for item in eligibility["unmet_verified_needs"][:5]:
        concerns.append(f"{_display_parameter_label(item['parameter_id'])} has a verified gap")

    if any(row["parameter_id"] == "current_availability" for row in table_rows):
        verify.append("Current availability must be confirmed directly with the facility")

    return strong, verify, concerns


def _agent_verified_medication_overlay(canonical_ids: List[str]) -> Dict[str, str]:
    """The registry's evidence arbiter (_best_evidence_row) already resolves conflicting
    registry evidence, but it never sees agent-research findings (AgentKnowledgeRecord),
    which live in a separate table populated at request time. This asks that same
    question of the agent's evidence for the current top candidates only (bounded, not
    the full facility universe), so a real verified finding there can resolve what the
    registry alone left UNKNOWN -- one governed answer per fact instead of two silently
    disagreeing ones.

    Only positive confirmations are used. An agent record with medication_support_verified
    == False must never turn into a hard exclusion here: that field is stamped on every
    agent record regardless of which dimension was actually being researched (see
    decision_research_worker.py), so a False is frequently "never checked", not "checked
    and absent". Missing evidence stays UNKNOWN, exactly as before this overlay existed.
    """
    if not canonical_ids:
        return {}
    from sqlalchemy import inspect
    from sqlalchemy.exc import OperationalError

    from app.database import SessionLocal
    from app.models.agent_execution import AgentKnowledgeRecord
    from app.services import governed_evidence_runtime

    db = SessionLocal()
    try:
        # Local/test SQLite databases may not have the agent persistence tables
        # initialized (see decision_agent_bridge.py's _agent_schema_available for the
        # same pattern elsewhere); treat that as "no agent evidence available" rather
        # than a hard failure.
        if AgentKnowledgeRecord.__tablename__ not in inspect(db.get_bind()).get_table_names():
            return {}
        # Deliberately the unfiltered reader (no market or source-trust filter), matching
        # this overlay's behavior before it was extracted: see is_governed_positive_source's
        # docstring for why tightening this to a governed-source-only check is left as an
        # open decision rather than applied here.
        evidence_by_id = governed_evidence_runtime.bulk_agent_evidence(db, canonical_ids)
    except OperationalError:
        return {}
    finally:
        db.close()

    verified: set[str] = set()
    for canonical_id, records in evidence_by_id.items():
        if any((record.get("payload") or {}).get("medication_support_verified") is True for record in records):
            verified.add(canonical_id)
    return {canonical_id: "YES" for canonical_id in verified}


def _build_ranked_candidate_detail(
    *,
    canonical_id: str,
    canonical_meta: Dict[str, Any],
    profile: Dict[str, Any],
    needs: List[Dict[str, Any]],
    recommendation_registry: List[Dict[str, Any]],
    ordered_parameter_ids: List[str],
    medication_overlay: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    table = get_facility_parameter_table(
        canonical_id,
        need_tags=profile["need_tags"],
        priority_parameter_ids=profile["priority_parameter_ids"],
        profile_key=profile["profile_key"],
        ordered_registry=recommendation_registry,
        include_evidence_records=False,
    )
    row_by_param = {row["parameter_id"]: row for row in table["rows"]}
    if (medication_overlay or {}).get(canonical_id) == "YES":
        existing = row_by_param.get("medication_support") or {}
        if str(existing.get("raw_value") or "UNKNOWN").upper() in {"UNKNOWN", ""}:
            row_by_param["medication_support"] = {
                **existing,
                "parameter_id": "medication_support",
                "raw_value": "YES",
                "source": "Agent-verified (governed evidence arbiter)",
            }
    eligibility = _eligibility_from_needs(needs, row_by_param)
    scoring = _score_result(needs, eligibility)
    requested_city = profile.get("location_city")
    geo_note, geo_bonus = _facility_geo_match({"city": table.get("city")}, requested_city)
    strong, verify, concerns = _top_reasons(eligibility, table["rows"])

    dimensions = _compute_dimensions(
        needs=needs,
        eligibility=eligibility,
        table_rows=table["rows"],
        row_by_param=row_by_param,
        requested_city=requested_city,
        facility_city=table.get("city"),
        match_evidence_certainty=scoring["evidence_certainty"],
    )

    quality_safety_score = dimensions["quality_safety"]["score"]
    staffing_score = dimensions["staffing"]["score"]
    capability_depth_score = dimensions["capability_depth"]["score"]
    outcomes_score = dimensions["patient_relevant_outcomes"]["score"]
    practical_fit_score = dimensions["practical_fit"]["score"]
    evidence_confidence = dimensions["evidence_confidence"]

    unknown_dimensions = [
        name
        for name, payload in [
            ("quality_safety", dimensions["quality_safety"]),
            ("staffing", dimensions["staffing"]),
            ("capability_depth", dimensions["capability_depth"]),
            ("patient_relevant_outcomes", dimensions["patient_relevant_outcomes"]),
            ("practical_fit", dimensions["practical_fit"]),
        ]
        if payload["score"] is None
    ]

    match_score = min(100.0, round(scoring["match_score"] + geo_bonus, 2))
    return {
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
        "match_score": match_score,
        "patient_match_score": match_score,
        "match_band": scoring["match_band"],
        "matched_needs": eligibility["matched_needs"],
        "unmet_verified_needs": eligibility["unmet_verified_needs"],
        "unknown_critical_needs": eligibility["unknown_critical_needs"],
        "preference_matches": eligibility["preference_matches"],
        "evidence_certainty": scoring["evidence_certainty"],
        "evidence_confidence": evidence_confidence,
        "quality_safety_score": quality_safety_score,
        "staffing_score": staffing_score,
        "capability_depth_score": capability_depth_score,
        "patient_relevant_outcomes_score": outcomes_score,
        "practical_fit_score": practical_fit_score,
        "domain_breakdown": scoring["domain_breakdown"],
        "match_evidence_profile": scoring["match_evidence_profile"],
        "explanation": {
            "why_matches": strong,
            "needs_verification": verify,
            "concerns": concerns,
            "eligibility_reasons": eligibility["reasons"],
            "availability_note": "Current availability must be confirmed directly with the facility.",
            "location_note": geo_note,
            "quality_safety": {
                "known": dimensions["quality_safety"]["known_signals"],
                "unknown": dimensions["quality_safety"]["unknown_signals"],
            },
            "staffing": {
                "known": dimensions["staffing"]["known_signals"],
                "unknown": dimensions["staffing"]["unknown_signals"],
            },
            "capability_depth": {
                "known": dimensions["capability_depth"]["known_signals"],
                "unknown": dimensions["capability_depth"]["unknown_signals"],
            },
            "patient_relevant_outcomes": {
                "known": dimensions["patient_relevant_outcomes"]["known_signals"],
                "unknown": dimensions["patient_relevant_outcomes"]["unknown_signals"],
            },
            "practical_fit": {
                "known": dimensions["practical_fit"]["known_signals"],
                "unknown": dimensions["practical_fit"]["unknown_signals"],
            },
            "unknown_tie_break_dimensions": unknown_dimensions,
        },
        "parameter_badges": [item["parameter_id"] for item in eligibility["matched_needs"][:6]],
        "comparison_parameter_ids": ordered_parameter_ids,
    }


def run_patient_decision_engine(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str = "",
    limit: int = 50,
) -> Dict[str, Any]:
    cache_enabled = os.getenv("OPTIME_DECISION_RESULT_CACHE", "0") == "1"
    cache_key = json.dumps(
        {
            "questionnaire_state": questionnaire_state,
            "natural_language_query": natural_language_query,
            "limit": limit,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    if cache_enabled:
        cached = _DECISION_RESULT_CACHE.get(cache_key)
        if cached is not None:
            return cached

    profile = build_patient_needs_profile(questionnaire_state, natural_language_query)
    needs = profile["needs"]

    order_payload = get_personalized_parameter_order(
        need_tags=profile["need_tags"],
        priority_parameter_ids=profile["priority_parameter_ids"],
        profile_key=profile["profile_key"],
    )
    ordered_parameters = order_payload.get("ordered_parameters", [])
    ordered_parameter_ids = [row["parameter_id"] for row in ordered_parameters]
    recommendation_parameter_ids = {
        *profile["priority_parameter_ids"],
        *profile["need_tags"],
        *QUALITY_SAFETY_PARAMETER_IDS,
        *STAFFING_PARAMETER_IDS,
        *OUTCOME_PARAMETER_IDS,
        *PRACTICAL_FIT_PARAMETER_IDS,
        "current_availability",
    }
    ordered_registry = [
        {
            "parameter_id": row["parameter_id"],
            "family": row.get("family", "CARE_NURSING"),
            "display_name": row.get("display_name", row["parameter_id"]),
            "applicable_scope": row.get("applicable_scope", "FACILITY"),
        }
        for row in ordered_parameters
    ]
    recommendation_registry = [row for row in ordered_registry if row["parameter_id"] in recommendation_parameter_ids]

    canonical_index = get_canonical_facility_index()
    discovered_ids = get_all_canonical_facility_ids()

    results = []
    requested_city = profile.get("location_city")

    _table_lookup_ms = 0.0
    _scoring_ms = 0.0
    for canonical_id in discovered_ids:
        _t0 = time.perf_counter()
        table = get_facility_parameter_table(
            canonical_id,
            need_tags=profile["need_tags"],
            priority_parameter_ids=profile["priority_parameter_ids"],
            profile_key=profile["profile_key"],
            ordered_registry=recommendation_registry,
            include_evidence_records=False,
            lean=True,
        )
        _t1 = time.perf_counter()
        _table_lookup_ms += (_t1 - _t0) * 1000
        canonical_meta = canonical_index.get(canonical_id, {})
        row_by_param = {row["parameter_id"]: row for row in table["rows"]}

        eligibility = _eligibility_from_needs(needs, row_by_param)
        scoring = _score_result(needs, eligibility)
        geo_note, geo_bonus = _facility_geo_match({"city": table.get("city")}, requested_city)

        # ELIGIBILITY_ORDER always sorts INELIGIBLE facilities after every
        # eligible/potentially-eligible/insufficient-evidence one regardless of these
        # dimension scores, so an ineligible facility only reaches the visible top-N
        # when there aren't enough non-ineligible candidates to fill it -- the common
        # case pays for 4 scoring passes across the whole market to never show them.
        if eligibility["eligibility_status"] == "INELIGIBLE":
            quality_safety_score = None
            staffing_score = None
            capability_depth_score = None
            outcomes_score = None
            practical_fit_score = None
        else:
            quality_safety_score = _dimension_quality_safety(table["rows"])["score"]
            staffing_score = _dimension_staffing(table["rows"])["score"]
            capability_depth_score = _dimension_capability_depth(needs, eligibility, row_by_param)["score"]
            outcomes_score = _dimension_outcomes(table["rows"], needs)["score"]
            practical_fit_score = _dimension_practical_fit(
                needs,
                _build_need_status_map(eligibility),
                requested_city,
                table.get("city"),
            )["score"]

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
                "patient_match_score": min(100.0, round(scoring["match_score"] + geo_bonus, 2)),
                "quality_safety_score": quality_safety_score,
                "staffing_score": staffing_score,
                "capability_depth_score": capability_depth_score,
                "patient_relevant_outcomes_score": outcomes_score,
                "practical_fit_score": practical_fit_score,
            }
        )
        _scoring_ms += (time.perf_counter() - _t1) * 1000

    logger.info(
        "run_patient_decision_engine_loop_breakdown_ms facility_count=%s table_lookup_ms=%s scoring_ms=%s",
        len(discovered_ids),
        round(_table_lookup_ms, 1),
        round(_scoring_ms, 1),
    )

    results, pairwise_decisions = _rank_with_true_ties(results, decision_limit=limit)

    decision_lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for decision in pairwise_decisions:
        key = (
            decision["higher_canonical_facility_id"],
            decision["lower_canonical_facility_id"],
        )
        decision_lookup[key] = decision

    for index, item in enumerate(results):
        if index + 1 < len(results):
            next_item = results[index + 1]
            key = (item["canonical_facility_id"], next_item["canonical_facility_id"])
            forward = decision_lookup.get(key)
            if forward:
                item["tie_break_explanation_vs_next"] = {
                    "why_ranked_above": forward["reason"],
                    "deciding_dimension": forward["decision_dimension"],
                    "remained_equal": forward.get("equal_dimensions", []),
                    "remaining_unknown": forward.get("unknown_dimensions", []),
                }
            else:
                item["tie_break_explanation_vs_next"] = {
                    "why_ranked_above": "Materially tied after all governed dimensions.",
                    "deciding_dimension": "true_tie",
                    "remained_equal": list(TIE_THRESHOLD_POLICY.keys()),
                    "remaining_unknown": item.get("explanation", {}).get("unknown_tie_break_dimensions", []),
                }
        else:
            item["tie_break_explanation_vs_next"] = None

    top = results[: max(10, limit)]

    medication_overlay = _agent_verified_medication_overlay(
        [item["canonical_facility_id"] for item in top]
    )

    detailed_top = []
    for item in top:
        detail = _build_ranked_candidate_detail(
            canonical_id=item["canonical_facility_id"],
            canonical_meta=canonical_index.get(item["canonical_facility_id"], {}),
            profile=profile,
            needs=needs,
            recommendation_registry=recommendation_registry,
            ordered_parameter_ids=ordered_parameter_ids,
            medication_overlay=medication_overlay,
        )
        detail["rank_position"] = item.get("rank_position")
        detail["rank_tie_status"] = item.get("rank_tie_status")
        detail["rank_display"] = item.get("rank_display")
        detail["tied_with"] = item.get("tied_with", [])
        detail["tie_break_explanation_vs_next"] = item.get("tie_break_explanation_vs_next")
        detailed_top.append(detail)

    result = {
        "patient_needs_profile": profile,
        "results": detailed_top[:limit],
        "result_count": len(detailed_top[:limit]),
        "total_candidates_scored": len(results),
        "availability_policy": "Current availability must be confirmed directly with the facility.",
        "tie_break_policy": {
            "thresholds": TIE_THRESHOLD_POLICY,
            "true_tie_label": "JOINT_RANK / TIED",
            "notes": [
                "UNKNOWN availability is neutral and never improves or reduces ranking.",
                "Evidence confidence is displayed separately and is not a ranking point.",
                "Missing values do not grant tie-break advantage.",
            ],
        },
        "tie_break_decisions": pairwise_decisions[: max(10, limit)],
    }

    if cache_enabled:
        _DECISION_RESULT_CACHE[cache_key] = result
        _DECISION_RESULT_CACHE_ORDER.append(cache_key)
        if len(_DECISION_RESULT_CACHE_ORDER) > _DECISION_RESULT_CACHE_LIMIT:
            stale_key = _DECISION_RESULT_CACHE_ORDER.pop(0)
            _DECISION_RESULT_CACHE.pop(stale_key, None)
    return result


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