from __future__ import annotations

from app.services import _suppress_unverified_recommendations


def test_suppresses_candidate_identities_when_execution_is_blocked():
    result = {
        "results": [{"canonical_facility_id": "NV-1", "facility_name": "Hidden Candidate"}],
        "result_count": 1,
        "decision_intelligence": {
            "decision_finality": "PROVISIONAL_PENDING_SEMANTIC_MUST_EVIDENCE",
            "recommendation_execution_allowed": False,
        },
        "recommendation_audit_trace": {
            "recommendations": [{"canonical_facility_id": "NV-1", "rank_position": 1}],
        },
    }

    out = _suppress_unverified_recommendations(result)

    assert out["results"] == []
    assert out["result_count"] == 0
    assert out["decision_intelligence"]["research_candidate_count"] == 1
    assert out["decision_intelligence"]["recommendation_visibility"] == "BLOCKED_UNTIL_MUST_GATE_PASS"
    assert out["recommendation_audit_trace"]["recommendations"] == []


def test_preserves_recommendations_only_when_execution_is_allowed():
    result = {
        "results": [{"canonical_facility_id": "NV-1", "facility_name": "Verified Candidate"}],
        "result_count": 1,
        "decision_intelligence": {"recommendation_execution_allowed": True},
    }

    out = _suppress_unverified_recommendations(result)

    assert out["result_count"] == 1
    assert out["results"][0]["facility_name"] == "Verified Candidate"
