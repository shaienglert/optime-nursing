"""A clarification question must be answerable: after the answer is applied the way the
interview screen applies it (adaptive signal with a target fact + canonical patch) the
same fact is never asked again, whatever the answer was (including "Not sure")."""
import copy

import pytest

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context

BASE = {"budget": 7000, "memoryStatus": "Significant memory issues", "assistanceLevel": "Help with bathing"}


def _asked(state):
    context = build_human_intelligence_context(state, "", structured_only=True)
    blockers = {row["fact_key"] for row in context["readiness_guardian"]["client_owned_blockers"]}
    questions = {q.get("target_fact_key") for q in context["adaptive_questions"]}
    return context, blockers | questions


def _answer(state, fact, text, patch=None):
    out = copy.deepcopy(state)
    hi = out.setdefault("humanIntelligenceV2", {})
    hi.setdefault("scoringEngine", {}).setdefault("adaptiveSignals", []).append({
        "questionKey": f"q_{fact}", "answer": text,
        "impactExplanation": f"Question: x | Target fact: {fact} | explicit client answer",
    })
    for path, value in (patch or {}).items():
        node = out
        *parents, leaf = path.split(".")
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = value
    return out


@pytest.mark.parametrize("answer", ["Yes", "No", "Not sure"])
def test_memory_safety_question_is_asked_once_and_then_closed(answer):
    _, asked = _asked(BASE)
    assert "memory_safety_need" in asked
    state = _answer(BASE, "memory_safety_need", answer, {"humanIntelligenceV2.transitionRiskProfile.wanderingConcerns": answer})
    _, asked_again = _asked(state)
    assert "memory_safety_need" not in asked_again


def test_memory_safety_not_sure_without_a_stored_value_still_closes_the_question():
    state = _answer(BASE, "memory_safety_need", "Not sure")
    _, asked_again = _asked(state)
    assert "memory_safety_need" not in asked_again


def test_numeric_budget_answer_closes_the_budget_question():
    start = dict(BASE, budget="seven thousand")
    _, asked = _asked(start)
    assert "monthly_budget" in asked
    _, after = _asked(_answer(start, "monthly_budget", "7,000", {"budget": 7000}))
    assert "monthly_budget" not in after


def test_unparseable_reply_to_the_budget_question_is_not_asked_forever():
    start = dict(BASE, budget="seven thousand")
    _, after = _asked(_answer(start, "monthly_budget", "no idea", {"budget": 0}))
    assert "monthly_budget" not in after


LANG = {"humanIntelligenceV2": {"languageProfile": {"preferredSpokenLanguage": "Other", "languageNeedScope": "Requirement"}}}


def test_required_language_question_closes_with_a_named_language_or_not_sure():
    start = dict(BASE, **copy.deepcopy(LANG))
    _, asked = _asked(start)
    assert "required_language" in asked
    named = _answer(start, "required_language", "Tagalog", {"humanIntelligenceV2.languageProfile.preferredSpokenLanguage": "Tagalog"})
    assert "required_language" not in _asked(named)[1]
    assert "required_language" not in _asked(_answer(start, "required_language", "Not sure"))[1]
