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


def test_profile_strategy_is_built_once_and_matches_standalone_context(monkeypatch):
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_ENABLED", "0")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_REQUIRED", "0")
    state = {"relationship": "Mom", "budget": 5000}
    story = "Mother is independent and wants social activities in Las Vegas."
    expected = human.build_human_intelligence_context(state, story)
    with patch.object(runtime, "build_living_strategy_context", wraps=runtime.build_living_strategy_context) as builder, \
         patch.object(human, "build_living_strategy_context", side_effect=AssertionError("second strategy build")):
        profile = runtime.build_patient_needs_profile(state, story)
    builder.assert_called_once()
    # The runtime deliberately attaches the full strategy and merges questions
    # after human-context construction; compare the shared interpretation first.
    actual = profile["decision_intelligence"]["human_intelligence"]
    for key in ("signals", "semantic_ai", "intake_resolution", "readiness_guardian"):
        assert actual.get(key) == expected.get(key)
    assert actual["living_strategy"] is profile["living_strategy"]
