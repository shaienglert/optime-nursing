import json
from pathlib import Path
from scripts.golden_decision_independent_oracle import evaluate

ROOT=Path(__file__).resolve().parents[2]
CONTRACT=json.loads((ROOT/"backend/gold_examples/oomnik_golden_decision_v01.json").read_text())
BY_ID={row["id"]:row for row in CONTRACT["scenarios"]}

def test_budget_tolerance_ceiling_is_independent():
    result=evaluate(BY_ID["D05"])
    assert all(row["price"] <= 4730 for row in result["eligible"])

def test_required_dialysis_never_passes_without_yes():
    result=evaluate(BY_ID["D10"])
    assert all("dialysis_arrangements" not in row["unknown"] for row in result["eligible"])
    assert all("dialysis_arrangements" not in row["fail"] for row in result["eligible"])

def test_hard_radius_excludes_outside_candidates():
    result=evaluate(BY_ID["D16"])
    assert all(row["distance_miles"] is not None and row["distance_miles"] <= 10 for row in result["eligible"])

def test_summerlin_is_measurable_not_disabled():
    result=evaluate(BY_ID["D18"])
    measured=result["eligible"]+result["pending"]
    assert measured
    assert all(row["distance_miles"] is not None for row in measured)

def test_pet_requirement_stays_pending_without_evidence():
    result=evaluate(BY_ID["D26"])
    assert result["counts"]["eligible"] == 0
    assert result["counts"]["pending"] > 0

def test_immediate_availability_is_visible_verification_state_not_silent_pass():
    result=evaluate(BY_ID["D20"])
    rows=result["eligible"]+result["pending"]
    assert rows
    assert all("availability" in row for row in rows)
