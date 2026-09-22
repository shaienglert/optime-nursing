from copy import deepcopy
from unittest.mock import patch

import pytest

from app.services.semantic_intent_ai import interpret_client_intent_with_ai


TEXT = "My father needs dialysis three times a week in Las Vegas. His monthly budget is $6500."


@pytest.fixture(autouse=True)
def learning_advice():
    # These tests exercise provider packet validation, independently of DB setup.
    with patch("app.services.semantic_intent_ai.build_learning_center_advice", return_value={
        "advisor": "test", "available_agent_count": 0, "agent_count": 0,
    }):
        yield


def packet():
    return {
        "decision_readiness": "READY", "next_question": None,
        "questionnaire_patch": {"medicalCareProfile": {"needs": ["Dialysis"]}},
        "statements": [{"raw_text": "dialysis three times a week", "meaning": "Dialysis required",
                        "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED",
                        "mapped_parameters": ["dialysis_arrangements"]}],
    }


@pytest.mark.parametrize("failure", ["missing_readiness", "invalid_importance"])
def test_live_invalid_packet_gets_one_explicit_validation_repair(failure):
    bad = packet()
    if failure == "missing_readiness":
        del bad["decision_readiness"]
    else:
        bad["statements"][0]["importance"] = "REQUIRED"
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[bad, packet()]) as transport:
        result = interpret_client_intent_with_ai(user_text=TEXT)
    assert transport.call_count == 2
    assert "packet_validation_repair" in transport.call_args.args[0]
    assert result["questionnaire_patch"]["medicalCareProfile"]["needs"] == ["Dialysis"]
    assert result["statements"][0]["importance"] == "MUST"


def test_repeated_invalid_repair_stays_blocked_and_does_not_loop():
    bad = packet()
    del bad["decision_readiness"]
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[deepcopy(bad), deepcopy(bad)]) as transport:
        with pytest.raises(RuntimeError, match="CLARIFICATION_WITHOUT_BLOCKING_QUESTION"):
            interpret_client_intent_with_ai(user_text=TEXT)
    assert transport.call_count == 2


def test_final_repair_can_recover_failed_question_repairs_with_ai_authored_question():
    bad = packet()
    bad["decision_readiness"] = "NEEDS_CLARIFICATION"
    corrected = packet()
    corrected["decision_readiness"] = "NEEDS_CLARIFICATION"
    corrected["next_question"] = "Does he need help arranging transport to his dialysis center?"
    corrected["statements"].append({"raw_text": "Dialysis transportation is unspecified", "meaning": "Transport needs clarification",
        "importance": "UNKNOWN", "knowledge_state": "UNKNOWN", "status": "ASKED",
        "gap_key": "dialysis_transportation", "clarification_question": corrected["next_question"]})
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[deepcopy(bad), deepcopy(bad), deepcopy(bad), corrected]) as transport:
        result = interpret_client_intent_with_ai(user_text=TEXT)
    assert transport.call_count == 4
    assert result["decision_readiness"] == "NEEDS_CLARIFICATION"
    assert result["next_question"] == corrected["next_question"]


def test_final_repair_must_not_erase_missing_minimum_client_information():
    bad = packet()
    del bad["decision_readiness"]
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[bad, packet()]):
        with pytest.raises(RuntimeError, match="MISSING_MINIMUM_DIMENSIONS"):
            interpret_client_intent_with_ai(user_text="My father needs dialysis")


def test_provider_failure_does_not_trigger_packet_repair():
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=RuntimeError("SEMANTIC_AI_HTTP_429")) as transport:
        with pytest.raises(RuntimeError, match="HTTP_429"):
            interpret_client_intent_with_ai(user_text=TEXT)
    assert transport.call_count == 1
