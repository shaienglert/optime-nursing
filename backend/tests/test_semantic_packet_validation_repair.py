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
                        "mapped_parameters": ["medicalCareProfile.needs"]}],
    }


@pytest.mark.parametrize("failure", ["missing_readiness", "invalid_importance", "missing_statements"])
def test_live_invalid_packet_gets_one_explicit_validation_repair(failure):
    bad = packet()
    if failure == "missing_readiness":
        del bad["decision_readiness"]
    elif failure == "missing_statements":
        bad["statements"] = []
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


def test_repeated_field_contract_violation_never_returns_a_usable_packet():
    bad = packet()
    bad["questionnaire_patch"]["budget"] = 0
    bad["statements"].append({"raw_text": "monthly budget is $6500", "meaning": "Budget",
        "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED",
        "mapped_parameters": ["budget"]})
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[deepcopy(bad), deepcopy(bad)]) as transport:
        with pytest.raises(RuntimeError, match="NONPOSITIVE_VALUE:budget"):
            interpret_client_intent_with_ai(user_text=TEXT)
    assert transport.call_count == 2
    assert "packet_validation_repair" in transport.call_args.args[0]


def test_injected_transport_cannot_bypass_field_acceptance():
    bad = packet()
    bad["questionnaire_patch"]["budget"] = 0
    with pytest.raises(RuntimeError, match="NONPOSITIVE_VALUE:budget"):
        interpret_client_intent_with_ai(user_text=TEXT, transport=lambda _: bad)


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


def test_structured_only_case_may_have_no_narrative_statements():
    structured = {"budget": 6500, "referenceLocationValue": "Las Vegas"}
    response = packet()
    response["statements"] = []
    response["questionnaire_patch"] = {}
    with patch("app.services.semantic_intent_ai._default_transport", return_value=response) as transport:
        result = interpret_client_intent_with_ai(user_text="", questionnaire_state=structured)
    assert transport.call_count == 1
    assert result["statements"] == []
    assert result["decision_readiness"] == "READY"


COUPLE_TEXT = "They are a couple; he needs help with daily activities and she is independent."
COUPLE_BASELINE = {"referenceLocationValue": "Las Vegas, Nevada", "budget": 6000}


def couple_packet():
    # Reproduces live I09: known partner facts, but clarification with no question.
    return {
        "decision_readiness": "NEEDS_CLARIFICATION", "next_question": None,
        "questionnaire_patch": {"relationship": "Couple", "coupleAssistance": "He needs help with daily activities; she is independent"},
        "questionnaire_patch_sources": {"relationship": "They are a couple",
            "coupleAssistance": "he needs help with daily activities and she is independent"},
        "statements": [
            {"raw_text": "They are a couple", "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["relationship"]},
            {"raw_text": "he needs help with daily activities", "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["coupleAssistance"]},
            {"raw_text": "she is independent", "importance": "MUST", "knowledge_state": "KNOWN", "status": "USED", "mapped_parameters": ["coupleAssistance"]},
        ],
    }


def test_i09_repair_preserves_both_partners_and_asks_about_the_unresolved_care_fact():
    invalid = couple_packet()
    corrected = deepcopy(invalid)
    question = "Which daily tasks does he need help with?"
    corrected["next_question"] = question
    corrected["statements"].append({
        "raw_text": "he needs help with daily activities", "meaning": "Specific assistance tasks are unspecified",
        "importance": "MUST", "knowledge_state": "AMBIGUOUS", "status": "ASKED",
        "gap_key": "daily_assistance_tasks", "clarification_question": question,
    })
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[deepcopy(invalid), deepcopy(invalid), deepcopy(invalid), corrected]) as transport:
        result = interpret_client_intent_with_ai(user_text=COUPLE_TEXT, questionnaire_state=COUPLE_BASELINE)
    assert transport.call_count == 4
    repair = transport.call_args.args[0]["packet_validation_repair"]
    assert repair["client_dimension_status"] == {"market_location": True, "monthly_affordability": True}
    assert repair["prior_packet"]["questionnaire_patch"] == invalid["questionnaire_patch"]
    assert result["questionnaire_patch"] == invalid["questionnaire_patch"]
    assert result["questionnaire_patch_sources"] == invalid["questionnaire_patch_sources"]
    assert result["next_question"] == question
    assert result["decision_readiness"] == "NEEDS_CLARIFICATION"
    assert [s["gap_key"] for s in result["statements"] if s["status"] == "ASKED"] == ["daily_assistance_tasks"]


def test_i09_repeated_missing_question_stays_blocked_after_the_existing_attempt_limit():
    invalid = couple_packet()
    with patch("app.services.semantic_intent_ai._default_transport", side_effect=[deepcopy(invalid) for _ in range(4)]) as transport:
        with pytest.raises(RuntimeError, match="CLARIFICATION_WITHOUT_BLOCKING_QUESTION") as error:
            interpret_client_intent_with_ai(user_text=COUPLE_TEXT, questionnaire_state=COUPLE_BASELINE)
    assert transport.call_count == 4
    assert error.value.patch_diagnostic["patch"] == invalid["questionnaire_patch"]
    assert error.value.patch_diagnostic["next_question"] is None
