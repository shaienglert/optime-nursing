from app.services.care_input_assertions import extract_care_denials
from app.services.client_statement_accounting import account_user_input
from app.services import decision_engine_core as core


def need_ids(story: str):
    return {row["parameter_id"] for row in core.build_patient_needs_profile({}, story)["needs"]}


def test_does_not_need_memory_care_does_not_create_memory_need():
    assert "memory_care" not in need_ids("She does not need memory care.")


def test_does_not_need_bathing_help_does_not_create_adl_need():
    assert "adl_support" not in need_ids("She does not need help with bathing.")


def test_does_not_need_medication_help_does_not_create_medication_need():
    assert "medication_support" not in need_ids("She doesn't need help with her medications.")


def test_fully_independent_but_explicit_bathing_help_is_not_silenced():
    story = "She is fully independent but needs help with bathing."
    assert extract_care_denials(story)["adl"] is False
    assert "adl_support" in need_ids(story)


def test_independent_with_bathing_remains_a_denial_of_bathing_help():
    story = "She is fully independent with bathing and dressing."
    assert extract_care_denials(story)["adl"] is True
    assert "adl_support" not in need_ids(story)


def test_past_need_is_not_a_current_requirement():
    assert "adl_support" not in need_ids("She used to need help with bathing, but she recovered completely.")


def test_future_need_is_not_a_current_requirement():
    assert "adl_support" not in need_ids("We expect she will need help with bathing within a year.")


def test_other_relative_need_is_not_assigned_to_search_subject():
    story = "My mother is fully independent. My aunt is on dialysis and uses oxygen."
    ids = need_ids(story)
    assert "dialysis_arrangements" not in ids
    assert "respiratory_trach_vent" not in ids


def test_contradiction_is_asked_not_claimed_used():
    rows = account_user_input("She is fully independent but needs help with bathing every day.")["statements"]
    assert any(row["status"] == "ASKED" and "CONFLICT_REQUIRES_CLARIFICATION" in row["concepts"] for row in rows)


def test_past_or_future_statement_is_asked_for_time_scope():
    rows = account_user_input("She used to need help with bathing.")["statements"]
    assert any(row["status"] == "ASKED" and "TIME_SCOPE_REQUIRES_CLARIFICATION" in row["concepts"] for row in rows)


def test_third_party_statement_is_asked_for_person_scope():
    rows = account_user_input("My aunt is on dialysis.")["statements"]
    assert any(row["status"] == "ASKED" and "PERSON_SCOPE_REQUIRES_CLARIFICATION" in row["concepts"] for row in rows)


def test_hebrew_material_is_not_falsely_marked_used():
    rows = account_user_input("אמא צריכה עזרה ברחצה ואין לה דמנציה.")["statements"]
    assert any(row["status"] == "ASKED" and "SEMANTIC_INTERPRETATION_REQUIRED" in row["concepts"] for row in rows)
