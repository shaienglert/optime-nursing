from copy import deepcopy
import pytest
from app.services.canonical_intake_state import canonicalize_intake_state
from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
from app.services.affordability_floor import apply_funding_pathway, apply_medicaid_affordability_rule, relevant_monthly_cost
from app.services.semantic_facility_requirements import _row_budget_verdict
from app.services.living_strategy_runtime import build_living_strategy_context

def test_legacy_insurance_is_removed_without_losing_clinical_answers():
    state = {"budget": 8000, "medicaidOriginalBudget": 5000, "medicaidBudgetScenarioChoice": "Include support in my search", "medicaidStatus": "Approved", "medicareStatus": "Original Medicare", "medicalCareProfile": {"needs": ["Dialysis"]}}
    before = deepcopy(state)
    clean = canonicalize_intake_state(state)
    assert clean["budget"] == 5000
    assert "medicaidStatus" not in clean and "medicareStatus" not in clean
    assert clean["medicalCareProfile"] == state["medicalCareProfile"]
    assert state == before
    assert canonicalize_intake_state(clean) == clean
    assert materialize_questionnaire(build_structured_profile(state))["budget"] == 5000

@pytest.mark.parametrize("status", ["Approved", "Application pending", "Not sure", ""])
def test_insurance_never_creates_funding_must_or_changes_price(status):
    row = {"starting_monthly_price": 4000, "verified_capabilities": {"medicaid_household_out_of_pocket": 100}}
    intent = {"must_haves": [{"key": "MEDICAID_PATHWAY_REQUIRED"}]}
    record = apply_medicaid_affordability_rule([row], intent, {"budget": 3000, "medicaidStatus": status}, {"needs": []})
    assert record["promoted"] is False
    assert intent["must_haves"] == []
    assert apply_funding_pathway([row], intent) == "PRIVATE_PAY"
    assert relevant_monthly_cost(row) == 4000

def test_starting_price_is_compared_without_requiring_unknown_final_fees():
    row = {"starting_monthly_price": 7000, "room_pricing_options": [{"base_price": 4395}], "total_affordability_status": "PENDING", "price_truth_basis": "ROOM_BASE_ONLY_TOTAL_PENDING"}
    assert relevant_monthly_cost(row) == 4395
    assert _row_budget_verdict(row, {"budget": 4500}) is True
    assert _row_budget_verdict(row, {"budget": 3900}) is False
    assert _row_budget_verdict({"starting_monthly_price": None}, {"budget": 4500}) is None
