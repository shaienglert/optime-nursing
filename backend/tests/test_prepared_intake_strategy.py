from copy import deepcopy
from unittest.mock import patch

import pytest

from app.services import human_intelligence_runtime_verified as human
from app.services import patient_decision_engine_runtime as runtime


@pytest.mark.parametrize("strategy", [{}, {"signals": {}, "household": {"type": "COUPLE"}}])
def test_prepared_strategy_is_consumed_without_reinterpretation(strategy):
    before = deepcopy(strategy)
    with patch.object(human, "build_living_strategy_context", side_effect=AssertionError("reinterpreted intake")), \
         patch.object(human._base, "build_human_intelligence_context", return_value={}), \
         patch.object(human, "_governed_context", return_value={}) as governed, \
         patch.object(human, "_consult_semantic_ai", side_effect=lambda context, *args: context):
        human.build_human_intelligence_context({}, "couple", prepared_strategy=strategy)
    assert governed.call_args.args[1] is strategy
    assert strategy == before


def test_profile_strategy_is_built_by_the_runtime_only_and_matches_standalone_context(monkeypatch):
    """The human-intelligence context never builds its own strategy inside the runtime.

    Single authority (owner, 2026-10-01): the runtime builds the strategy exactly twice and
    never from free text -- once for the interpreter pass (raw structured answers) and once
    from the Canonical Structured Profile the interpreter produced, which is the strategy
    every decision fact uses. Neither build reads the story.
    """
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "0")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_REQUIRED", "0")
    state = {"relationship": "Mom", "budget": 5000}
    story = "Mother is independent and wants social activities in Las Vegas."
    expected = human.build_human_intelligence_context(state, story)
    with patch.object(runtime, "build_living_strategy_context", wraps=runtime.build_living_strategy_context) as builder, \
         patch.object(human, "build_living_strategy_context", side_effect=AssertionError("second strategy build")):
        profile = runtime.build_patient_needs_profile(state, story)
    # Was assert_called_once(); the owner rule (2026-10-01) requires a second, profile-derived
    # build: interpreter pass first, then the decision strategy from the materialized profile.
    assert builder.call_count == 2
    interpreter_call, decision_call = builder.call_args_list
    assert all(call.args[1] == "" for call in builder.call_args_list), "a strategy was built from free text"
    assert "_structured_profile_authoritative" not in interpreter_call.args[0]
    assert decision_call.args[0].get("_structured_profile_authoritative") is True
    # The runtime deliberately attaches the full strategy and merges questions
    # after human-context construction; compare the shared interpretation first.
    actual = profile["decision_intelligence"]["human_intelligence"]
    for key in ("signals", "semantic_ai", "intake_resolution", "readiness_guardian"):
        assert actual.get(key) == expected.get(key)
    assert actual["living_strategy"] is profile["living_strategy"]
