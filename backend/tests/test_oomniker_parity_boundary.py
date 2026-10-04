"""Advisor presentation changes cannot hide changes to the actual recommendations."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("oomniker_parity_runner", ROOT / "scripts/decision_parity/run_parity.py")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

def compare(tmp_path, monkeypatch, before, after):
    monkeypatch.setattr(RUNNER, "CASES", {"one": {}})
    base, candidate = tmp_path / "base", tmp_path / "candidate"
    base.mkdir()
    candidate.mkdir()
    (base / "one.json").write_text(json.dumps(before))
    (candidate / "one.json").write_text(json.dumps(after))
    return RUNNER.compare(str(base), str(candidate))

def test_advice_contract_can_change_while_the_original_order_is_identical(tmp_path, monkeypatch):
    before = {"run_limit5": {"results": [{"canonical_facility_id": "A"}], "oomniker": {"suggestions": [{"authority": "CLIENT_MUST"}]}}}
    after = {"run_limit5": {"results": [{"canonical_facility_id": "A"}], "oomniker": {"suggestions": [], "preference_analysis": {}}}}
    assert compare(tmp_path, monkeypatch, before, after) == 0

def test_an_advice_change_cannot_hide_a_ranking_change(tmp_path, monkeypatch):
    before = {"run_limit5": {"results": [{"canonical_facility_id": "A"}, {"canonical_facility_id": "B"}], "oomniker": {}}}
    after = {"run_limit5": {"results": [{"canonical_facility_id": "B"}, {"canonical_facility_id": "A"}], "oomniker": {"new": True}}}
    assert compare(tmp_path, monkeypatch, before, after) == 1

def test_an_advice_change_cannot_hide_a_must_change(tmp_path, monkeypatch):
    before = {"run_limit5": {"decision_intelligence": {"must_gate": {"eligible": 5}}, "oomniker": {}}}
    after = {"run_limit5": {"decision_intelligence": {"must_gate": {"eligible": 6}}, "oomniker": {"new": True}}}
    assert compare(tmp_path, monkeypatch, before, after) == 1

def test_source_paths_are_additive_but_existing_preferences_cannot_change(tmp_path, monkeypatch):
    before = {"run_limit5": {"decision_intelligence": {"dynamic_preference_model": {"preferences": [{"client_expression": "Music"}]}}}}
    after = {"run_limit5": {"decision_intelligence": {"dynamic_preference_model": {"preferences": [{"client_expression": "Swimming", "mapped_parameters": ["happinessPreferences"]}]}}}}
    assert compare(tmp_path, monkeypatch, before, after) == 1

def test_changed_or_removed_source_paths_are_not_exempt(tmp_path, monkeypatch):
    before = {"run_limit5": {"decision_intelligence": {"dynamic_preference_model": {"preferences": [{"mapped_parameters": ["happinessPreferences"]}]}}}}
    after = {"run_limit5": {"decision_intelligence": {"dynamic_preference_model": {"preferences": [{"mapped_parameters": ["budget"]}]}}}}
    assert compare(tmp_path, monkeypatch, before, after) == 1
