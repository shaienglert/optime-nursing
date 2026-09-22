from app.services.canonical_decision_state import (
    CanonicalDecisionStateError,
    DecisionFinality,
    DecisionPhase,
    apply_canonical_decision_state_authority,
    canonical_can_show_recommendations,
    canonical_client_is_complete,
    canonical_is_final,
    derive_canonical_decision_state,
    legacy_state_conflicts,
)
import pytest


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


def test_ai_failure_does_not_override_canonical_policy():
    result = base_result()
    result["decision_intelligence"]["human_intelligence"]["semantic_ai"] = {"required": True, "status": "FAILED"}
    state = derive_canonical_decision_state(result)
    assert state.phase is not DecisionPhase.SYSTEM_BLOCKED


def test_pending_must_routes_to_evidence_collection_before_ranking_runs():
    # No candidate has passed every MUST yet, and AI ranking has not run over the
    # pending pool either (no facility_selection_pipeline.ai_ranking status set) --
    # there is genuinely nothing ranked to show yet, unlike
    # test_pending_candidates_are_shown_provisionally_once_ranked below, where
    # ranking over the pending pool has already completed.
    result = base_result()
    result.update({"must_eligible_count": 0, "must_pending_verification_count": 4, "must_rejected_count": 2})
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.EVIDENCE_COLLECTION


def test_pending_candidates_are_shown_provisionally_once_ranked():
    # Pending candidates are ranked alongside eligible ones (must_ai_nice_pipeline.py)
    # rather than excluded, so a completed ranking over eligible+pending must show a
    # shortlist -- but with 40 still-unresolved candidates in that ranked pool, this
    # is provisional (not final): the old "hide everything" and a false "fully
    # final" claim are both wrong here.
    result = base_result()
    result.update({"must_eligible_count": 3, "must_pending_verification_count": 40, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 0, "verification_required_count": 0},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.PROVISIONAL_RECOMMENDATION
    assert state.can_show_recommendations is True
    assert state.finality is DecisionFinality.PROVISIONAL


def test_zero_eligible_ranked_pending_candidates_remain_research_only():
    # No candidate has fully passed MUST yet, but 5 pending ones have already been
    # ranked on today's evidence -- this must not collapse to an empty shortlist.
    result = base_result()
    result.update({"must_eligible_count": 0, "must_pending_verification_count": 5, "must_rejected_count": 0})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 0, "verification_required_count": 0},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.EVIDENCE_COLLECTION
    assert state.can_show_recommendations is False


def test_must_pass_routes_to_ai_ranking_until_ranking_complete():
    result = base_result()
    result.update({"must_eligible_count": 8, "must_pending_verification_count": 0, "must_rejected_count": 3})
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.AI_RANKING


def test_no_resolved_preferences_at_all_still_shows_a_provisional_recommendation():
    # NICE preferences are a ranking/labeling signal, not a visibility gate: more
    # confirmed matches can only raise a candidate's standing, but their absence
    # never blocks a validated MUST-pass, fully-ranked shortlist from being shown --
    # even when literally no candidate has any preference resolved yet.
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {"preference_count": 3, "nice_complete_candidate_count": 0, "verification_required_count": 4},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.PROVISIONAL_RECOMMENDATION
    assert state.can_show_recommendations is True
    assert state.finality is DecisionFinality.PROVISIONAL


def test_one_candidate_with_resolved_preferences_reaches_provisional_despite_other_gaps():
    # A candidate whose own NICE preferences are fully resolved must not stay hidden
    # because some *other* checked candidate still has unresolved evidence -- the
    # same "unresolved evidence on one candidate is a research queue, not a veto"
    # principle already applied to the MUST gate (see
    # test_pending_candidates_are_shown_provisionally_once_ranked).
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


def test_deterministic_thin_evidence_waterfall_is_a_complete_ranking_not_a_fallback():
    """Distinct from DETERMINISTIC_FALLBACK: this status means AI was deliberately
    skipped because the candidate pool had no NICE preferences and no known rating/
    grade/disciplinary record to differentiate on, not that AI was unavailable. The
    governed deterministic key still produced a real, meaningful order (MUST, then
    NICE, then regulatory grade, then reviews), so this must reach a real
    recommendation phase like AI_RANKED does -- never the "unranked set, no order
    implied" treatment DETERMINISTIC_FALLBACK gets.
    """
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "DETERMINISTIC_THIN_EVIDENCE_WATERFALL"},
        "dynamic_preferences": {"preference_count": 0, "nice_complete_candidate_count": 0, "verification_required_count": 0},
    }
    state = derive_canonical_decision_state(result)
    assert state.phase is DecisionPhase.FINAL_RECOMMENDATION
    assert state.can_show_recommendations is True
    assert state.is_degraded_result is False


def test_deterministic_fallback_shows_an_unranked_eligible_set():
    """Recorded as a legacy divergence during the shadow rollout; now resolved in favour
    of showing the set.

    When the ranking model is unavailable the hard criteria still produced eligible
    communities, and a family is better served by "these meet your requirements, we could
    not study them today" than by an empty screen. What the result must never do is imply
    an order, so the phase is its own and the finality says degraded rather than provisional.
    """
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
    assert state.phase is DecisionPhase.UNRANKED_ELIGIBLE_SET
    assert state.can_show_recommendations is True
    assert state.is_degraded_result is True
    assert state.finality is DecisionFinality.DEGRADED_UNRANKED
    assert "LEGACY_VISIBILITY_SHOWS_PREMATURE_RECOMMENDATION" not in legacy_state_conflicts(state)


def test_canonical_authority_overwrites_legacy_global_controls():
    result = base_result()
    result.update({"must_eligible_count": 6, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"].update(
        recommendation_execution_allowed=True,
        recommendation_visibility="PROVISIONAL_RANKING_VISIBLE",
        decision_finality="PROVISIONAL_PENDING_PROVIDER_VERIFICATION",
        # A model error removes AI ordering but must not erase verified candidates.
        facility_selection_pipeline={"ai_ranking": {"status": "AI_RANKING_ERROR"}},
    )

    out = apply_canonical_decision_state_authority(result)
    decision = out["decision_intelligence"]
    assert decision["canonical_decision_state"]["authoritative"] is True
    assert decision["recommendation_execution_allowed"] is True
    assert decision["recommendation_visibility"] == "UNRANKED_ELIGIBLE_SET_VISIBLE"


def test_control_readers_fail_closed_without_authoritative_canonical_state():
    with pytest.raises(CanonicalDecisionStateError, match="NOT_AUTHORITATIVE"):
        canonical_can_show_recommendations(base_result())


def test_legacy_mirrors_cannot_override_canonical_control_decisions():
    result = base_result()
    result.update({"must_eligible_count": 5, "must_pending_verification_count": 0, "must_rejected_count": 2})
    result["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_BATCH_RANKED"},
        "dynamic_preferences": {"preference_count": 0, "verification_required_count": 0},
    }
    apply_canonical_decision_state_authority(result)

    # Simulate a stale late writer. Compatibility mirrors may be wrong, but no
    # production control reader is permitted to consult them anymore.
    result["decision_intelligence"]["recommendation_execution_allowed"] = False
    result["decision_intelligence"]["decision_finality"] = "BLOCKED_SYSTEM"
    result["decision_intelligence"]["human_intelligence"]["decision_readiness"] = "NEEDS_CLARIFICATION"

    assert canonical_can_show_recommendations(result) is True
    assert canonical_client_is_complete(result) is True
    assert canonical_is_final(result) is True
