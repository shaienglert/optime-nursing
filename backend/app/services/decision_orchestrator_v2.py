from __future__ import annotations

"""Explicit OPTIME Nursing V2 decision orchestrator.

This is the architectural replacement for import-hook/wrapper composition. Raw client
input is consumed only by the canonical client interpreter. Every later stage receives
canonical state objects only.

The first migration version is dependency-injected deliberately: it lets us prove the
process contract before swapping production adapters one by one. Adapters may load
legacy data during migration, but they may not make new client decisions.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Sequence


ClientInterpreter = Callable[[Dict[str, Any], str], Dict[str, Any]]
UniverseLoader = Callable[[Dict[str, Any]], Sequence[Dict[str, Any]]]
FacilityStateLoader = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
MustEvaluator = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
Ranker = Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]
NiceVerifier = Callable[[List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]]
ProcessSynthesizer = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class DecisionOrchestratorDependencies:
    interpret_client: ClientInterpreter
    load_candidate_universe: UniverseLoader
    load_facility_state: FacilityStateLoader
    evaluate_must: MustEvaluator
    rank_all_must_eligible: Ranker
    verify_top_nice: NiceVerifier
    synthesize_process: ProcessSynthesizer


def _require_canonical_client_state(state: Dict[str, Any]) -> None:
    governance = state.get("governance") if isinstance(state.get("governance"), dict) else {}
    if governance.get("single_interpretation") is not True:
        raise RuntimeError("V2_CLIENT_STATE_NOT_SINGLE_INTERPRETATION")
    if governance.get("downstream_raw_text_reparse_forbidden") is not True:
        raise RuntimeError("V2_CLIENT_STATE_RAW_REPARSE_NOT_FORBIDDEN")
    if not isinstance(state.get("requirements"), list):
        raise RuntimeError("V2_CLIENT_STATE_REQUIREMENTS_MISSING")
    if not isinstance(state.get("strategy_candidates"), list):
        raise RuntimeError("V2_CLIENT_STATE_STRATEGIES_MISSING")


def _require_canonical_facility_state(state: Dict[str, Any]) -> None:
    if not str(state.get("canonical_facility_id") or "").strip():
        raise RuntimeError("V2_FACILITY_STATE_ID_MISSING")
    if state.get("canonical_evidence_state") is not True:
        raise RuntimeError("V2_FACILITY_STATE_NOT_CANONICAL")


def _must_requirements(client_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        requirement
        for requirement in client_state.get("requirements") or []
        if isinstance(requirement, dict)
        and str(requirement.get("importance") or "").upper() == "MUST"
        and str(requirement.get("knowledge_state") or "KNOWN").upper() == "KNOWN"
    ]


def _partition_by_must(rows: Iterable[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    eligible: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for row in rows:
        must = row.get("authoritative_must") if isinstance(row.get("authoritative_must"), dict) else {}
        status = str(must.get("status") or "PENDING_VERIFICATION").upper()
        if status == "PASS":
            eligible.append(row)
        elif status == "FAIL":
            rejected.append(row)
        elif status == "PENDING_VERIFICATION":
            pending.append(row)
        else:
            raise RuntimeError(f"V2_INVALID_MUST_STATUS:{status}")
    return eligible, pending, rejected


def _validate_ranked_closed_world(eligible: List[Dict[str, Any]], ranked: List[Dict[str, Any]]) -> None:
    expected = [str(row.get("canonical_facility_id")) for row in eligible]
    actual = [str(row.get("canonical_facility_id")) for row in ranked]
    if len(actual) != len(expected) or len(set(actual)) != len(actual) or set(actual) != set(expected):
        raise RuntimeError("V2_ALL_MUST_ELIGIBLE_NOT_AI_RANKED")
    for row in ranked:
        ai = row.get("ai_ranking") if isinstance(row.get("ai_ranking"), dict) else {}
        if str(ai.get("status") or "").upper() not in {"AI_RANKED", "AI_BATCH_SCORED", "AI_GLOBAL_RANKED"}:
            raise RuntimeError("V2_NON_AI_RANKING_IN_AUTHORITATIVE_PATH")


def _validate_final_top(rows: List[Dict[str, Any]], limit: int) -> None:
    if len(rows) > min(5, max(0, int(limit))):
        raise RuntimeError("V2_TOP_N_EXCEEDS_FIVE")
    for row in rows:
        must = row.get("authoritative_must") if isinstance(row.get("authoritative_must"), dict) else {}
        if str(must.get("status") or "").upper() != "PASS":
            raise RuntimeError("V2_NON_MUST_PASS_VISIBLE_RECOMMENDATION")


def run_decision_orchestrator_v2(
    *,
    questionnaire_state: Dict[str, Any],
    natural_language_query: str,
    dependencies: DecisionOrchestratorDependencies,
    limit: int = 5,
) -> Dict[str, Any]:
    """Run the complete V2 lifecycle through one explicit entrypoint.

    Critical contract: after `interpret_client`, this function never passes raw client
    text/questionnaire to any dependency. Downstream code receives canonical state only.
    """
    client_state = dependencies.interpret_client(questionnaire_state, natural_language_query)
    _require_canonical_client_state(client_state)

    readiness = str(client_state.get("decision_readiness") or "NEEDS_CLARIFICATION").upper()
    if readiness == "NEEDS_CLARIFICATION":
        next_question = client_state.get("next_question") if isinstance(client_state.get("next_question"), dict) else {}
        return {
            "version": "nursing-decision-orchestrator-v2",
            "status": "NEEDS_CLARIFICATION",
            "canonical_client_state": client_state,
            "results": [],
            "result_count": 0,
            "next_question": next_question,
            "process_owner": {
                "owner": "SEMANTIC_AI",
                "phase": "CLARIFICATION",
                "next_best_action": "ASK_CLIENT",
            },
        }
    if readiness != "READY":
        raise RuntimeError(f"V2_INVALID_CLIENT_READINESS:{readiness}")

    raw_universe = list(dependencies.load_candidate_universe(client_state))
    facility_states: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for candidate in raw_universe:
        facility_state = dependencies.load_facility_state(candidate, client_state)
        _require_canonical_facility_state(facility_state)
        canonical_id = str(facility_state.get("canonical_facility_id"))
        if canonical_id in seen_ids:
            raise RuntimeError(f"V2_DUPLICATE_CANONICAL_FACILITY:{canonical_id}")
        seen_ids.add(canonical_id)
        facility_state["authoritative_must"] = dependencies.evaluate_must(
            facility_state,
            {"requirements": _must_requirements(client_state), "client_state_version": client_state.get("version")},
        )
        facility_states.append(facility_state)

    eligible, pending, rejected = _partition_by_must(facility_states)

    ranked = dependencies.rank_all_must_eligible(eligible, client_state) if eligible else []
    _validate_ranked_closed_world(eligible, ranked)

    visible_limit = min(5, max(0, int(limit)))
    top_for_verification = ranked[: min(10, max(visible_limit, 5))]
    verified_top = dependencies.verify_top_nice(top_for_verification, client_state) if top_for_verification else []

    verified_by_id = {str(row.get("canonical_facility_id")): row for row in verified_top}
    final_rows = [verified_by_id.get(str(row.get("canonical_facility_id")), row) for row in ranked[:visible_limit]]
    _validate_final_top(final_rows, visible_limit)

    decision = {
        "version": "nursing-decision-orchestrator-v2",
        "status": "PROVISIONAL" if pending else "READY_TO_COMPARE",
        "canonical_client_state": client_state,
        "candidate_universe_count": len(facility_states),
        "must_eligible_count": len(eligible),
        "must_pending_verification_count": len(pending),
        "must_rejected_count": len(rejected),
        "all_must_eligible_ai_ranked": len(ranked) == len(eligible),
        "pending_verification": [
            {
                "canonical_facility_id": row.get("canonical_facility_id"),
                "facility_name": row.get("facility_name"),
                "authoritative_must": row.get("authoritative_must"),
            }
            for row in pending
        ],
        "results": final_rows,
        "result_count": len(final_rows),
        "rules": {
            "raw_client_input_interpreted_once": True,
            "all_must_eligible_candidates_ai_ranked": True,
            "pending_must_never_visible_as_recommendation": True,
            "top_n_is_up_to_five": True,
        },
    }
    decision["process_owner"] = dependencies.synthesize_process(decision)
    return decision


__all__ = ["DecisionOrchestratorDependencies", "run_decision_orchestrator_v2"]
