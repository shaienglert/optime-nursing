from app.services.patient_decision_engine import build_patient_needs_profile

try:
    from .interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, statement
except ImportError:  # pragma: no cover - direct module import
    from interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, statement

WOUND_TEXT = "pressure wound on her heel that needs daily dressing changes"


def test_stated_wound_need_is_high():
    # Single authority (owner, 2026-10-01): the narrative becomes a need only through the
    # interpreter's questionnaire_patch (AI_EXTRACTED Structured Profile field).
    packet = interpreter_packet(
        {"medicalCareProfile": {"hasOngoingMedicalNeeds": "Yes", "needs": ["Wound care"], "woundCareFrequency": "Daily"}},
        [statement(WOUND_TEXT, ["medicalCareProfile.needs", "medicalCareProfile.woundCareFrequency"])],
    )
    with interpreter_returning(packet):
        profile = build_patient_needs_profile({}, WOUND_TEXT)
    assert profile["canonical_structured_profile"]["fields"]["medicalCareProfile.needs"]["provenance"] == "AI_EXTRACTED"
    needs = {n['parameter_id']: n for n in profile['needs']}
    assert needs['wound_care']['requirement_level'] == 'HIGH'


def test_stated_wound_text_without_the_interpreter_adds_no_need():
    with interpreter_off():
        baseline = decision_facts(build_patient_needs_profile({}, ""))
        profile = build_patient_needs_profile({}, WOUND_TEXT)
    assert decision_facts(profile) == baseline
    assert 'wound_care' not in {n['parameter_id'] for n in profile['needs']}


def test_negated_wound_need_is_not_added():
    profile = build_patient_needs_profile({}, "She has no pressure wound and does not need dressing changes.")
    assert 'wound_care' not in {n['parameter_id'] for n in profile['needs']}


def test_negated_dressing_changes_are_not_wound_evidence():
    profile = build_patient_needs_profile({}, "She needs no daily dressing changes.")
    assert "wound_care" not in {n["parameter_id"] for n in profile["needs"]}
