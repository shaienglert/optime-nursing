from app.services.semantic_intent_ai import _ground_clinical_patch
from app.services.decision_engine_core import build_patient_needs_profile


def packet():
    return {"questionnaire_patch": {"assistanceLevel": "Skilled nursing care", "medicalCareProfile": {"needs": ["Nursing supervision", "Complex medication management", "Wound care"]}}}


def test_supervision_and_reminders_do_not_create_high_acuity_fields():
    result = _ground_clinical_patch(packet(), "She needs supervision 24/7 and reminders to take pills. She needs wound care.", {})
    assert result["questionnaire_patch"]["medicalCareProfile"]["needs"] == ["Wound care"]
    assert "assistanceLevel" not in result["questionnaire_patch"]
    assert len(result["clinical_fact_validation"]["omitted_unsupported_fields"]) == 3


def test_explicit_clinical_facts_survive_an_unrelated_denial():
    result = _ground_clinical_patch(packet(), "No dementia; needs skilled nursing and complex medication management.", {})
    assert result == packet()


def test_explicit_structured_selections_are_preserved():
    state = {"medicalCareProfile": {"needs": ["Nursing supervision", "Complex medication management"]}}
    assert _ground_clinical_patch(packet(), "", state) == packet()


def test_negated_nursing_does_not_ground_an_ai_inference():
    result = _ground_clinical_patch(packet(), "No skilled nursing. Supervision around the clock.", {})
    assert "Nursing supervision" not in result["questionnaire_patch"]["medicalCareProfile"]["needs"]


def test_rehabilitation_does_not_invent_speech_therapy():
    state = {"humanIntelligenceV2": {"transitionRiskProfile": {"postHospitalRehabNeed": "Required"}}}
    profile = build_patient_needs_profile(state, "Rehabilitation after hip replacement.")
    assert "speech_therapy" not in {need["parameter_id"] for need in profile["needs"]}
    explicit = build_patient_needs_profile(state, "Needs speech therapy after a stroke.")
    assert "speech_therapy" in {need["parameter_id"] for need in explicit["needs"]}
    denied = build_patient_needs_profile(state, "Hip rehabilitation. No speech or swallowing problems.")
    assert "speech_therapy" not in {need["parameter_id"] for need in denied["needs"]}


def test_live_dementia_case_denies_nursing_without_losing_memory_care():
    profile = build_patient_needs_profile({}, "Diagnosed dementia, wandering, needs 24/7 supervision. She has no skilled nursing procedures.")
    parameters = {need["parameter_id"] for need in profile["needs"]}
    assert "memory_care" in parameters
    assert not parameters.intersection({"nursing_24_7", "skilled_nursing_capabilities"})
    positive = build_patient_needs_profile({}, "Mother has no skilled nursing needs; father needs skilled nursing.")
    assert "nursing_24_7" in {need["parameter_id"] for need in positive["needs"]}


def test_live_wound_case_preserves_explicit_skilled_dressing_changes():
    profile = build_patient_needs_profile({}, "A wound requiring daily skilled dressing changes.")
    assert "wound_care" in {need["parameter_id"] for need in profile["needs"]}
