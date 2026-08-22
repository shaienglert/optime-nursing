from app.services.semantic_intent_ai import (
    _question_reasks_answered_dimension,
    _repair_clarification_contract_with_ai,
    _repair_missing_minimum_dimensions_with_ai,
    _validate_result,
)


def _state(question: str, answer: str):
    return {
        "humanIntelligenceV2": {
            "scoringEngine": {
                "adaptiveSignals": [
                    {
                        "questionKey": "prior",
                        "answer": answer,
                        "impactExplanation": f"Question: {question} | explicit client answer",
                    }
                ]
            }
        }
    }


def _packet(*, readiness="NEEDS_CLARIFICATION", question=None):
    status = "ASKED" if question else "USED"
    return {
        "facts": [],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": [
            {
                "raw_text": "client intent",
                "meaning": "client intent",
                "importance": "MUST",
                "knowledge_state": "UNKNOWN" if question else "KNOWN",
                "status": status,
                "mapped_parameters": [],
                "clarification_question": question,
                "research_task": None,
            }
        ],
        "next_question": question,
        "research_requests": [],
        "decision_readiness": readiness,
    }


def test_guardian_detects_semantic_reask_of_answered_mobility_dimension():
    state = _state(
        "Does she walk independently or use a walker or wheelchair?",
        "She walks independently and has no mobility limitation, walker, or wheelchair requirement.",
    )
    packet = {
        "decision_readiness": "NEEDS_CLARIFICATION",
        "next_question": "Can you confirm whether she has any mobility limitations or needs help walking or using stairs?",
    }
    assert _question_reasks_answered_dimension(packet, state) is True


def test_unrelated_new_question_is_not_treated_as_duplicate():
    state = _state(
        "Does she walk independently or use a walker or wheelchair?",
        "She walks independently and has no mobility limitation.",
    )
    packet = {
        "decision_readiness": "NEEDS_CLARIFICATION",
        "next_question": "What city or metro area should I search in?",
    }
    assert _question_reasks_answered_dimension(packet, state) is False


def test_needs_clarification_without_blocking_question_fails_closed():
    packet = {
        "facts": ["Location is Las Vegas"],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": [
            {
                "raw_text": "Las Vegas",
                "meaning": "Search Las Vegas",
                "importance": "MUST",
                "knowledge_state": "KNOWN",
                "status": "USED",
                "mapped_parameters": ["location"],
                "clarification_question": None,
                "research_task": None,
            }
        ],
        "next_question": None,
        "research_requests": [],
        "decision_readiness": "NEEDS_CLARIFICATION",
    }
    try:
        _validate_result(packet)
    except RuntimeError as exc:
        assert "SEMANTIC_AI_CLARIFICATION_WITHOUT_BLOCKING_QUESTION" in str(exc)
    else:
        raise AssertionError("invalid clarification packet must fail closed")


def test_first_malformed_repair_can_fall_through_to_minimum_dimension_repair():
    calls = []

    def clarification_transport(payload):
        calls.append(payload)
        return _packet(readiness="NEEDS_CLARIFICATION", question=None)

    malformed = _packet(readiness="NEEDS_CLARIFICATION", question=None)
    first_pass = _repair_clarification_contract_with_ai(
        result=malformed,
        payload={},
        user_text="",
        questionnaire_state={},
        transport=clarification_transport,
        strict=False,
    )
    assert first_pass["decision_readiness"] == "NEEDS_CLARIFICATION"
    assert first_pass["next_question"] is None

    def minimum_transport(payload):
        calls.append(payload)
        assert payload["readiness_repair"]["missing_client_owned_dimensions"] == [
            "market_location",
            "monthly_affordability",
        ]
        return _packet(
            readiness="NEEDS_CLARIFICATION",
            question="What city or area should I search in?",
        )

    repaired = _repair_missing_minimum_dimensions_with_ai(
        result=first_pass,
        payload={},
        user_text="",
        questionnaire_state={},
        transport=minimum_transport,
    )
    assert repaired["decision_readiness"] == "NEEDS_CLARIFICATION"
    assert repaired["next_question"] == "What city or area should I search in?"
