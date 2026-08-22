from app.services.semantic_intent_ai import (
    _explicit_user_text_answered_dimensions,
    _question_reasks_answered_dimension,
    interpret_client_intent_with_ai,
)


def _packet(question: str, readiness: str = "NEEDS_CLARIFICATION"):
    return {
        "facts": [],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": [
            {
                "raw_text": "mobility",
                "meaning": "mobility status",
                "importance": "MUST",
                "knowledge_state": "UNKNOWN",
                "status": "ASKED",
                "mapped_parameters": ["mobility"],
                "clarification_question": question,
                "research_task": None,
            }
        ],
        "next_question": question,
        "research_requests": [],
        "decision_readiness": readiness,
    }


def _ready_packet():
    return {
        "facts": ["No mobility limitation"],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": [
            {
                "raw_text": "no mobility limitation",
                "meaning": "No mobility limitation",
                "importance": "MUST",
                "knowledge_state": "KNOWN",
                "status": "USED",
                "mapped_parameters": ["mobility"],
                "clarification_question": None,
                "research_task": None,
            }
        ],
        "next_question": None,
        "research_requests": [],
        "decision_readiness": "READY",
    }


def test_explicit_free_text_mobility_answer_is_not_reasked(monkeypatch):
    calls = []

    def transport(payload):
        calls.append(payload)
        if "clarification_contract_repair" in payload:
            assert "no mobility limitation" in payload["clarification_contract_repair"]["original_user_text"].lower()
            return _ready_packet()
        return _packet("Does she use a walker, cane, wheelchair, or need help walking at all?")

    monkeypatch.setattr("app.services.semantic_intent_ai._default_transport", transport)
    result = interpret_client_intent_with_ai(
        user_text=(
            "My mother is looking for senior living in Las Vegas. "
            "She has no mobility limitation and walks independently. "
            "Her total monthly budget is up to $8,000."
        ),
        questionnaire_state={},
    )

    assert result["decision_readiness"] == "READY"
    assert result["next_question"] is None
    assert any("clarification_contract_repair" in call for call in calls)


def test_dimension_label_without_answer_does_not_suppress_question():
    text = "Location and mobility still need to be discussed."
    assert _explicit_user_text_answered_dimensions(text) == set()
    packet = _packet("What city or area should I search in?")
    assert _question_reasks_answered_dimension(packet, {}, text) is False


def test_explicit_location_and_budget_are_recognized_as_answers():
    text = "Please search in Las Vegas. Her monthly budget is $8,000."
    answered = _explicit_user_text_answered_dimensions(text)
    assert {"location", "budget"}.issubset(answered)
