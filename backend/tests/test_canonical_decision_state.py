from app.services.canonical_decision_state import DecisionPhase, derive_canonical_decision_state


def base_result():
    return {
        "decision_intelligence": {
            "human_intelligence": {
                "decision_readiness": "READY",
                "readiness_guardian": {"client_owned_blockers": []},
                "semantic_ai": {"required": True, "status": "CONSULTED_AND_VALIDATED"},
            }
        },
        "results": [],
    }


def test_client_blocker_beats_legacy_ready():
    result = base_result()
    result["decision_intelligence"]["human_intelligence"]["readiness_guardian"]["client_owned_blockers"] = [{"fact_key": "move_timing"}]
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.CLIENT_INPUT_REQUIRED
    assert state.next_action == "ASK_CLIENT"


def test_ai_failure_is_system_blocked():
    result = base_result()
    result["decision_intelligence"]["human_intelligence"]["semantic_ai"] = {"required": True, "status": "FAILED"}
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.SYSTEM_BLOCKED


def test_pending_must_routes_to_evidence_collection():
    result = base_result()
    result.update({"must_eligible_count": 3, "must_pending_verification_count": 4, "must_rejected_count": 2})
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.EVIDENCE_COLLECTION


def test_must_pass_routes_to_ai_ranking_until_ranking_complete():
    result = base_result()
    result.update({"must_eligible_count": 8, "must_pending_verification_count": 0, "must_rejected_count": 3})
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.AI_RANKING


def test_ranked_with_nice_gaps_routes_to_preference_verification():
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 3, "nice_complete_candidate_count": 1, "verification_required_count": 4},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.PREFERENCE_VERIFICATION


def test_complete_pipeline_reaches_final_recommendation():
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_BATCH_RANKED"},
        "dynamic_preferences": {"preference_count": 2, "nice_complete_candidate_count": 5, "verification_required_count": 0},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.FINAL_RECOMMENDATION
    assert state.can_show_recommendations is True
