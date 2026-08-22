from app.services.semantic_intent_ai import interpret_client_intent_with_ai


def test_ready_packet_with_blocking_asked_statement_normalizes_to_clarification():
    def transport(_payload):
        return {
            "facts": ["Resident uses a walker."],
            "preferences": [],
            "constraints": ["Walker mobility is material."],
            "concerns": [],
            "implications": [],
            "statements": [
                {
                    "raw_text": "I use a walker.",
                    "meaning": "Resident uses a walker.",
                    "importance": "MUST",
                    "knowledge_state": "AMBIGUOUS",
                    "status": "ASKED",
                    "mapped_parameters": ["mobility"],
                    "clarification_question": "How far can you comfortably walk with your walker?",
                    "research_task": None,
                }
            ],
            "next_question": "How far can you comfortably walk with your walker?",
            "research_requests": [],
            "decision_readiness": "READY",
        }

    result = interpret_client_intent_with_ai(
        user_text="I use a walker.",
        questionnaire_state={"budget": 8000, "locationCity": "Las Vegas"},
        transport=transport,
    )

    assert result["decision_readiness"] == "NEEDS_CLARIFICATION"
    assert result["next_question"] == "How far can you comfortably walk with your walker?"
    assert result["readiness_normalization"]["reason"] == "BLOCKING_AI_QUESTION_PRESENT"
    assert result["dropped_statement_count"] == 0
