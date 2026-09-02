from app.services.canonical_decision_state import (
    DecisionFinality,
    DecisionPhase,
    apply_canonical_decision_state_authority,
    derive_canonical_decision_state,
    legacy_state_conflicts,
)


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
    # No candidate has passed every MUST yet -- pending evidence is still a
    # real block here, unlike test_pending_non_eligible_candidates_do_not_hide_
    # completed_ranked_shortlist below, where eligible > 0 already.
    result = base_result()
    result.update({"must_eligible_count": 0, "must_pending_verification_count": 4, "must_rejected_count": 2})
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.EVIDENCE_COLLECTION


def test_pending_non_eligible_candidates_do_not_hide_completed_ranked_shortlist():
    result = base_result()
    result.update({"must_eligible_count": 3, "must_pending_verification_count": 40, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 0, "verification_required_count": 0},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.FINAL_RECOMMENDATION
    assert state.can_show_recommendations is True


def test_must_pass_routes_to_ai_ranking_until_ranking_complete():
    result = base_result()
    result.update({"must_eligible_count": 8, "must_pending_verification_count": 0, "must_rejected_count": 3})
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.AI_RANKING


def test_no_candidate_with_resolved_preferences_yet_routes_to_preference_verification():
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 3, "nice_complete_candidate_count": 0, "verification_required_count": 4},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.PREFERENCE_VERIFICATION
    assert state.can_show_recommendations is False


def test_one_candidate_with_resolved_preferences_reaches_provisional_despite_other_gaps():
    # A candidate whose own NICE preferences are fully resolved must not stay hidden
    # because some *other* checked candidate still has unresolved evidence -- the
    # same "unresolved evidence on one candidate is a research queue, not a veto"
    # principle already applied to the MUST gate (see
    # test_pending_non_eligible_candidates_do_not_hide_completed_ranked_shortlist).
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 3, "nice_complete_candidate_count": 1, "verification_required_count": 4},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.PROVISIONAL_RECOMMENDATION
    assert state.can_show_recommendations is True
    assert state.finality is DecisionFinality.PROVISIONAL


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


def test_visible_deterministic_fallback_is_reported_as_legacy_conflict():
    result = base_result()
    result.update({"must_eligible_count": 6, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"].update(
        recommendation_execution_allowed=True,
        recommendation_visibility="PROVISIONAL_RANKING_VISIBLE",
    )
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "DETERMINISTIC_FALLBACK"}
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.AI_RANKING
    assert "LEGACY_VISIBILITY_SHOWS_PREMATURE_RECOMMENDATION" in legacy_state_conflicts(state)


def test_canonical_authority_overwrites_legacy_global_controls():
    result = base_result()
    result.update({"must_eligible_count": 6, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"].update(
        recommendation_execution_allowed=True,
        recommendation_visibility="PROVISIONAL_RANKING_VISIBLE",
        decision_finality="PROVISIONAL_PENDING_PROVIDER_VERIFICATION",
        facility_selection_pipeline={"ai_ranking": {"status": "DETERMINISTIC_FALLBACK"}},
    )

    out = apply_canonical_decision_state_authority(result)
    decision = out["decision_intelligence"]
    assert decision["canonical_decision_state"]["authoritative"] is True
    assert decision["canonical_decision_state"]["phase"] == "AI_RANKING"
    assert decision["recommendation_execution_allowed"] is False
    assert decision["recommendation_visibility"] == "BLOCKED_AI_RANKING"
    assert decision["decision_finality"] == "PENDING_AI_RANKING"
