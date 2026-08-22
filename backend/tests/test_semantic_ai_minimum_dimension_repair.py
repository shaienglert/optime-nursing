import unittest
from unittest.mock import patch

from app.services.semantic_intent_ai import interpret_client_intent_with_ai


def packet(*, readiness, statements, next_question=None):
    return {
        "facts": ["Client context captured."],
        "preferences": [],
        "constraints": [],
        "concerns": [],
        "implications": [],
        "statements": statements,
        "next_question": next_question,
        "research_requests": [],
        "decision_readiness": readiness,
    }


class SemanticAiMinimumDimensionRepairTests(unittest.TestCase):
    def test_live_ready_without_location_is_repaired_by_ai_question(self):
        first = packet(
            readiness="READY",
            statements=[{
                "raw_text": "Budget is $8,000.",
                "meaning": "Monthly budget is $8,000.",
                "importance": "MUST",
                "knowledge_state": "KNOWN",
                "status": "USED",
                "mapped_parameters": ["monthly_affordability"],
                "clarification_question": None,
                "research_task": None,
            }],
        )
        repaired = packet(
            readiness="NEEDS_CLARIFICATION",
            statements=[{
                "raw_text": "Search market is not yet known.",
                "meaning": "Client must supply the desired search market.",
                "importance": "MUST",
                "knowledge_state": "UNKNOWN",
                "status": "ASKED",
                "mapped_parameters": ["market_location"],
                "clarification_question": "What city or area should I search in for your mother?",
                "research_task": None,
            }],
            next_question="What city or area should I search in for your mother?",
        )
        with patch("app.services.semantic_intent_ai._default_transport", side_effect=[first, repaired]) as mocked:
            result = interpret_client_intent_with_ai(
                user_text="My mother is 82 and fully independent.",
                questionnaire_state={"budget": 8000},
            )
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(result["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(result["next_question"], "What city or area should I search in for your mother?")
        self.assertEqual(result["minimum_dimension_repair"]["missing_dimensions"], ["market_location"])

    def test_free_text_with_location_and_budget_needs_no_minimum_repair(self):
        first = packet(
            readiness="READY",
            statements=[{
                "raw_text": "Las Vegas with a monthly budget of $8,000.",
                "meaning": "Market and affordability are known.",
                "importance": "MUST",
                "knowledge_state": "KNOWN",
                "status": "USED",
                "mapped_parameters": ["market_location", "monthly_affordability"],
                "clarification_question": None,
                "research_task": None,
            }],
        )
        with patch("app.services.semantic_intent_ai._default_transport", return_value=first) as mocked:
            result = interpret_client_intent_with_ai(
                user_text="My mother needs senior living in Las Vegas. Her monthly budget is $8,000.",
                questionnaire_state={},
            )
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(result["decision_readiness"], "READY")
        self.assertNotIn("minimum_dimension_repair", result)


if __name__ == "__main__":
    unittest.main()
