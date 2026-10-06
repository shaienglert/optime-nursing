"""Owner decisions 1 and 5: monthly budget and one-time capital are separate; Medicaid
states stay distinct and no coverage is promised without evidence."""
import pytest

from app.services.funding_explanation import build_funding_explanation, medicaid_state


@pytest.mark.parametrize("raw,state", [
    ("Approved", "APPROVED"), ("Application pending", "APPLICATION_PENDING"),
    ("May qualify", "MAY_QUALIFY"), ("Not sure", "UNKNOWN"), ("", "UNKNOWN"), (None, "UNKNOWN"),
    ("Not eligible", "NOT_ELIGIBLE"),
])
def test_medicaid_states_stay_distinct(raw, state):
    assert medicaid_state(raw) == state


def _row(**kw):
    base = {"funding_pathway": "PRIVATE_PAY", "starting_monthly_price": 6000, "official_website": "https://example.org/a",
            "verified_capabilities": {}}
    base.update(kw)
    return base


def test_entrance_fee_is_never_added_to_the_monthly_amount():
    out = build_funding_explanation(_row(entrance_fee=90000), {"budget": 7000})
    assert out["monthly"]["amount"] == 6000 and out["monthly"]["included_in_budget"] is True
    assert out["one_time"]["amount"] == 90000


def test_missing_capital_is_unknown_not_assumed():
    out = build_funding_explanation(_row(entrance_fee=90000), {"budget": 7000})
    assert out["one_time"]["status"] == "CAPITAL_NOT_PROVIDED"


@pytest.mark.parametrize("capital,status", [(120000, "FEE_WITHIN_STATED_CAPITAL"), (50000, "FEE_EXCEEDS_STATED_CAPITAL")])
def test_stated_capital_is_compared_only_with_the_one_time_fee(capital, status):
    out = build_funding_explanation(_row(entrance_fee=90000), {"budget": 7000, "availableCapital": capital})
    assert out["one_time"]["status"] == status
    assert out["monthly"]["included_in_budget"] is True


def test_no_one_time_fee_means_no_capital_question():
    assert build_funding_explanation(_row(), {"budget": 7000})["one_time"] is None


def test_unknown_price_is_unknown_not_fit():
    out = build_funding_explanation(_row(starting_monthly_price=None), {"budget": 7000})
    assert out["monthly"]["amount"] is None and out["monthly"]["included_in_budget"] is None


def test_over_budget_is_reported_as_not_included():
    out = build_funding_explanation(_row(starting_monthly_price=9000), {"budget": 7000})
    assert out["monthly"]["included_in_budget"] is False


@pytest.mark.parametrize("status", ["Approved", "Application pending", "May qualify", "Not sure"])
def test_medicaid_never_promises_coverage_without_evidence(status):
    out = build_funding_explanation(_row(), {"budget": 7000, "medicaidStatus": status})
    assert out["medicaid"]["coverage_promised"] is False
    assert out["medicaid"]["acceptance_evidence"] == "UNKNOWN"
    assert "not confirmed" in out["explanation"].lower()


def test_medicaid_amount_and_links_come_only_from_verified_evidence():
    row = _row(funding_pathway="MEDICAID", relevant_monthly_cost=1800,
               verified_capabilities={"medicaid_attributes": "YES", "medicaid_household_out_of_pocket": 1800})
    out = build_funding_explanation(row, {"budget": 2000, "medicaidStatus": "Approved"})
    assert out["monthly"]["amount"] == 1800 and out["monthly"]["basis"] == "MEDICAID_HOUSEHOLD_OUT_OF_POCKET"
    assert out["medicaid"]["acceptance_evidence"] == "YES"
    assert out["links"] == ["https://example.org/a"]
    bare = build_funding_explanation({"funding_pathway": "PRIVATE_PAY"}, {})
    assert bare["links"] == []
