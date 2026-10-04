"""Owner decision: a secured unit needs a confirmed safety need or explicit requirement."""
import pytest

from app.services.client_intent_runtime import build_client_intent
from app.services.living_strategy_runtime import build_living_strategy_context


def _must(state, query=""):
    strategy = build_living_strategy_context(state, query)
    return {row["key"] for row in build_client_intent(state, query, strategy, {})["must_haves"]}, strategy


@pytest.mark.parametrize("status", ["Mild memory issues", "Significant memory issues", "Occasionally forgetful", "No", "Not sure"])
def test_memory_severity_alone_never_requires_a_secured_unit(status):
    must, _ = _must({"memoryStatus": status})
    assert "SECURE_MEMORY_CARE_CONFIRMED" not in must and "SECURED_UNIT_AVAILABLE" not in must


def test_significant_memory_without_safety_answer_asks_instead_of_assuming():
    _, strategy = _must({"memoryStatus": "Significant memory issues"})
    asked = {q["question_key"] for q in strategy["guardian_clarification_candidates"]}
    assert "memory_safety_need" in asked
    assert strategy["signals"]["memory_care_needed"] is True


@pytest.mark.parametrize("answer", ["Yes", "No", "Not sure"])
def test_answered_safety_question_is_not_asked_again(answer):
    state = {"memoryStatus": "Significant memory issues", "humanIntelligenceV2": {"transitionRiskProfile": {"wanderingConcerns": answer}}}
    _, strategy = _must(state)
    assert "memory_safety_need" not in {q["question_key"] for q in strategy["guardian_clarification_candidates"]}


@pytest.mark.parametrize("path", [("transitionRiskProfile", "wanderingConcerns"), ("futureCareProfile", "secureMemoryNeighborhoodNeed")])
def test_explicit_safety_need_requires_confirmed_secured_memory_care(path):
    state = {"memoryStatus": "Significant memory issues", "humanIntelligenceV2": {path[0]: {path[1]: "Yes"}}}
    must, _ = _must(state)
    assert "SECURE_MEMORY_CARE_CONFIRMED" in must


def test_safety_question_is_asked_in_the_approved_words_even_without_semantic_wording():
    from app.services.human_intelligence_runtime_verified import build_human_intelligence_context

    context = build_human_intelligence_context(
        {"budget": 7000, "memoryStatus": "Significant memory issues", "assistanceLevel": "Help with bathing"}, "", structured_only=True)
    question = context["adaptive_questions"][0]
    assert question["question"] == "Does the resident wander, or need a secured unit for safety?"
    assert question["target_fact_key"] == "memory_safety_need"
