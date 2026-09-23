"""A client who answers the budget question without naming an amount must not be stuck.

Reproduces the production deadlock observed on the live site: the family answers the
guardian's `monthly_budget` question with "Not sure". The interview AI correctly returns
READY (the readiness guardian's stated rule is that an explicit adaptive answer, including
an acknowledged unknown, resolves the interview blocker without fabricating a value), but
the minimum-dimension guard still counted `monthly_affordability` as missing and raised
SEMANTIC_AI_READY_WITH_MISSING_MINIMUM_DIMENSIONS. The UI surfaced that as "We could not
verify our understanding of your answers. Please try again", and every retry reissued an
identical request, so the interview could never be completed.
"""
import unittest
from unittest.mock import patch

from app.services.semantic_intent_ai import (
    _minimum_dimension_status,
    interpret_client_intent_with_ai,
)


def _state(answer: str, *, budget=0):
    return {
        "budget": budget,
        "humanIntelligenceV2": {
            "scoringEngine": {
                "adaptiveSignals": [
                    {
                        "questionKey": "monthly_budget",
                        "answer": answer,
                        "impactExplanation": (
                            "Question: What monthly housing-and-care budget is comfortable? "
                            "| Target fact: monthly_budget"
                        ),
                    }
                ]
            }
        },
    }


def _ready_packet():
    return {
        "facts": ["Client context captured."],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": [{
            "raw_text": "Budget is not known.",
            "meaning": "The family answered the budget question with an acknowledged unknown.",
            "importance": "MUST",
            "knowledge_state": "UNKNOWN",
            "status": "USED",
            "mapped_parameters": ["monthly_affordability"],
            "clarification_question": None,
            "research_task": None,
        }],
        "next_question": None,
        "research_requests": [],
        "decision_readiness": "READY",
    }


class BudgetAcknowledgedUnknownTests(unittest.TestCase):
    def test_answered_budget_question_resolves_the_dimension_without_inventing_a_value(self):
        for answer in ("Not sure", "I don't know", "Above $12,000", "Prefer not to say"):
            with self.subTest(answer=answer):
                status = _minimum_dimension_status(
                    "My mother is 84 and lives in Las Vegas. She needs help with bathing and dressing.",
                    _state(answer),
                )
                self.assertTrue(
                    status["monthly_affordability"],
                    f"answering the budget question with {answer!r} must not leave the dimension unknown",
                )

    def test_unanswered_budget_question_still_counts_as_missing(self):
        status = _minimum_dimension_status(
            "My mother is 84 and lives in Las Vegas. She needs help with bathing and dressing.",
            {"budget": 0},
        )
        self.assertFalse(status["monthly_affordability"])

    def test_not_sure_answer_does_not_raise_and_does_not_fabricate_a_budget(self):
        state = _state("Not sure")
        with patch("app.services.semantic_intent_ai._default_transport", return_value=_ready_packet()):
            result = interpret_client_intent_with_ai(
                user_text="My mother is 84 and lives in Las Vegas. She needs help with bathing and dressing.",
                questionnaire_state=state,
            )
        self.assertEqual(result["decision_readiness"], "READY")
        # The acknowledged unknown must stay unknown; nothing may invent a ceiling.
        self.assertEqual(state["budget"], 0)

    def test_a_seven_thousand_budget_is_a_real_budget(self):
        # A literal 7000 was previously excluded, so a family whose budget is exactly
        # $7,000 was treated as having supplied no budget at all.
        status = _minimum_dimension_status("My mother lives in Las Vegas.", {"budget": 7000})
        self.assertTrue(status["monthly_affordability"])


if __name__ == "__main__":
    unittest.main()
