from __future__ import annotations

from app.services.decision_orchestrator_v2 import DecisionOrchestratorDependencies, run_decision_orchestrator_v2


def _client_state(readiness="READY"):
    return {
        "version": "canonical-client-v2",
        "decision_readiness": readiness,
        "requirements": [
            {"requirement_id": "r1", "importance": "MUST", "knowledge_state": "KNOWN", "capability_key": "MEDICATION_SUPPORT"},
            {"requirement_id": "r2", "importance": "NICE", "knowledge_state": "KNOWN", "capability_key": "CLASSICAL_MUSIC"},
        ],
        "strategy_candidates": [{"strategy_id": "ASSISTED_LIVING", "status": "LEADING"}],
        "next_question": {"question": "Which level?" if readiness == "NEEDS_CLARIFICATION" else None},
        "governance": {"single_interpretation": True, "downstream_raw_text_reparse_forbidden": True},
    }


def _deps(*, readiness="READY", universe=None, ranking_recorder=None):
    universe = universe or [
        {"id": "A", "must": "PASS"},
        {"id": "B", "must": "PASS"},
        {"id": "C", "must": "PENDING_VERIFICATION"},
        {"id": "D", "must": "FAIL"},
    ]

    def interpret_client(questionnaire, text):
        assert questionnaire == {"budget": 8000}
        assert "mother" in text.lower()
        return _client_state(readiness)

    def load_universe(client_state):
        assert "raw_input_provenance" not in client_state
        return universe

    def load_facility(candidate, client_state):
        return {
            "canonical_evidence_state": True,
            "canonical_facility_id": candidate["id"],
            "facility_name": candidate["id"],
            "fixture_must": candidate["must"],
        }

    def evaluate_must(facility_state, must_context):
        assert set(must_context) == {"requirements", "client_state_version"}
        return {
            "status": facility_state["fixture_must"],
            "pass": ["MEDICATION_SUPPORT"] if facility_state["fixture_must"] == "PASS" else [],
            "pending_verification": ["MEDICATION_SUPPORT"] if facility_state["fixture_must"] == "PENDING_VERIFICATION" else [],
            "fail": ["MEDICATION_SUPPORT"] if facility_state["fixture_must"] == "FAIL" else [],
            "authoritative": True,
        }

    def rank_all(rows, client_state):
        if ranking_recorder is not None:
            ranking_recorder.extend(row["canonical_facility_id"] for row in rows)
        return [
            {**row, "ai_ranking": {"status": "AI_RANKED", "rank": index + 1}}
            for index, row in enumerate(reversed(rows))
        ]

    def verify_nice(rows, client_state):
        return [{**row, "nice": {"status": "MATCH"}} for row in rows]

    def synthesize(decision):
        return {"owner": "SEMANTIC_AI", "phase": "COMPARE", "result_count": decision["result_count"]}

    return DecisionOrchestratorDependencies(
        interpret_client=interpret_client,
        load_candidate_universe=load_universe,
        load_facility_state=load_facility,
        evaluate_must=evaluate_must,
        rank_all_must_eligible=rank_all,
        verify_top_nice=verify_nice,
        synthesize_process=synthesize,
    )


def test_raw_client_input_is_consumed_only_by_interpreter_and_all_eligible_are_ranked():
    ranked_ids = []
    result = run_decision_orchestrator_v2(
        questionnaire_state={"budget": 8000},
        natural_language_query="My mother needs help",
        dependencies=_deps(ranking_recorder=ranked_ids),
        limit=5,
    )
    assert ranked_ids == ["A", "B"]
    assert result["candidate_universe_count"] == 4
    assert result["must_eligible_count"] == 2
    assert result["must_pending_verification_count"] == 1
    assert result["must_rejected_count"] == 1
    assert result["all_must_eligible_ai_ranked"] is True
    assert [row["canonical_facility_id"] for row in result["results"]] == ["B", "A"]
    assert result["rules"]["raw_client_input_interpreted_once"] is True


def test_pending_candidate_is_not_visible_even_when_fewer_than_five_pass():
    result = run_decision_orchestrator_v2(
        questionnaire_state={"budget": 8000},
        natural_language_query="My mother needs help",
        dependencies=_deps(),
        limit=5,
    )
    assert result["result_count"] == 2
    assert all(row["authoritative_must"]["status"] == "PASS" for row in result["results"])
    assert [row["canonical_facility_id"] for row in result["pending_verification"]] == ["C"]


def test_clarification_stops_before_facility_universe():
    called = {"universe": False}
    deps = _deps(readiness="NEEDS_CLARIFICATION")
    original = deps.load_candidate_universe

    def forbidden(client_state):
        called["universe"] = True
        return original(client_state)

    deps = DecisionOrchestratorDependencies(**{**deps.__dict__, "load_candidate_universe": forbidden})
    result = run_decision_orchestrator_v2(
        questionnaire_state={"budget": 8000},
        natural_language_query="My mother needs help",
        dependencies=deps,
    )
    assert result["status"] == "NEEDS_CLARIFICATION"
    assert called["universe"] is False


def test_top_n_is_up_to_five_not_exactly_five():
    universe = [{"id": f"F{i}", "must": "PASS"} for i in range(1, 8)]
    result = run_decision_orchestrator_v2(
        questionnaire_state={"budget": 8000},
        natural_language_query="My mother needs help",
        dependencies=_deps(universe=universe),
        limit=10,
    )
    assert result["must_eligible_count"] == 7
    assert result["all_must_eligible_ai_ranked"] is True
    assert result["result_count"] == 5
