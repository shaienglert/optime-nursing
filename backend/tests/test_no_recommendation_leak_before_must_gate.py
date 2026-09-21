from __future__ import annotations

from app.services.decision_pipeline import _suppress_unverified_recommendations
import pytest

from app.services.canonical_decision_state import CanonicalDecisionStateError, apply_canonical_decision_state_authority


def test_suppresses_candidate_identities_when_execution_is_blocked():
    result = {
        "results": [{"canonical_facility_id": "NV-1", "facility_name": "Hidden Candidate"}],
        "result_count": 1,
        "must_rejected_count": 1,
        "decision_intelligence": {
            "decision_finality": "PROVISIONAL_PENDING_SEMANTIC_MUST_EVIDENCE",
            "recommendation_execution_allowed": False,
        },
        "recommendation_audit_trace": {
            "recommendations": [{"canonical_facility_id": "NV-1", "rank_position": 1}],
        },
    }

    out = _suppress_unverified_recommendations(apply_canonical_decision_state_authority(result))

    assert out["results"] == []
    assert out["result_count"] == 0
    assert out["decision_intelligence"]["research_candidate_count"] == 1
    assert out["decision_intelligence"]["recommendation_visibility"] == "BLOCKED_MUST_EVALUATION"
    assert out["recommendation_audit_trace"]["recommendations"] == []


def test_preserves_recommendations_only_when_canonical_state_allows_them():
    # Since canonical decision state became the sole authority (#260), visibility is
    # read from the sealed canonical state, never from the legacy
    # recommendation_execution_allowed mirror.
    result = {
        "results": [{
            "canonical_facility_id": "NV-1",
            "facility_name": "Verified Candidate",
            "client_intent_fit": {"hard_gate": "PASS"},
            "must_eligibility": "MUST_ELIGIBLE",
        }],
        "result_count": 1,
        "must_eligible_count": 1,
        "decision_intelligence": {
            "decision_readiness": "READY",
            "human_intelligence": {"decision_readiness": "READY", "adaptive_questions": []},
            "facility_selection_pipeline": {"ai_ranking": {"status": "AI_RANKED"}, "must_eligible_count": 1},
            "must_gate": {"eligible": 1, "pending_verification": 0, "rejected": 0},
        },
    }

    out = _suppress_unverified_recommendations(apply_canonical_decision_state_authority(result))

    assert out["decision_intelligence"]["canonical_decision_state"]["can_show_recommendations"] is True
    assert out["result_count"] == 1
    assert out["results"][0]["facility_name"] == "Verified Candidate"


def test_unsealed_result_fails_closed_instead_of_trusting_legacy_flag():
    result = {
        "results": [{"canonical_facility_id": "NV-1", "facility_name": "Unsealed Candidate"}],
        "result_count": 1,
        "decision_intelligence": {"recommendation_execution_allowed": True},
    }

    with pytest.raises(CanonicalDecisionStateError):
        _suppress_unverified_recommendations(result)
