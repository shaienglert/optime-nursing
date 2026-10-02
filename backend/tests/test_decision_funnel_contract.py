"""Contract: the mechanical funnel cannot certify a wrong CORRECT_ZERO."""
from __future__ import annotations

from app.services.decision_funnel import build_funnel

CATALOG = {"market_universe_count": 4, "excluded_ids_by_parameter": {"adl_support": ["D"]}, "scored_count": 3, "in_scope_count": 3}


def _row(fid, *, fail=(), unknown=(), price=4000, eligibility="ELIGIBLE", unmet=()):
    return {"canonical_facility_id": fid, "eligibility_status": eligibility, "unmet_critical_needs": list(unmet),
            "must_fail": list(fail), "must_unknown": list(unknown), "price": price}


def _funnel(ledger, shown=0, budget=5000, coverage=None, catalog=CATALOG):
    return build_funnel(catalog=catalog, location_scope={"applied": True}, ledger=ledger,
                        must_order=["LICENSE_CURRENTLY_VALID", "ADL_SUPPORT_AVAILABLE", "KOSHER_MEALS"],
                        budget=budget, shown_count=shown, requested_must_coverage=coverage)


def test_zero_held_only_by_unknown_evidence_is_evidence_pending():
    f = _funnel([_row("A", fail=["KOSHER_MEALS"]), _row("B", unknown=["KOSHER_MEALS"]), _row("C", price=9000)])
    assert f["zero_result_classification"] == "EVIDENCE_PENDING"
    assert f["zeroing_parameter"] == "KOSHER_MEALS"


def test_zero_by_verified_evidence_is_correct_and_names_the_last_parameter():
    f = _funnel([_row("A", fail=["KOSHER_MEALS"]), _row("B", fail=["ADL_SUPPORT_AVAILABLE"]), _row("C", price=9000)])
    assert f["zero_result_classification"] == "CORRECT_ZERO"
    assert f["zeroing_stage"] == "BUDGET_VERIFIED_PRICE_ABOVE_LIMIT"
    by_stage = {s["stage"]: s for s in f["stages"]}
    assert by_stage["CARE_MUST_VERIFIED_FAIL"]["removed_by"] == {"ADL_SUPPORT_AVAILABLE": 1}
    assert by_stage["CLIENT_MUST_VERIFIED_FAIL"]["removed_by"] == {"KOSHER_MEALS": 1}


def test_candidates_that_cleared_every_gate_but_were_not_shown_is_engine_failure():
    f = _funnel([_row("A"), _row("B")], shown=0, catalog={**CATALOG, "scored_count": 2, "in_scope_count": 2, "excluded_ids_by_parameter": {"adl_support": ["C", "D"]}})
    assert f["zero_result_classification"] == "ENGINE_FAILURE"
    assert f["zero_result_reason"] == "RECOMMENDABLE_CANDIDATES_NOT_SHOWN"


def test_a_trace_that_does_not_reconcile_is_engine_failure_even_if_zero_looks_correct():
    f = _funnel([_row("A", fail=["KOSHER_MEALS"])])  # catalog says 3 in scope, ledger has 1
    assert f["zero_result_classification"] == "ENGINE_FAILURE"
    assert f["zero_result_reason"] == "TRACE_DOES_NOT_RECONCILE"


def test_requested_must_without_market_evidence_is_a_readiness_failure():
    ledger = [_row("A", unknown=["KOSHER_MEALS"]), _row("B", unknown=["KOSHER_MEALS"]), _row("C", unknown=["KOSHER_MEALS"])]
    f = _funnel(ledger, coverage={"KOSHER_MEALS": {"status": "NO_EVIDENCE_IN_MARKET"}})
    assert f["zero_result_classification"] == "ENGINE_FAILURE"
    assert f["readiness_gaps"] == ["KOSHER_MEALS"]


def test_verified_price_over_budget_is_not_unknown_and_unknown_price_is_not_over_budget():
    f = _funnel([_row("A", price=9000), _row("B", price=None), _row("C", price=9000)])
    budget = next(s for s in f["stages"] if s["stage"] == "BUDGET_VERIFIED_PRICE_ABOVE_LIMIT")
    unknown = next(s for s in f["stages"] if s["stage"] == "MUST_EVIDENCE_UNKNOWN")
    assert budget["removed"] == 2 and unknown["removed_by"] == {"current_price_unknown": 1}
    assert f["zero_result_classification"] == "EVIDENCE_PENDING"
