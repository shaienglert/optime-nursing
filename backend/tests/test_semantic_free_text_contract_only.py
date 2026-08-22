from app.services.semantic_intent_ai import SEMANTIC_AI_SYSTEM_RULES, _build_prompt, _question_reasks_answered_dimension

def test_explicit_free_text_is_ai_contract_not_runtime_topic_heuristic():
    packet = {"next_question": "Does she have any mobility limitations?"}
    assert _question_reasks_answered_dimension(packet, {}, "She has no mobility limitation.") is False
    assert any("explicit free-text client statements" in rule.lower() for rule in SEMANTIC_AI_SYSTEM_RULES)
    prompt = _build_prompt("She has no mobility limitation.", {}, {"advisor":"x","available_agent_count":0,"agent_count":0})
    assert "free_text_answer_rule" in prompt["response_constraints"]
