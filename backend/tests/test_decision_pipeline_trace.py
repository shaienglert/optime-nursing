from app.services.decision_pipeline_trace import attach_decision_pipeline_trace


def test_trace_keeps_must_lineage_when_visibility_is_blocked():
    result = {
        "total_candidates_scored": 10,
        "must_eligible_count": 2,
        "must_pending_verification_count": 6,
        "must_rejected_count": 2,
        "results": [],
        "decision_intelligence": {
            "recommendation_execution_allowed": False,
            "canonical_decision_state": {"phase": "SYSTEM_BLOCKED", "reason": "required AI ranking did not complete", "next_action": "RECOVER_SYSTEM", "must": "PASS"},
            "facility_selection_pipeline": {
                "ai_ranking": {"status": "AI_CANDIDATE_RANKING_REQUIRED_FAILED"},
                "candidate_dispositions": [
                    {"reason_code": "MUST_PASS"}, {"reason_code": "MUST_PASS"},
                    {"reason_code": "MUST_EVIDENCE_PENDING"}, {"reason_code": "MUST_FAIL"},
                ],
            },
        },
    }
    out = attach_decision_pipeline_trace(result)
    trace = out["decision_pipeline_trace"]
    assert trace["candidate_counts"]["must_eligible"] == 2
    assert trace["gates"]["must"]["reason_counts"]["MUST_PASS"] == 2
    assert trace["gates"]["visibility"]["phase"] == "SYSTEM_BLOCKED"
    assert trace["outcome"] == "NO_VISIBLE_RECOMMENDATIONS"
