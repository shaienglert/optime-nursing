"""Invariant (owner, 2026-10-01): once the Canonical Structured Profile exists, no
downstream component may derive a new fact from raw text. Without the AI interpreter, free
text stays UNPROCESSED -- it does not come back through a regex.

Mechanical form: with AI off, adding any free text to a structured profile must not change
a single decision fact or result.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
PERSONAS = json.loads((ROOT / "backend/gold_examples/oomnik_golden_personas_v1.submissions.json").read_text())["personas"]
ENV = {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200", "OPTIME_SEMANTIC_AI_ENABLED": "0", "OPTIME_SEMANTIC_AI_REQUIRED": "0"}
TEXTS = [
    "My father has dementia, wanders at night and needs a locked memory unit.",
    "She needs dialysis three times a week and daily wound care, and uses continuous oxygen.",
    "She is fully independent, no help with bathing, dressing or medications, no memory problems.",
    "We keep strictly kosher and she only speaks Hebrew. The facility must accept Medicaid.",
    "My parents are a couple and must live together, near Henderson, within 5 miles.",
    "Only in-house care, no outside agencies. Budget is $2,000 at most.",
]


def _facts(response):
    profile = response.get("patient_needs_profile") or {}
    intent = (response.get("decision_intelligence") or {}).get("client_intent") or {}
    return {
        "needs": sorted((n.get("parameter_id"), n.get("requirement_level"), str(n.get("desired_value"))) for n in profile.get("needs") or []),
        "musts": sorted(str(m.get("key")) for m in intent.get("must_haves") or []),
        "nices": sorted(str(m.get("key")) for m in intent.get("nice_to_haves") or []),
        "results": [r.get("canonical_facility_id") for r in response.get("results") or []],
        "funnel": [(s.get("stage"), s.get("remaining")) for s in (response.get("decision_funnel") or {}).get("stages") or []],
        "location": (response.get("location_scope") or {}).get("reference"),
    }


@pytest.fixture(scope="module")
def engine():
    with patch.dict(os.environ, ENV, clear=False):
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("single-authority")
        yield run_patient_decision_engine


@pytest.mark.parametrize("persona", PERSONAS[::3], ids=[p["id"] for p in PERSONAS[::3]])
def test_free_text_without_interpreter_changes_no_decision_fact(persona, engine):
    state = persona["questionnaire_state"]
    baseline = _facts(engine(state, "", limit=10))
    for text in TEXTS:
        assert _facts(engine(state, text, limit=10)) == baseline, text


def test_unprocessed_text_is_marked_not_used():
    with patch.dict(os.environ, ENV, clear=False):
        from app.services.patient_decision_engine import build_patient_needs_profile

        profile = build_patient_needs_profile(PERSONAS[0]["questionnaire_state"], TEXTS[1])
    human = profile["decision_intelligence"]["human_intelligence"]
    assert human["intake_resolution"]["unprocessed_narrative"] is True
    unprocessed = human["structured_profile_shadow"]["unprocessed"]
    assert unprocessed and unprocessed[0]["status"] == "UNPROCESSED"


def test_interpreter_patch_is_the_only_road_from_text_to_a_fact():
    # The same fact typed as free text reaches the decision only as an AI_EXTRACTED field
    # of the Structured Profile (here: the interpreter's questionnaire_patch).
    from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

    state = {"medicalCareProfile": {"needs": []}}
    semantic = {
        "questionnaire_patch": {"medicalCareProfile": {"needs": ["Dialysis"]}},
        "statements": [{"raw_text": "She needs dialysis", "mapped_parameters": ["medicalCareProfile.needs"], "knowledge_state": "KNOWN"}],
    }
    profile = build_structured_profile(state, semantic)
    assert profile["fields"]["medicalCareProfile.needs"]["provenance"] == "AI_EXTRACTED"
    assert materialize_questionnaire(profile)["medicalCareProfile"]["needs"] == ["Dialysis"]
