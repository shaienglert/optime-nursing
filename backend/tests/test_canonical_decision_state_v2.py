from __future__ import annotations

import pytest

from app.services.canonical_decision_state import (
    assert_ai_output_respects_authoritative_must,
    build_authoritative_must_snapshot,
    build_canonical_client_state,
    build_canonical_facility_state,
)


def _decision() -> dict:
    return {
        "human_intelligence": {
            "decision_readiness": "READY",
            "adaptive_questions": [],
            "semantic_ai": {
                "result": {
                    "facts": ["Resident is 90 and cognitively alert"],
                    "preferences": ["Enjoys classical music and social company"],
                    "constraints": ["Monthly budget is $8,000"],
                    "concerns": ["Does not want to remain alone after spouse's death"],
                    "statements": [
                        {
                            "raw_text": "She needs help with medications",
                            "meaning": "Medication support is required",
                            "importance": "MUST",
                            "knowledge_state": "KNOWN",
                            "status": "USED",
                            "mapped_parameters": ["medication_support"],
                        }
                    ],
                    "governance": {"no_silent_drop": True},
                }
            },
        },
        "client_intent": {
            "must_haves": [{"key": "MEDICATION_SUPPORT_AVAILABLE"}],
            "nice_to_haves": [],
        },
        "living_strategy": {
            "strategy_candidates": [{"strategy_id": "ASSISTED_LIVING", "rank_hint": 1}],
        },
        "dynamic_preference_model": {
            "preferences": [{"preference_id": "pref:music", "semantic_meaning": "classical music access"}],
        },
    }


def test_canonical_client_state_seals_one_downstream_truth():
    state = build_canonical_client_state(
        {"budget": 8000, "locationCity": "Las Vegas"},
        "She needs help with medications and loves classical music.",
        _decision(),
    )
    assert state["sealed_for_downstream"] is True
    assert state["decision_readiness"] == "READY"
    assert state["must_requirements"][0]["key"] == "MEDICATION_SUPPORT_AVAILABLE"
    assert state["living_strategies"][0]["strategy_id"] == "ASSISTED_LIVING"
    assert state["statement_accounting"][0]["provenance"] == "SEMANTIC_AI_STATEMENT_ACCOUNTING"


def test_authoritative_must_has_exactly_one_bucket():
    row = {
        "client_intent_fit": {
            "hard_gate": "PASS",
            "must_pass": ["MEDICATION_SUPPORT_AVAILABLE", "ADL_SUPPORT_AVAILABLE"],
            "must_unknown": [],
            "must_fail": [],
        }
    }
    snapshot = build_authoritative_must_snapshot(row)
    assert snapshot["status"] == "PASS"
    assert snapshot["immutable_downstream"] is True


def test_must_bucket_conflict_fails_closed():
    row = {
        "client_intent_fit": {
            "hard_gate": "PENDING_VERIFICATION",
            "must_pass": ["MEDICATION_SUPPORT_AVAILABLE"],
            "must_unknown": ["MEDICATION_SUPPORT_AVAILABLE"],
            "must_fail": [],
        }
    }
    with pytest.raises(RuntimeError, match="CANONICAL_MUST_BUCKET_CONFLICT"):
        build_authoritative_must_snapshot(row)


def test_gate_cannot_disagree_with_buckets():
    row = {
        "client_intent_fit": {
            "hard_gate": "PASS",
            "must_pass": [],
            "must_unknown": ["MEDICATION_SUPPORT_AVAILABLE"],
            "must_fail": [],
        }
    }
    with pytest.raises(RuntimeError, match="CANONICAL_MUST_GATE_CONTRADICTION"):
        build_authoritative_must_snapshot(row)


def test_facility_state_carries_authoritative_must_even_if_claims_are_sampled():
    row = {
        "canonical_facility_id": "NV-ATRIA-SEVILLE",
        "facility_name": "Atria Seville",
        "canonical_type": "ASSISTED_LIVING_RFG",
        "client_intent_fit": {
            "hard_gate": "PASS",
            "must_pass": ["MEDICATION_SUPPORT_AVAILABLE"],
            "must_unknown": [],
            "must_fail": [],
        },
    }
    state = build_canonical_facility_state(row, governed_claims=[{"claim_id": "claim:x", "path": "facility.other", "value": True}])
    assert state["must"]["pass"] == ["MEDICATION_SUPPORT_AVAILABLE"]
    assert state["must"]["authoritative"] is True


def test_ai_cannot_call_passed_medication_must_unknown():
    row = {
        "client_intent_fit": {
            "hard_gate": "PASS",
            "must_pass": ["MEDICATION_SUPPORT_AVAILABLE"],
            "must_unknown": [],
            "must_fail": [],
        }
    }
    with pytest.raises(RuntimeError, match="AI_DOWNSTREAM_CONTRADICTS_AUTHORITATIVE_MUST"):
        assert_ai_output_respects_authoritative_must(
            row,
            ["Medication support is still UNKNOWN in the governed ledger"],
        )
