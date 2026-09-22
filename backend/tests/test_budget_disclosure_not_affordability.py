"""Published pricing is not proof that a family's budget is met."""
import pytest

from app.services.semantic_facility_requirements import apply_semantic_facility_requirements


@pytest.mark.parametrize("source", ["provider", "agent"])
@pytest.mark.parametrize("price", [None, 9500])
def test_disclosure_flag_cannot_bypass_missing_or_over_budget_price(source, price):
    row = {
        "canonical_facility_id": "BUDGET-REGRESSION",
        "starting_monthly_price": price,
        "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
    }
    evidence = {"published_rates_verified": True}
    if source == "provider":
        row["provider_housing_evidence"] = {"evidence": evidence}
    else:
        row["agent_person_fit_evidence"] = [{"payload": evidence}]
    result = apply_semantic_facility_requirements(
        {"results": [row]}, research_limit=0, questionnaire_state={"budget": 3000}
    )
    fit = result["results"][0]["client_intent_fit"]
    assert "SEMANTIC_BUDGET_VERIFICATION" not in fit["must_pass"]
    assert "SEMANTIC_BUDGET_VERIFICATION" in fit["must_unknown"]
    assert fit["hard_gate"] == "PENDING_VERIFICATION"


def test_disclosure_and_within_budget_price_remain_eligible():
    row = {
        "canonical_facility_id": "AFFORDABLE",
        "starting_monthly_price": 2800,
        "provider_housing_evidence": {"evidence": {"published_rates_verified": True}},
    }
    result = apply_semantic_facility_requirements(
        {"results": [row]}, research_limit=0, questionnaire_state={"budget": 3000}
    )
    assert result["results"][0]["client_intent_fit"]["hard_gate"] == "PASS"
