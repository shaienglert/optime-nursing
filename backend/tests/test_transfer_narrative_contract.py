from app.services.patient_decision_engine import build_patient_needs_profile

try:
    from .interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, statement
except ImportError:  # pragma: no cover - direct module import
    from interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, statement

TRANSFER_TEXT = "She needs one person to help her get in and out of bed and the shower."


def _interpreted_transfer(text, answer):
    packet = interpreter_packet(
        {"medicalCareProfile": {"transferAssistance": answer}},
        [statement(text, ["medicalCareProfile.transferAssistance"])],
    )
    with interpreter_returning(packet):
        profile = build_patient_needs_profile({}, text)
    assert profile["canonical_structured_profile"]["fields"]["medicalCareProfile.transferAssistance"]["provenance"] == "AI_EXTRACTED"
    return {n['parameter_id']: n for n in profile['needs']}


def _button_transfer(answer):
    with interpreter_off():
        profile = build_patient_needs_profile({"medicalCareProfile": {"transferAssistance": answer}}, "")
    return {n['parameter_id']: n for n in profile['needs']}


def test_stated_transfer_need_matches_the_structured_answer():
    # Single authority (owner, 2026-10-01): the narrative becomes a need only through the
    # interpreter's questionnaire_patch (AI_EXTRACTED Structured Profile field), and then
    # weighs exactly what the same button answer weighs.
    needs = _interpreted_transfer(TRANSFER_TEXT, "One person")
    # Was 'HIGH' (the regex gave any transfer wording HIGH). Under the owner rule the
    # interpreted "One person" is the same fact as the button "One person", which the
    # canonical mapping (_map_structured_follow_ups) weighs MEDIUM; HIGH is two people/lift.
    assert needs['transfer_assistance']['requirement_level'] == 'MEDIUM'
    assert needs['transfer_assistance']['requirement_level'] == _button_transfer("One person")['transfer_assistance']['requirement_level']


def test_stated_two_person_transfer_need_is_high():
    text = "She needs two people to help her get in and out of bed and the shower."
    assert _interpreted_transfer(text, "Two people")['transfer_assistance']['requirement_level'] == 'HIGH'


def test_stated_transfer_text_without_the_interpreter_adds_no_need():
    with interpreter_off():
        baseline = decision_facts(build_patient_needs_profile({}, ""))
        profile = build_patient_needs_profile({}, TRANSFER_TEXT)
    assert decision_facts(profile) == baseline
    assert 'transfer_assistance' not in {n['parameter_id'] for n in profile['needs']}


def test_negated_transfer_need_is_not_added():
    profile = build_patient_needs_profile({}, "She does not need one person to help her get in and out of bed and the shower.")
    assert 'transfer_assistance' not in {n['parameter_id'] for n in profile['needs']}


def test_negated_help_getting_out_of_bed_is_not_a_transfer_need():
    profile = build_patient_needs_profile({}, "She does not need help getting out of bed.")
    assert "transfer_assistance" not in {n["parameter_id"] for n in profile["needs"]}
