from app.services.semantic_intent_ai import _validate_result


def test_nice_ambiguity_is_not_a_blocking_question():
    packet = {
        "statements": [
            {
                "raw_text": "Balanced location",
                "meaning": "Family proximity is a preference but no anchor was given.",
                "importance": "NICE",
                "knowledge_state": "AMBIGUOUS",
                "status": "ASKED",
                "mapped_parameters": ["family_location"],
                "clarification_question": "Where does family live?",
                "research_task": None,
            }
        ],
        "next_question": "Where does family live?",
        "research_requests": [],
        "decision_readiness": "NEEDS_CLARIFICATION",
    }
    validated = _validate_result(packet)
    assert validated["decision_readiness"] == "READY"
    assert validated["next_question"] is None
    assert validated["statements"][0]["status"] == "USED"
