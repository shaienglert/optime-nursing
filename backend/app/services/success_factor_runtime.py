from __future__ import annotations

"""Runtime bridge for the approved Resident–Senior Living Success Factors Canon.

The research canon explicitly forbids converting literature findings into invented
numeric product weights. This module therefore connects the canon to production as
an auditable decision policy: every canonical factor is present, its resident and
facility evidence state is explicit, and its authorized influence class is recorded.
UNKNOWN remains UNKNOWN. Existing governed care/safety matching remains the source
of eligibility and quantitative evidence scoring.
"""

from typing import Any, Dict, Iterable, List, Optional

from app.services.facility_parameter_service import get_facility_parameter_table

CANON_VERSION = "resident-senior-living-success-factors-v1"
INFLUENCE_VERSION = "recommendation-influence-model-v1"
CANON_REFERENCE = "reports/RESIDENT_SENIOR_LIVING_SUCCESS_FACTORS_CANON_V1.md"
INFLUENCE_REFERENCE = "reports/RECOMMENDATION_INFLUENCE_MODEL_V1.md"
NBQ_REFERENCE = "reports/RECOMMENDATION_REQUIRED_DATA_AND_NBQ_V1.md"

# factor_key, display_name, influence_class, authorized role
FACTOR_POLICY = (
    ("clinical_capability_fit", "Clinical Capability Fit", "HARD_GATE", "eligibility"),
    ("decision_participation", "Decision Participation / Move Voluntariness", "HIGH", "transition_support"),
    ("transition_preparation", "Transition Preparation / Expectation Realism", "HIGH", "transition_support"),
    ("functional_cognitive_fit", "Functional & Cognitive Care-Needs Fit", "HIGH_OR_HARD_GATE", "eligibility_and_ordering"),
    ("autonomy_choice_fit", "Autonomy / Choice Fit", "HIGH", "ordering_when_evidenced"),
    ("preference_congruence", "Preference Congruence / Person-Centred Daily Life", "MEDIUM_HIGH", "ordering_when_evidenced"),
    ("resident_staff_relationship", "Resident–Staff Relationship Capability", "HIGH", "ordering_when_evidenced"),
    ("family_connection_visitability", "Family Connection / Visitability", "MEDIUM_HIGH", "ordering_when_evidenced"),
    ("family_staff_communication", "Family–Staff Communication Fit", "MEDIUM_HIGH", "ordering_when_evidenced"),
    ("social_connection_engagement", "Social Connection / Meaningful Engagement Fit", "HIGH_MEDIUM", "ordering_when_evidenced"),
    ("social_climate", "Social Climate: Cohesion vs Conflict", "HIGH", "ordering_when_evidenced"),
    ("sense_of_home_privacy", "Sense-of-Home / Privacy / Personalization Fit", "MEDIUM", "ordering_when_explicit_and_evidenced"),
    ("staffing_stability", "Staffing Stability / Consistency", "HIGH", "quality_layer"),
    ("staffing_sufficiency", "Staffing Sufficiency / Skill Mix", "HIGH", "safety_and_capability"),
    ("facility_quality_safety", "Verified Facility Quality / Safety History", "HARD_GATE_OR_HIGH", "safety_and_ordering"),
    ("continuum_relocation_risk", "Multiple-Relocation / Continuum-of-Care Risk", "MEDIUM_HIGH", "ordering_when_evidenced"),
)

RESEARCH_ONLY_FACTORS = (
    "facility_size_as_independent_quality_factor",
    "ownership_chain_profit_as_independent_quality_factor",
    "generic_personality_match",
    "unvalidated_placement_success_probability",
)


def _nested(payload: Dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _text(value: Any) -> str:
    return str(value or "").strip()


def _known(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return bool([item for item in value if _text(item)])
    return _text(value).lower() not in {"", "unknown", "not sure", "unsure"}


def _known_values(values: Iterable[Any]) -> List[str]:
    return [_text(value) for value in values if _known(value)]


def _resident_factor_state(questionnaire: Dict[str, Any], profile: Dict[str, Any], factor_key: str) -> Dict[str, Any]:
    hi = questionnaire.get("humanIntelligenceV2") if isinstance(questionnaire.get("humanIntelligenceV2"), dict) else {}
    social = hi.get("socialProfile") if isinstance(hi.get("socialProfile"), dict) else {}
    family = hi.get("familyProfile") if isinstance(hi.get("familyProfile"), dict) else {}
    family_culture = hi.get("familyCultureProfile") if isinstance(hi.get("familyCultureProfile"), dict) else {}
    personality = hi.get("personalityProfile") if isinstance(hi.get("personalityProfile"), dict) else {}
    independence = hi.get("independenceProfile") if isinstance(hi.get("independenceProfile"), dict) else {}
    transition = hi.get("transitionRiskProfile") if isinstance(hi.get("transitionRiskProfile"), dict) else {}
    future = hi.get("futureCareProfile") if isinstance(hi.get("futureCareProfile"), dict) else {}
    distance = hi.get("distanceProfile") if isinstance(hi.get("distanceProfile"), dict) else {}
    language = hi.get("languageProfile") if isinstance(hi.get("languageProfile"), dict) else {}
    food = hi.get("foodProfile") if isinstance(hi.get("foodProfile"), dict) else {}
    cultural = hi.get("culturalProfile") if isinstance(hi.get("culturalProfile"), dict) else {}

    needs = profile.get("needs") if isinstance(profile.get("needs"), list) else []
    if factor_key == "clinical_capability_fit":
        relevant = [item for item in needs if str(item.get("requirement_level") or "") in {"REQUIRED", "HIGH"}]
        return {"status": "KNOWN" if relevant else "NO_EXPLICIT_HIGH_NEED", "evidence": relevant}
    if factor_key == "functional_cognitive_fit":
        values = _known_values((questionnaire.get("assistanceLevel"), questionnaire.get("memoryStatus")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "decision_participation":
        values = _known_values((transition.get("attitudeTowardMove"), family_culture.get("decisionRole"), family.get("familyDecisionDynamics")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "transition_preparation":
        values = _known_values((transition.get("biggestFear"), transition.get("previousMoves"), transition.get("attitudeTowardMove")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "autonomy_choice_fit":
        values = _known_values((independence.get("drivingImportance"), independence.get("cookingImportance"), independence.get("abilityToLeaveIndependently"), independence.get("hostingFamilyImportance"), personality.get("structureFlexibilityPreference")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "preference_congruence":
        values = _known_values((language.get("preferredSpokenLanguage"), personality.get("privacyImportance"), personality.get("communitySizePreference"), *(food.get("dietaryPreferences") or []), *(questionnaire.get("happinessPreferences") or [])))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "resident_staff_relationship":
        values = _known_values((social.get("preferredSocialIntensity"), transition.get("biggestFear")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "family_connection_visitability":
        values = _known_values((family.get("visitFrequencyExpectation"), distance.get("familyVisitExpectation"), questionnaire.get("distanceFromFamily"), questionnaire.get("referenceAddress")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "family_staff_communication":
        values = _known_values((family_culture.get("involvementExpectation"), family_culture.get("decisionRole"), family.get("familyDecisionDynamics")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key in {"social_connection_engagement", "social_climate"}:
        values = _known_values((social.get("socialInteractionFrequency"), social.get("newFriendsImportance"), social.get("preferredSocialIntensity"), family.get("socialInteractionNeed"), transition.get("lonelinessRisk"), transition.get("socialIsolationConcern"), *(social.get("hobbyParticipation") or []), *(questionnaire.get("happinessPreferences") or [])))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key == "sense_of_home_privacy":
        values = _known_values((personality.get("privacyImportance"), *(cultural.get("whatFeelsLikeHome") or []), independence.get("hostingFamilyImportance")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    if factor_key in {"staffing_stability", "staffing_sufficiency", "facility_quality_safety"}:
        return {"status": "NOT_RESIDENT_INPUT", "evidence": []}
    if factor_key == "continuum_relocation_risk":
        values = _known_values((future.get("agingInPlaceImportance"), future.get("avoidFutureMovesPreference"), future.get("continuumOfCarePreference"), questionnaire.get("futureCarePreference")))
        return {"status": "KNOWN" if values else "UNKNOWN", "evidence": values}
    return {"status": "UNKNOWN", "evidence": []}


FACILITY_FACTOR_PARAMETERS: Dict[str, tuple[str, ...]] = {
    "clinical_capability_fit": ("adl_support", "medication_support", "transfer_assistance", "nursing_24_7", "memory_care", "pt", "ot", "speech_therapy"),
    "functional_cognitive_fit": ("adl_support", "transfer_assistance", "memory_care", "dementia_alz_programs"),
    "autonomy_choice_fit": ("transportation", "private_shared_rooms"),
    "preference_congruence": ("languages", "gluten_free", "kosher", "religious_cultural_services", "activities", "transportation", "private_shared_rooms"),
    "resident_staff_relationship": ("staffing_turnover",),
    "family_connection_visitability": ("transportation",),
    "family_staff_communication": (),
    "social_connection_engagement": ("activities", "transportation"),
    "social_climate": (),
    "sense_of_home_privacy": ("private_shared_rooms", "activities"),
    "staffing_stability": ("staffing_turnover",),
    "staffing_sufficiency": ("rn_hours_per_resident_day", "total_nurse_hours_per_resident_day", "therapy_staffing"),
    "facility_quality_safety": ("inspection_rating", "deficiency_count", "deficiency_severity", "complaint_related_findings", "penalties_fines", "sanctions_final_orders"),
    "continuum_relocation_risk": ("continuum_of_care", "memory_care", "skilled_nursing_capabilities"),
}


def _facility_factor_state(canonical_id: str, factor_key: str) -> Dict[str, Any]:
    parameter_ids = FACILITY_FACTOR_PARAMETERS.get(factor_key, ())
    if factor_key in {"decision_participation", "transition_preparation"}:
        return {"status": "RESIDENT_TRANSITION_FACTOR", "evidence": []}
    if not parameter_ids:
        return {"status": "UNKNOWN", "evidence": [], "reason": "No governed facility parameter is currently mapped for this factor."}
    try:
        table = get_facility_parameter_table(canonical_id, priority_parameter_ids=list(parameter_ids), include_evidence_records=False)
    except KeyError:
        return {"status": "UNKNOWN", "evidence": [], "reason": "Facility not found in canonical parameter runtime."}
    known_rows = []
    for row in table.get("rows") or []:
        if row.get("parameter_id") not in parameter_ids:
            continue
        raw = row.get("raw_value")
        source = str(row.get("source") or "")
        if raw in (None, "", "UNKNOWN") or source in {"", "Not verified"}:
            continue
        known_rows.append({
            "parameter_id": row.get("parameter_id"),
            "value": raw,
            "source": source,
            "last_verified": row.get("last_verified"),
            "evidence_strength": row.get("evidence_strength"),
        })
    return {
        "status": "KNOWN" if known_rows else "UNKNOWN",
        "evidence": known_rows,
        "requested_parameters": list(parameter_ids),
    }


def build_success_factor_trace(
    questionnaire_state: Dict[str, Any],
    patient_profile: Dict[str, Any],
    recommendation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    canonical_id = str((recommendation or {}).get("canonical_facility_id") or "")
    factors: List[Dict[str, Any]] = []
    for factor_key, name, influence, role in FACTOR_POLICY:
        resident_state = _resident_factor_state(questionnaire_state, patient_profile, factor_key)
        facility_state = _facility_factor_state(canonical_id, factor_key) if canonical_id else {"status": "NOT_EVALUATED_PRE_SEARCH", "evidence": []}
        rank_effect = "NONE"
        if factor_key in {"clinical_capability_fit", "functional_cognitive_fit"}:
            rank_effect = "CORE_ELIGIBILITY_AND_MATCHING"
        elif factor_key == "facility_quality_safety":
            rank_effect = "CORE_SAFETY_REGULATORY"
        elif factor_key in {"staffing_stability", "staffing_sufficiency"}:
            rank_effect = "CORE_WHEN_VERIFIED"
        elif factor_key == "preference_congruence":
            rank_effect = "CORE_PERSONAL_PARAMETERS_WHEN_EXPLICIT_AND_VERIFIED"
        elif resident_state.get("status") == "KNOWN" and facility_state.get("status") == "KNOWN" and role.startswith("ordering"):
            rank_effect = "ELIGIBLE_FOR_GOVERNED_ORDERING_NOT_NUMERIC_WEIGHT"

        factors.append({
            "factor_key": factor_key,
            "factor": name,
            "influence_class": influence,
            "authorized_role": role,
            "resident_state": resident_state,
            "facility_state": facility_state,
            "rank_effect": rank_effect,
        })

    return {
        "canon_version": CANON_VERSION,
        "influence_version": INFLUENCE_VERSION,
        "policy_references": [CANON_REFERENCE, INFLUENCE_REFERENCE, NBQ_REFERENCE],
        "factors": factors,
        "research_only_not_ranked": list(RESEARCH_ONLY_FACTORS),
        "policy": {
            "unknown_is_not_mismatch": True,
            "no_unvalidated_numeric_success_weights": True,
            "facility_size_is_not_independent_quality": True,
            "explicit_legitimate_preference_may_be_used_for_congruence": True,
        },
    }


def summarize_trace(trace: Dict[str, Any]) -> Dict[str, Any]:
    factors = trace.get("factors") or []
    known_both = [f["factor_key"] for f in factors if (f.get("resident_state") or {}).get("status") == "KNOWN" and (f.get("facility_state") or {}).get("status") == "KNOWN"]
    facility_unknown = [f["factor_key"] for f in factors if (f.get("facility_state") or {}).get("status") == "UNKNOWN"]
    resident_unknown = [f["factor_key"] for f in factors if (f.get("resident_state") or {}).get("status") == "UNKNOWN"]
    return {
        "known_on_both_sides": known_both,
        "facility_evidence_unknown": facility_unknown,
        "resident_input_unknown": resident_unknown,
        "research_only_not_ranked": trace.get("research_only_not_ranked") or [],
    }


__all__ = [
    "CANON_VERSION",
    "INFLUENCE_VERSION",
    "FACTOR_POLICY",
    "build_success_factor_trace",
    "summarize_trace",
]
