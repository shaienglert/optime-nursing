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
