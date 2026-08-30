from __future__ import annotations

"""Default production adapters for the explicit Nursing V2 decision orchestrator."""

from typing import Any, Dict, Sequence

from app.services.canonical_ai_ranker_v2 import rank_all_canonical_must_eligible_v2
from app.services.canonical_client_ai_v2 import build_canonical_client_ai_state
from app.services.canonical_facility_runtime_v2 import CanonicalFacilityRuntimeV2
from app.services.canonical_must_guard_v2 import evaluate_canonical_must_v2
from app.services.canonical_nice_verifier_v2 import verify_top_nice_canonical_v2
from app.services.canonical_process_owner_v2 import synthesize_process_owner_v2
from app.services.canonical_strategy_universe_v2 import filter_universe_by_canonical_strategy_v2
from app.services.decision_orchestrator_v2 import DecisionOrchestratorDependencies, run_decision_orchestrator_v2


class NursingDecisionRuntimeV2:
    """One request-scoped runtime; no import-hook composition."""

    def __init__(self) -> None:
        self.facilities = CanonicalFacilityRuntimeV2()
        self.strategy_universe_meta: Dict[str, Any] = {}

    def interpret_client(self, questionnaire_state: Dict[str, Any], natural_language_query: str) -> Dict[str, Any]:
        return build_canonical_client_ai_state(questionnaire_state, natural_language_query)

    def load_candidate_universe(self, client_state: Dict[str, Any]) -> Sequence[Dict[str, Any]]:
        market_rows = list(self.facilities.load_candidate_universe(client_state))
        selected, meta = filter_universe_by_canonical_strategy_v2(market_rows, client_state)
        self.strategy_universe_meta = meta
        return selected

    def load_facility_state(self, candidate: Dict[str, Any], client_state: Dict[str, Any]) -> Dict[str, Any]:
        return self.facilities.load_facility_state(candidate, client_state)

    def evaluate_must(self, facility_state: Dict[str, Any], must_context: Dict[str, Any]) -> Dict[str, Any]:
        return evaluate_canonical_must_v2(facility_state, must_context)

    def rank_all(self, rows, client_state):
        return rank_all_canonical_must_eligible_v2(rows, client_state)

    def verify_nice(self, rows, client_state):
        return verify_top_nice_canonical_v2(rows, client_state)

    def synthesize(self, decision):
        enriched = {**decision, "strategy_universe": self.strategy_universe_meta}
        return synthesize_process_owner_v2(enriched)

    def dependencies(self) -> DecisionOrchestratorDependencies:
        return DecisionOrchestratorDependencies(
            interpret_client=self.interpret_client,
            load_candidate_universe=self.load_candidate_universe,
            load_facility_state=self.load_facility_state,
            evaluate_must=self.evaluate_must,
            rank_all_must_eligible=self.rank_all,
            verify_top_nice=self.verify_nice,
            synthesize_process=self.synthesize,
        )


def run_nursing_decision_v2(
    questionnaire_state: Dict[str, Any],
    natural_language_query: str = "",
    limit: int = 5,
) -> Dict[str, Any]:
    runtime = NursingDecisionRuntimeV2()
    result = run_decision_orchestrator_v2(
        questionnaire_state=questionnaire_state,
        natural_language_query=natural_language_query,
        dependencies=runtime.dependencies(),
        limit=limit,
    )
    result["strategy_universe"] = runtime.strategy_universe_meta
    result["architecture"] = {
        "version": "NURSING_DECISION_ARCHITECTURE_V2",
        "orchestrator": "EXPLICIT_SINGLE_ENTRYPOINT",
        "client_truth": "CANONICAL_CLIENT_AI_STATE",
        "facility_truth": "CANONICAL_FACILITY_EVIDENCE_STATE",
        "must_owner": "DETERMINISTIC_GUARDIAN",
        "ranking_owner": "SEMANTIC_AI_ALL_MUST_ELIGIBLE",
        "nice_owner": "SEMANTIC_AI_CLOSED_WORLD_EVIDENCE",
        "process_owner": "SEMANTIC_AI_GOVERNED",
        "raw_reparse_downstream": False,
    }
    return result


__all__ = ["NursingDecisionRuntimeV2", "run_nursing_decision_v2"]
