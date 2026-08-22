from app.services.patient_decision_engine import build_patient_needs_profile
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.client_statement_accounting import split_user_statements

CLIENT_TEXT = "My mother is 82 and is looking for senior living in Las Vegas. She is fully independent with bathing, dressing, toileting, transfers, medications, decision-making and memory. She has no memory concerns, does not need cognitive support, has no mobility limitation, and has no special medical or nursing needs. Her total monthly budget is up to $8,000."

def test_explicit_independence_does_not_become_positive_care_needs():
    profile = build_patient_needs_profile({}, CLIENT_TEXT)
    needs = {row["parameter_id"]: row for row in profile["needs"]}
    for forbidden in ("adl_support", "medication_support", "transfer_assistance", "ot", "memory_care"):
        assert not (forbidden in needs and needs[forbidden].get("desired_value") == "YES"), (forbidden, needs.get(forbidden))
    assert profile["location_city"] == "LAS VEGAS"

def test_strategy_respects_independence_and_memory_negation():
    strategy = build_living_strategy_context({}, CLIENT_TEXT)
    assert strategy["signals"]["adl_support_needed"] is False
    assert strategy["signals"]["medication_support_needed"] is False
    assert strategy["signals"]["no_dementia"] is True

def test_currency_comma_is_not_split_into_fake_statement():
    statements = split_user_statements(CLIENT_TEXT)
    assert any("$8,000" in statement for statement in statements)
    assert "000" not in statements
