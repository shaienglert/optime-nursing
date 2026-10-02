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
         patch.object(human, "_consult_semantic_ai", side_effect=lambda context, *args, **kwargs: context):
        human.build_human_intelligence_context({}, "couple", prepared_strategy=strategy)
    assert governed.call_args.args[1] is strategy
    assert strategy == before


def test_strategy_and_guardian_are_built_once_from_canonical_state(monkeypatch):
    """Owner order (2026-10-02): Interpreter -> validated canonical profile -> materialize
    -> strategy/guardian ONCE from canonical state. No second build, no build from raw
    answers or free text."""
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "0")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_REQUIRED", "0")
    state = {"relationship": "Mom", "budget": 5000}
    story = "Mother is independent and wants social activities in Las Vegas."
    expected = human.build_human_intelligence_context(state, story)
    with patch.object(runtime, "build_living_strategy_context", side_effect=AssertionError("runtime rebuilt the strategy")), \
         patch.object(human, "build_living_strategy_context", wraps=human.build_living_strategy_context) as builder, \
         patch.object(human, "_governed_context", wraps=human._governed_context) as guardian:
        profile = runtime.build_patient_needs_profile(state, story)
    assert builder.call_count == 1 and guardian.call_count == 1
    (state_arg, text_arg), _ = builder.call_args
    assert text_arg == "" and state_arg.get("_structured_profile_authoritative") is True
    assert guardian.call_args.args[3].get("_structured_profile_authoritative") is True
    actual = profile["decision_intelligence"]["human_intelligence"]
    for key in ("signals", "semantic_ai", "intake_resolution", "readiness_guardian"):
        assert actual.get(key) == expected.get(key)
    assert actual["living_strategy"] is profile["living_strategy"]
