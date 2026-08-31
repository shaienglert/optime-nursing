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

    ranking = _base()
    ranking.update(must_eligible_count=8, must_pending_verification_count=0, must_rejected_count=2)

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

    return [
        {"id": "client-owned-blocker", "payload": client_blocked, "phase": DecisionPhase.CLIENT_INPUT_REQUIRED, "next": "ASK_CLIENT"},
        {"id": "provider-must-unknown", "payload": provider_unknown, "phase": DecisionPhase.EVIDENCE_COLLECTION, "next": "RESEARCH_PROVIDER_EVIDENCE"},
        {"id": "required-ai-failure", "payload": ai_failure, "phase": DecisionPhase.SYSTEM_BLOCKED, "next": "RECOVER_SYSTEM"},
        {"id": "must-pass-awaiting-ranking", "payload": ranking, "phase": DecisionPhase.AI_RANKING, "next": "RUN_AI_RANKING"},
        {"id": "ranked-with-nice-unknowns", "payload": nice_unknown, "phase": DecisionPhase.PREFERENCE_VERIFICATION, "next": "VERIFY_MATERIAL_PREFERENCES"},
        {"id": "complete-decision", "payload": final, "phase": DecisionPhase.FINAL_RECOMMENDATION, "next": "SHOW_FINAL_RECOMMENDATION"},
    ]


def main() -> int:
    failed = 0
    conflict_total = 0
    for fixture in _fixtures():
        state = derive_canonical_decision_state(fixture["payload"])
        conflicts = legacy_state_conflicts(state)
        conflict_total += len(conflicts)
        ok = state.phase is fixture["phase"] and state.next_action == fixture["next"]
        marker = "[OK]" if ok else "[XX]"
        print(f"{marker} {fixture['id']}: {state.phase.value} -> {state.next_action}")
        if conflicts:
            print(f"    legacy_conflicts={','.join(conflicts)}")
        if not ok:
            failed += 1
            print(f"    expected={fixture['phase'].value} -> {fixture['next']}")

    total = len(_fixtures())
    print(f"\n{total - failed}/{total} canonical lifecycle fixtures match; {conflict_total} legacy conflict(s) surfaced.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
