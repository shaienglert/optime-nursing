from app.services.patient_decision_engine import build_patient_needs_profile
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.client_statement_accounting import split_user_statements

try:
    from .interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, need_values, statement
except ImportError:  # pragma: no cover - direct pytest module import
    from interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, need_values, statement

CLIENT_TEXT = "My mother is 82 and is looking for senior living in Las Vegas. She is fully independent with bathing, dressing, toileting, transfers, medications, decision-making and memory. She has no memory concerns, does not need cognitive support, has no mobility limitation, and has no special medical or nursing needs. Her total monthly budget is up to $8,000."

# Single authority (owner, 2026-10-01): free text reaches the decision only as the
# interpreter's questionnaire_patch -> AI_EXTRACTED Structured Profile fields. This is the
# patch the interpreter returns for CLIENT_TEXT: explicit independence, no memory concern,
# no medical needs, Las Vegas, $8,000.
INDEPENDENT_PATCH = {
    "relationship": "Mom",
    "ageGroup": "80-84",
    "assistanceLevel": "Fully independent",
    "memoryStatus": "No",
    "budget": 8000,
    "referenceLocationValue": "Las Vegas",
    "medicalCareProfile": {"hasOngoingMedicalNeeds": "No", "mobilityMethod": "Independent", "transferAssistance": "No"},
}


def test_explicit_independence_does_not_become_positive_care_needs():
    packet = interpreter_packet(
        INDEPENDENT_PATCH,
        [statement(CLIENT_TEXT, ["assistanceLevel", "memoryStatus", "medicalCareProfile.hasOngoingMedicalNeeds", "budget", "referenceLocationValue"])],
    )
    with interpreter_returning(packet):
        profile = build_patient_needs_profile({}, CLIENT_TEXT)
    assert profile["canonical_structured_profile"]["fields"]["assistanceLevel"]["provenance"] == "AI_EXTRACTED"
    needs = {row["parameter_id"]: row for row in profile["needs"]}
    for forbidden in ("adl_support", "medication_support", "transfer_assistance", "ot", "memory_care"):
        assert not (forbidden in needs and needs[forbidden].get("desired_value") == "YES"), (forbidden, needs.get(forbidden))
    # The city stated in the text arrives as the interpreter's location field.
    assert profile["canonical_structured_profile"]["fields"]["referenceLocationValue"]["provenance"] == "AI_EXTRACTED"
    assert profile["canonical_decision_questionnaire"]["referenceLocationValue"] == "Las Vegas"


def test_interpreted_city_reaches_the_needs_profile_location():
    # Split from the test above so the needs contract stays green. Known app gap (left
    # failing on purpose, no backend/app change allowed here): the needs profile's
    # location_city is read only from locationCity/location_city/city
    # (decision_engine_evidence._explicit_location_city), never from referenceLocationValue
    # or referenceAddress -- the keys both the interpreter's questionnaire_patch and the
    # real intake write. It used to be filled only by the regex reading of the free text.
    packet = interpreter_packet(INDEPENDENT_PATCH, [statement(CLIENT_TEXT, ["referenceLocationValue"])])
    with interpreter_returning(packet):
        profile = build_patient_needs_profile({}, CLIENT_TEXT)
    assert profile["location_city"] == "LAS VEGAS"


def test_independence_text_without_the_interpreter_changes_no_decision_fact():
    # Negation parsing used to live in the regex reader; it is now the Live Golden
    # Interpreter set's responsibility. With AI off the text is UNPROCESSED: no fact at all.
    with interpreter_off():
        baseline = decision_facts(build_patient_needs_profile({}, ""))
        profile = build_patient_needs_profile({}, CLIENT_TEXT)
    assert decision_facts(profile) == baseline
    assert profile["decision_intelligence"]["human_intelligence"]["intake_resolution"]["unprocessed_narrative"] is True


def test_strategy_respects_independence_and_memory_negation():
    strategy = build_living_strategy_context({}, CLIENT_TEXT)
    assert strategy["signals"]["adl_support_needed"] is False
    assert strategy["signals"]["medication_support_needed"] is False
    assert strategy["signals"]["no_dementia"] is True

def test_currency_comma_is_not_split_into_fake_statement():
    statements = split_user_statements(CLIENT_TEXT)
    assert any("$8,000" in statement for statement in statements)
    assert "000" not in statements


def test_negated_dialysis_wound_and_oxygen_do_not_become_required_needs():
    # Reproduces a live finding: "no dialysis, no wounds" was matched purely by the
    # substring "dialysis"/"wound" appearing in the text, with no negation handling
    # for these three keywords specifically (unlike ADL/medication/transfer/memory/
    # 24-7-nursing, which already have a suppressed_positive entry). A fully
    # independent client with no dialysis need was shown a REQUIRED dialysis
    # arrangements need purely because the word "dialysis" appeared in "no dialysis".
    text = (
        "My father is 73, fully independent, no dialysis, no wounds needing care, "
        "not on oxygen, no falls, budget is $4,500 a month."
    )
    profile = build_patient_needs_profile({}, text)
    needs = {row["parameter_id"]: row for row in profile["needs"]}
    for forbidden in ("dialysis_arrangements", "wound_care", "respiratory_trach_vent"):
        assert not (forbidden in needs and needs[forbidden].get("desired_value") == "YES"), (forbidden, needs.get(forbidden))


AFFIRMED_TEXT = "My mother needs dialysis three times a week, has a wound needing daily wound care, and uses continuous oxygen."
AFFIRMED_PATCH = {
    "relationship": "Mom",
    "medicalCareProfile": {
        "hasOngoingMedicalNeeds": "Yes",
        "needs": ["Dialysis", "Wound care", "Oxygen"],
        "dialysisFrequency": "Three times a week",
        "woundCareFrequency": "Daily",
        "oxygenUse": "Continuously",
    },
}


def test_affirmed_dialysis_wound_and_oxygen_still_become_required_needs():
    # Genuine positive mentions reach the decision through the interpreter's patch.
    packet = interpreter_packet(AFFIRMED_PATCH, [statement(AFFIRMED_TEXT, ["medicalCareProfile.needs"])])
    with interpreter_returning(packet):
        profile = build_patient_needs_profile({}, AFFIRMED_TEXT)
    assert profile["canonical_structured_profile"]["fields"]["medicalCareProfile.needs"]["provenance"] == "AI_EXTRACTED"
    needs = {row["parameter_id"]: row for row in profile["needs"]}
    assert needs["dialysis_arrangements"]["desired_value"] == "YES"
    assert needs["wound_care"]["desired_value"] == "YES"
    assert needs["respiratory_trach_vent"]["desired_value"] == "YES"


def test_affirmed_clinical_text_without_the_interpreter_changes_no_decision_fact():
    with interpreter_off():
        baseline = decision_facts(build_patient_needs_profile({}, ""))
        profile = build_patient_needs_profile({}, AFFIRMED_TEXT)
    assert decision_facts(profile) == baseline
    for need in ("dialysis_arrangements", "wound_care", "respiratory_trach_vent"):
        assert need_values(profile).get(need) != "YES", need
