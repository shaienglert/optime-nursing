from app.services.semantic_intent_ai import _validate_result


def test_nice_unknown_must_not_block_ready():
    packet = {
        "statements": [
            {
                "raw_text": "Balanced location",
                "meaning": "Family proximity is a preference but no anchor was given.",
                "importance": "NICE",
                "knowledge_state": "AMBIGUOUS",
                "status": "USED",
                "mapped_parameters": ["family_location"],
                "clarification_question": None,
                "research_task": None,
            }
        ],
        "next_question": None,
        "research_requests": [],
        "decision_readiness": "READY",
    }
    validated = _validate_result(packet)
    assert validated["decision_readiness"] == "READY"
