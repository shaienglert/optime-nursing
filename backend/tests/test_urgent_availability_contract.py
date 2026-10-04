"""Availability depends on move timing (owner decision (a), 2026-10-02).

Urgent move (Immediately / Within 30 days):
  current YES or LIMITED -> passes;
  recorded NO            -> PENDING_RECONFIRMATION: not shown, not a permanent fail;
  no / stale evidence    -> EVIDENCE_PENDING: not shown as a verified recommendation.
Later move: availability is informational only and never excludes a community.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.client_intent_runtime import URGENT_AVAILABILITY_KEY, build_client_intent, evaluate_candidate_intent

INTENT = {"must_haves": [{"key": URGENT_AVAILABILITY_KEY}]}


@pytest.mark.parametrize("recorded,gate,reason", [
    ("YES", "PASS", None), ("LIMITED", "PASS", None),
    ("NO", "PENDING_VERIFICATION", "PENDING_RECONFIRMATION"),
    (None, "PENDING_VERIFICATION", "EVIDENCE_PENDING"),
])
def test_urgent_availability_gate(recorded, gate, reason):
    row = {"verified_capabilities": {"current_availability": recorded} if recorded else {}}
    fit = evaluate_candidate_intent(row, INTENT)
    assert fit["hard_gate"] == gate
    assert URGENT_AVAILABILITY_KEY not in fit["must_fail"]  # never a permanent fail
    assert fit["must_pending_reasons"].get(URGENT_AVAILABILITY_KEY) == reason


@pytest.mark.parametrize("timing,is_must", [("Immediately", True), ("Within 30 days", True), ("1-3 months", False), ("Planning ahead", False)])
def test_only_an_urgent_move_makes_availability_a_must(timing, is_must):
    intent = build_client_intent({"moveTiming": timing}, "", {"signals": {}, "household": {}}, {"signals": {}})
    assert (URGENT_AVAILABILITY_KEY in {m["key"] for m in intent["must_haves"]}) is is_must


def test_engine_never_shows_recorded_no_for_an_urgent_move_and_keeps_it_for_a_later_one():
    root = Path(__file__).resolve().parents[2]
    persona = next(p for p in json.loads((root / "backend/gold_examples/oomnik_golden_personas_v1.submissions.json").read_text())["personas"] if p["id"] == "pilot-002")
    env = {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200", "OPTIME_SEMANTIC_AI_ENABLED": "0"}
    with patch.dict(os.environ, env, clear=False):
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("urgent-availability")
        urgent = run_patient_decision_engine(persona["questionnaire_state"], "", limit=50)
        later = run_patient_decision_engine({**persona["questionnaire_state"], "moveTiming": "1-3 months"}, "", limit=50)
    def recorded(r):
        return (r.get("verified_capabilities") or {}).get("current_availability")
    assert urgent["results"] and all(recorded(r) in {"YES", "LIMITED"} for r in urgent["results"])
    stage = next(s for s in urgent["decision_funnel"]["stages"] if s["stage"] == "MUST_EVIDENCE_UNKNOWN")
    assert stage["removed_by"].get(f"{URGENT_AVAILABILITY_KEY}:PENDING_RECONFIRMATION", 0) > 0
    later_ids = set(later["decision_funnel"]["recommendable_ids"])
    assert any(recorded(r) == "NO" for r in later["results"]) or len(later_ids) > len(urgent["decision_funnel"]["recommendable_ids"])


# Owner decision (2026-10-04): a community that publishes vacancies is relevant; FULL (YES)
# ranks above LIMITED; a recorded NO ranks lowest and never excludes; unknown stays unknown.
NICE_INTENT = {"nice_to_haves": [{"key": "AVAILABILITY_FIT"}]}


@pytest.mark.parametrize("recorded,score,bucket", [
    ("YES", 100.0, "nice_match"), ("LIMITED", 50.0, "nice_match"),
    ("NO", 0.0, "nice_mismatch"), (None, None, "nice_unknown"),
])
def test_availability_fit_ranks_full_above_limited_and_keeps_unknown_distinct(recorded, score, bucket):
    row = {"verified_capabilities": {"current_availability": recorded} if recorded else {}}
    fit = evaluate_candidate_intent(row, NICE_INTENT)
    assert "AVAILABILITY_FIT" in fit[bucket]
    assert fit["nice_fit_scores"].get("AVAILABILITY_FIT") == score
    assert fit["hard_gate"] != "FAIL"


@pytest.mark.parametrize("timing", ["Immediately", "Within 30 days", "1-3 months"])
def test_availability_preference_present_for_any_stated_timing_but_never_a_must_later(timing):
    intent = build_client_intent({"moveTiming": timing}, "", {"signals": {}, "household": {}}, {"signals": {}})
    assert "AVAILABILITY_FIT" in {n["key"] for n in intent["nice_to_haves"]}


def test_planning_ahead_adds_no_availability_preference():
    intent = build_client_intent({"moveTiming": "Planning ahead"}, "", {"signals": {}, "household": {}}, {"signals": {}})
    assert "AVAILABILITY_FIT" not in {n["key"] for n in intent["nice_to_haves"]}
