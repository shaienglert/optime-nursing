"""Shadow-compare CanonicalDecisionState against reviewed lifecycle fixtures.

This is deliberately separate from validate_against_engine.py: the existing harness
validates facility-level MUST behavior, while this harness validates global decision
phase/next-action semantics without changing production control flow.

Usage:
    cd backend && python gold_examples/validate_canonical_state_shadow.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.canonical_decision_state import (
    DecisionPhase,
    SystemHealth,
    derive_canonical_decision_state,
    legacy_state_conflicts,
)


def _base() -> dict:
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


def _fixtures() -> list[dict]:
    client_blocked = _base()
    client_blocked["decision_intelligence"]["human_intelligence"]["readiness_guardian"]["client_owned_blockers"] = [
        {"fact_key": "move_timing"}
    ]

    provider_unknown = _base()
    provider_unknown.update(
        must_eligible_count=3,
        must_pending_verification_count=2,
        must_rejected_count=1,
    )
    provider_unknown["decision_intelligence"]["recommendation_execution_allowed"] = True

    ai_failure = _base()
    ai_failure["decision_intelligence"]["human_intelligence"]["semantic_ai"] = {
        "required": True,
        "status": "FAILED",
    }

    ai_disabled = _base()
    ai_disabled["decision_intelligence"]["human_intelligence"]["semantic_ai"] = {
        "required": True,
        "status": "REQUIRED_BUT_DISABLED",
    }

    ranking_fail_closed = _base()
    ranking_fail_closed.update(must_eligible_count=5, must_pending_verification_count=0, must_rejected_count=1)
    ranking_fail_closed["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "ERROR"},
        "ai_ranking_fail_closed": True,
    }

    legacy_visibility_block = _base()
    legacy_visibility_block.update(must_eligible_count=4, must_pending_verification_count=0, must_rejected_count=2)
    legacy_visibility_block["decision_intelligence"]["recommendation_visibility"] = "BLOCKED_AI_RANKING_UNAVAILABLE"

    no_eligible = _base()
    no_eligible.update(must_eligible_count=0, must_pending_verification_count=0, must_rejected_count=8)

    ranking = _base()
    ranking.update(must_eligible_count=8, must_pending_verification_count=0, must_rejected_count=2)

    deterministic_fallback = _base()
    deterministic_fallback.update(must_eligible_count=6, must_pending_verification_count=0, must_rejected_count=2)
    deterministic_fallback["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "DETERMINISTIC_FALLBACK"}
    }

    nice_unknown = _base()
    nice_unknown.update(must_eligible_count=5, must_pending_verification_count=0, must_rejected_count=2)
    nice_unknown["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_RANKED"},
        "dynamic_preferences": {
            "preference_count": 3,
            "nice_complete_candidate_count": 1,
            "verification_required_count": 4,
        },
    }

    final = _base()
    final.update(must_eligible_count=5, must_pending_verification_count=0, must_rejected_count=2)
    final["decision_intelligence"]["facility_selection_pipeline"] = {
        "ai_ranking": {"status": "AI_BATCH_RANKED"},
        "dynamic_preferences": {
            "preference_count": 2,
            "nice_complete_candidate_count": 5,
            "verification_required_count": 0,
        },
    }

    ambiguous = {"decision_intelligence": {}, "results": []}

    return [
        {
            "id": "client-owned-blocker",
            "payload": client_blocked,
            "phase": DecisionPhase.CLIENT_INPUT_REQUIRED,
            "next": "ASK_CLIENT",
            "conflicts": {"LEGACY_READINESS_ADVANCES_WITH_CLIENT_BLOCKERS"},
        },
        {
            "id": "provider-must-unknown",
            "payload": provider_unknown,
            "phase": DecisionPhase.EVIDENCE_COLLECTION,
            "next": "RESEARCH_PROVIDER_EVIDENCE",
            "conflicts": {"LEGACY_EXECUTION_ALLOWS_PREMATURE_RECOMMENDATION"},
        },
        {"id": "required-ai-failure", "payload": ai_failure, "phase": DecisionPhase.SYSTEM_BLOCKED, "next": "RECOVER_SYSTEM"},
        {"id": "required-ai-disabled", "payload": ai_disabled, "phase": DecisionPhase.SYSTEM_BLOCKED, "next": "RECOVER_SYSTEM"},
        {"id": "ranking-fail-closed", "payload": ranking_fail_closed, "phase": DecisionPhase.SYSTEM_BLOCKED, "next": "RECOVER_SYSTEM"},
        {"id": "legacy-ai-visibility-block", "payload": legacy_visibility_block, "phase": DecisionPhase.SYSTEM_BLOCKED, "next": "RECOVER_SYSTEM"},
        {"id": "no-eligible-candidates", "payload": no_eligible, "phase": DecisionPhase.MUST_EVALUATION, "next": "EXPAND_OR_REVISE_STRATEGY"},
        {"id": "must-pass-awaiting-ranking", "payload": ranking, "phase": DecisionPhase.AI_RANKING, "next": "RUN_AI_RANKING"},
        {"id": "deterministic-fallback-not-ai-complete", "payload": deterministic_fallback, "phase": DecisionPhase.AI_RANKING, "next": "RUN_AI_RANKING"},
        {"id": "ranked-with-nice-unknowns", "payload": nice_unknown, "phase": DecisionPhase.PREFERENCE_VERIFICATION, "next": "VERIFY_MATERIAL_PREFERENCES"},
        {"id": "complete-decision", "payload": final, "phase": DecisionPhase.FINAL_RECOMMENDATION, "next": "SHOW_FINAL_RECOMMENDATION"},
        {
            "id": "ambiguous-payload",
            "payload": ambiguous,
            "phase": DecisionPhase.CLIENT_INPUT_REQUIRED,
            "next": "RESOLVE_STATE_AMBIGUITY",
            "system": SystemHealth.DEGRADED,
        },
    ]


def main() -> int:
    failed = 0
    conflict_total = 0
    for fixture in _fixtures():
        state = derive_canonical_decision_state(fixture["payload"])
        conflicts = set(legacy_state_conflicts(state))
        conflict_total += len(conflicts)
        expected_conflicts = fixture.get("conflicts")
        conflict_ok = expected_conflicts is None or conflicts == expected_conflicts
        system_ok = fixture.get("system") is None or state.system is fixture["system"]
        ok = (
            state.phase is fixture["phase"]
            and state.next_action == fixture["next"]
            and conflict_ok
            and system_ok
        )
        marker = "[OK]" if ok else "[XX]"
        print(f"{marker} {fixture['id']}: {state.phase.value} -> {state.next_action}")
        if conflicts:
            print(f"    legacy_conflicts={','.join(sorted(conflicts))}")
        if not ok:
            failed += 1
            print(f"    expected={fixture['phase'].value} -> {fixture['next']}")
            if expected_conflicts is not None:
                print(f"    expected_conflicts={','.join(sorted(expected_conflicts))}")
            if fixture.get("system") is not None:
                print(f"    expected_system={fixture['system'].value}; actual_system={state.system.value}")

    total = len(_fixtures())
    print(f"\n{total - failed}/{total} canonical lifecycle fixtures match; {conflict_total} legacy conflict(s) surfaced.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
