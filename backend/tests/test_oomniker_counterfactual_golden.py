"""Oomniker counterfactuals, checked against the real engine.

For every golden persona, each NTH alternative is applied to the structured profile
and the engine is run again. Promised identities must enter the first five while
eligibility and every MUST remain unchanged. A suggestion the ordinary engine cannot
reproduce is a broken promise.
"""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
PERSONAS = json.loads((ROOT / "backend/gold_examples/oomnik_golden_personas_v1.submissions.json").read_text())["personas"]
ENV = {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "500", "OPTIME_SEMANTIC_AI_ENABLED": "0"}
IMMUTABLE = {"SYSTEM_MUST", "CARE_MUST", "CARE_NEED"}


def _relax(state, suggestion):
    """Apply one suggestion to a copy of the structured answers, or None if this test has no
    structured lever for it (reported, never silently skipped)."""
    s = copy.deepcopy(state)
    if suggestion.get("action") == "OFFER_PREFERENCE_ALTERNATIVE":
        for path, value in suggestion["profile_patch"].items():
            current = s
            parts = path.split(".")
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value
        return s
    parameter = suggestion["parameter"]
    if parameter == "budget" and suggestion.get("budget_needed_for_first_option"):
        s["budget"] = int(math.ceil(suggestion["lowest_price_unlocked"] / 100.0) * 100)
        return s
    if parameter == "KOSHER_MEALS":
        s["humanIntelligenceV2"]["culturalProfile"]["kosherRequirements"] = "Preference"
        return s
    if parameter == "CONTINUUM_OF_CARE_REQUIRED":
        s["humanIntelligenceV2"]["futureCareProfile"]["continuumOfCarePreference"] = "Preferred"
        return s
    if parameter == "maximum_distance_miles":
        s["approvedSearchRadiusMiles"] = str(suggestion["proposed_miles"])
        return s
    return None


@pytest.fixture(scope="module")
def engine():
    with patch.dict(os.environ, ENV, clear=False):
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("oomniker-counterfactual")
        yield lambda state: run_patient_decision_engine(state, "", limit=20)


@pytest.mark.parametrize("persona", PERSONAS, ids=[p["id"] for p in PERSONAS])
def test_every_oomniker_relaxation_is_reproduced_by_the_engine(persona, engine):
    base = engine(persona["questionnaire_state"])
    advice = base.get("oomniker") or {}
    assert advice.get("input_universe") == "FULL_CANDIDATE_LEDGER_OF_THIS_SEARCH"
    assert advice.get("profile_mutated") is False
    base_count = (base.get("decision_funnel") or {}).get("recommendable_count") or 0
    problems = []
    for suggestion in advice.get("suggestions") or []:
        if suggestion.get("action") != "VERIFY_WITH_COMMUNITIES" and suggestion.get("authority") != "PREFERENCE":
            problems.append(f"offered an immutable constraint: {suggestion}")
        if suggestion.get("may_auto_change") is not False:
            problems.append(f"suggestion may auto-change: {suggestion['parameter']}")
        if suggestion.get("action") in {"VERIFY_WITH_COMMUNITIES", "EXPLAIN_NARROWING"}:
            continue
        relaxed = _relax(persona["questionnaire_state"], suggestion)
        if relaxed is None:
            problems.append(f"no structured lever to verify suggestion {suggestion['parameter']} ({suggestion['authority']})")
            continue
        after = engine(relaxed)
        funnel = after.get("decision_funnel") or {}
        if suggestion.get("action") == "OFFER_PREFERENCE_ALTERNATIVE":
            original_ids = {row["canonical_facility_id"] for row in base.get("results", [])[:5]}
            after_ids = {row["canonical_facility_id"] for row in after.get("results", [])[:5]}
            promised_ids = {row["canonical_facility_id"] for row in suggestion["candidates"]}
            assert len(promised_ids) == suggestion["new_recommendation_count"] >= 2
            assert promised_ids.issubset(after_ids - original_ids)
            assert (funnel.get("recommendable_count") or 0) == base_count
            before_musts = {row["key"] for row in base["decision_intelligence"]["client_intent"]["must_haves"]}
            after_musts = {row["key"] for row in after["decision_intelligence"]["client_intent"]["must_haves"]}
            assert before_musts == after_musts
            continue
        if suggestion["parameter"] == "maximum_distance_miles":
            scope = after.get("location_scope") or {}
            gained = (scope.get("within_count") or 0) - ((base.get("location_scope") or {}).get("within_count") or 0)
            if gained < (suggestion.get("additional_candidates_before_requirement_checks") or 0):
                problems.append(f"radius {suggestion['proposed_miles']} added {gained}, promised {suggestion['additional_candidates_before_requirement_checks']}")
            continue
        gained = (funnel.get("recommendable_count") or 0) - base_count
        # A budget suggestion names the budget for the FIRST option it unlocks.
        promised = 1 if suggestion["parameter"] == "budget" else (suggestion.get("additional_options_if_relaxed") or 1)
        if gained < promised:
            problems.append(f"{suggestion['parameter']}: engine gained {gained}, Oomniker promised {suggestion.get('additional_options_if_relaxed')}")
    assert not problems, f"{persona['id']}:\n  " + "\n  ".join(problems)
