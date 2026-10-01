"""Contract: the affordability floor and the Medicaid pathway CLIENT MUST.

Invariant (owner rule, 2026-10-01): the floor a budget is compared against is the lowest
price among THIS search's candidates that passed SYSTEM MUST and the family's care needs,
computed before any budget/Medicaid gate. Budget < floor with Medicaid Approved/pending
makes the Medicaid pathway a CLIENT MUST; UNKNOWN Medicaid acceptance is never PASS.

These tests hold the invariant at the engine level, for any profile -- no persona, price or
care combination is special. The golden persona test only illustrates it.
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.affordability_floor import (
    CARE_MUST_KEYS,
    MEDICAID_PATHWAY_KEY,
    NON_CARE_CLIENT_MUST_KEYS,
    SYSTEM_MUST_KEYS,
    apply_medicaid_affordability_rule,
    compute_affordability_floor,
)
from app.services.client_intent_runtime import evaluate_candidate_intent

ROOT = Path(__file__).resolve().parents[2]


def _row(fid, price, must_pass=(), matched=(), eligibility="ELIGIBLE"):
    return {
        "canonical_facility_id": fid,
        "starting_monthly_price": price,
        "eligibility_status": eligibility,
        "client_intent_fit": {"must_pass": list(must_pass)},
        "matched_needs": [{"parameter_id": pid} for pid in matched],
    }


INTENT = {"must_haves": [{"key": "LICENSE_CURRENTLY_VALID"}, {"key": "ADL_SUPPORT_AVAILABLE"}, {"key": "COUPLE_CORESIDENCE"}]}
PROFILE = {"needs": [
    {"parameter_id": "wound_care", "requirement_level": "HIGH"},
    {"parameter_id": "current_availability", "requirement_level": "HIGH"},  # not care
    {"parameter_id": "kosher", "requirement_level": "HIGH"},  # not care
    {"parameter_id": "medicaid_attributes", "requirement_level": "PREFERENCE"},
]}
CARE_OK = ("LICENSE_CURRENTLY_VALID", "ADL_SUPPORT_AVAILABLE")


def test_floor_counts_only_candidates_that_passed_system_and_care():
    rows = [
        _row("cheap_no_care_evidence", 1500, must_pass=("LICENSE_CURRENTLY_VALID",), matched=("wound_care",)),  # ADL UNKNOWN
        _row("cheap_wound_unknown", 1800, must_pass=CARE_OK),  # wound care need UNKNOWN
        _row("cheap_ineligible", 1900, must_pass=CARE_OK, matched=("wound_care",), eligibility="INELIGIBLE"),
        _row("unpriced", None, must_pass=CARE_OK, matched=("wound_care",)),
        _row("qualified_no_couple", 4100, must_pass=CARE_OK, matched=("wound_care",)),  # couple MUST not passed: still counts
        _row("qualified", 5200, must_pass=(*CARE_OK, "COUPLE_CORESIDENCE"), matched=("wound_care",)),
    ]
    floor = compute_affordability_floor(rows, INTENT, PROFILE)
    assert floor["floor_monthly_price"] == 4100
    assert floor["floor_canonical_facility_id"] == "qualified_no_couple"
    assert floor["care_need_parameters"] == ["wound_care"]
    assert floor["qualified_count"] == 3 and floor["qualified_priced_count"] == 2


@pytest.mark.parametrize("status,budget,expect_must,outcome", [
    ("Application pending", 3000, True, "MEDICAID_PATHWAY_CLIENT_MUST"),
    ("Approved", 4099, True, "MEDICAID_PATHWAY_CLIENT_MUST"),
    ("Approved", 4100, False, "PRIVATE_PAY_REACHABLE"),
    ("May qualify", 3000, False, "NOT_APPLICABLE_MEDICAID_NOT_PURSUED"),
    ("Not sure", 3000, False, "NOT_APPLICABLE_MEDICAID_NOT_PURSUED"),
    ("Not eligible", 3000, False, "NOT_APPLICABLE_MEDICAID_NOT_PURSUED"),
    ("Application pending", None, False, "NOT_DETERMINED_NO_BUDGET"),
])
def test_rule_promotes_medicaid_only_below_the_floor_when_pursued(status, budget, expect_must, outcome):
    rows = [_row("a", 4100, must_pass=CARE_OK, matched=("wound_care",)), _row("b", 900)]
    intent, profile = copy.deepcopy(INTENT), copy.deepcopy(PROFILE)
    record = apply_medicaid_affordability_rule(rows, intent, {"medicaidStatus": status, "budget": budget}, profile)
    keys = [m["key"] for m in intent["must_haves"]]
    assert record["outcome"] == outcome
    assert (MEDICAID_PATHWAY_KEY in keys) is expect_must
    level = next(n["requirement_level"] for n in profile["needs"] if n["parameter_id"] == "medicaid_attributes")
    assert level == ("HIGH" if expect_must else "PREFERENCE")
    assert intent["affordability_floor"]["floor_monthly_price"] == 4100


def test_no_qualified_price_never_invents_a_must():
    intent = copy.deepcopy(INTENT)
    record = apply_medicaid_affordability_rule([_row("x", 900)], intent, {"medicaidStatus": "Approved", "budget": 500}, copy.deepcopy(PROFILE))
    assert record["outcome"] == "NOT_DETERMINED_NO_QUALIFIED_PRICE"
    assert MEDICAID_PATHWAY_KEY not in [m["key"] for m in intent["must_haves"]]


def test_rule_is_idempotent():
    intent, profile = copy.deepcopy(INTENT), copy.deepcopy(PROFILE)
    rows = [_row("a", 4100, must_pass=CARE_OK, matched=("wound_care",))]
    state = {"medicaidStatus": "Approved", "budget": 3000}
    apply_medicaid_affordability_rule(rows, intent, state, profile)
    second = apply_medicaid_affordability_rule(rows, intent, state, profile)
    assert second["promoted"] is False
    assert [m["key"] for m in intent["must_haves"]].count(MEDICAID_PATHWAY_KEY) == 1


def test_unknown_medicaid_acceptance_is_pending_never_pass_or_fail():
    intent = {"must_haves": [{"key": MEDICAID_PATHWAY_KEY}]}
    fit = evaluate_candidate_intent({"canonical_facility_id": "x"}, intent)
    assert MEDICAID_PATHWAY_KEY in fit["must_unknown"]
    assert MEDICAID_PATHWAY_KEY not in fit["must_pass"] and MEDICAID_PATHWAY_KEY not in fit["must_fail"]
    assert fit["hard_gate"] == "PENDING_VERIFICATION"


def test_every_client_must_key_is_classified_for_the_floor():
    """A new MUST key must be declared SYSTEM, care, or non-care; silence would let it
    shape (or escape) the floor by accident."""
    source = (ROOT / "backend/app/services/client_intent_runtime.py").read_text()
    emitted = set(re.findall(r'add_must\(\s*"([A-Z_]+)"', source))
    classified = SYSTEM_MUST_KEYS | CARE_MUST_KEYS | NON_CARE_CLIENT_MUST_KEYS
    unclassified = sorted(emitted - classified)
    assert not unclassified, f"classify these MUST keys in affordability_floor.py: {unclassified}"


# ---- Engine level: the invariant over every golden profile, not one persona ----------

SUBMISSIONS = ROOT / "backend/gold_examples/oomnik_golden_personas_v1.submissions.json"
PERSONAS = json.loads(SUBMISSIONS.read_text(encoding="utf-8"))["personas"]
PILOT_ENV = {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200", "OPTIME_SEMANTIC_AI_ENABLED": "0"}


@pytest.fixture(scope="module")
def engine():
    with patch.dict(os.environ, PILOT_ENV, clear=False):
        from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("affordability-floor-contract")

        def run(state):
            questionnaire = materialize_questionnaire(build_structured_profile(state))
            response = run_patient_decision_engine(questionnaire, "", limit=50)
            intent = (response.get("decision_intelligence") or {}).get("client_intent") or {}
            return response, intent

        yield run


@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_floor_is_a_property_of_the_care_universe_not_of_budget_or_funding(persona, engine):
    records, musts = {}, {}
    for status in ("Application pending", "Not eligible"):
        for budget in (500, 50000):
            state = {**copy.deepcopy(persona["questionnaire_state"]), "medicaidStatus": status, "budget": budget}
            response, intent = engine(state)
            record = intent.get("affordability_floor") or {}
            records[(status, budget)] = (record.get("floor_monthly_price"), record.get("floor_canonical_facility_id"))
            musts[(status, budget)] = MEDICAID_PATHWAY_KEY in {m.get("key") for m in intent.get("must_haves") or []}
            # Whatever is shown under a Medicaid MUST has verified Medicaid acceptance.
            if musts[(status, budget)]:
                for row in response.get("results") or []:
                    assert MEDICAID_PATHWAY_KEY in ((row.get("client_intent_fit") or {}).get("must_pass") or []), row.get("canonical_facility_id")
    # 1. Neither the budget nor the funding status moves the floor.
    assert len(set(records.values())) == 1, records
    floor_price = next(iter(records.values()))[0]
    # 2. The MUST appears exactly when funding is pursued and the budget is below the floor.
    for (status, budget), has_must in musts.items():
        expected = status == "Application pending" and floor_price is not None and budget < floor_price
        assert has_must is expected, (status, budget, floor_price)


# ---- Funding pathway decides which cost the budget is compared with ---------------------

def test_medicaid_pathway_compares_budget_with_household_cost_never_private_price():
    from app.services.affordability_floor import apply_funding_pathway, relevant_monthly_cost
    from app.services.semantic_facility_requirements import _row_budget_verdict

    intent = {"must_haves": [{"key": MEDICAID_PATHWAY_KEY}]}
    known_in = {"starting_monthly_price": 6000, "verified_capabilities": {"medicaid_household_out_of_pocket": "2800"}}
    known_over = {"starting_monthly_price": 2000, "verified_capabilities": {"medicaid_household_out_of_pocket": "3600"}}
    unknown = {"starting_monthly_price": 2000, "verified_capabilities": {}}
    assert apply_funding_pathway([known_in, known_over, unknown], intent) == "MEDICAID"
    state = {"budget": 3000}
    assert relevant_monthly_cost(known_in) == 2800 and _row_budget_verdict(known_in, state) is True
    assert _row_budget_verdict(known_over, state) is False
    # A private price inside the budget proves nothing about the Medicaid household cost.
    assert relevant_monthly_cost(unknown) is None and _row_budget_verdict(unknown, state) is None


def test_private_pay_pathway_keeps_the_current_private_price():
    from app.services.affordability_floor import apply_funding_pathway, relevant_monthly_cost

    row = {"starting_monthly_price": 4000, "verified_capabilities": {"medicaid_household_out_of_pocket": "100"}}
    assert apply_funding_pathway([row], {"must_haves": []}) == "PRIVATE_PAY"
    row["starting_monthly_price"] = 4750  # e.g. second-resident fee added later
    assert relevant_monthly_cost(row) == 4750
