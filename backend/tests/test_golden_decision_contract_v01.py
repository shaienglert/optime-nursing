from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "backend" / "gold_examples" / "oomnik_golden_decision_v01.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_owner_golden_contract_has_unique_scenarios_and_global_safety_rules():
    payload = _contract()
    scenarios = payload["scenarios"]
    ids = [row["id"] for row in scenarios]
    assert len(ids) == len(set(ids))
    assert payload["global_rules"]["max_results"] == 10
    assert payload["global_rules"]["budget_tolerance_pct"] == 10
    assert payload["global_rules"]["unknown_is_pass"] is False
    assert payload["global_rules"]["final_availability_requires_direct_facility_verification"] is True


def test_every_budget_case_encodes_owner_tolerance_without_relaxing_other_musts():
    payload = _contract()
    assert payload["global_rules"]["budget_order"] == "IN_BUDGET_THEN_WITHIN_10_PERCENT"
    by_id = {row["id"]: row for row in payload["scenarios"]}
    assert by_id["D05"]["expected"]["max_price"] == 4730
    assert by_id["D06"]["expected"]["max_price"] == 6600
    assert by_id["D08"]["expected"]["max_price"] == 6600


def test_availability_policy_distinguishes_immediate_from_thirty_day_move():
    by_id = {row["id"]: row for row in _contract()["scenarios"]}
    assert by_id["D12"]["expected"]["availability_affects_initial_rank"] is False
    immediate = by_id["D20"]["expected"]
    assert immediate["availability_affects_practical_order"] is True
    assert immediate["limited_unknown_allowed_with_caveat"] is True
    assert immediate["final_verification_required"] is True


def test_true_ties_and_oomniker_are_explicit_contract_not_ai_tiebreak():
    by_id = {row["id"]: row for row in _contract()["scenarios"]}
    assert by_id["D25"]["expected"] == {"preserve_joint_rank": True, "offer_oomniker": True}


def test_personal_destination_fallback_is_transparent_not_silent_failure():
    expected = {row["id"]: row for row in _contract()["scenarios"]}["D27"]["expected"]
    assert expected["inside_target_first"] is True
    assert expected["outside_target_allowed_after_with_distance_caveat"] is True
    assert expected["offer_oomniker_when_supply_constrained"] is True
