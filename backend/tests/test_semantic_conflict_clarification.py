import unittest
from app.services.semantic_intent_ai import _question_reasks_answered_dimension


class ConflictClarificationTest(unittest.TestCase):
    def test_explicit_clarification_still_triggers_repeat_repair(self):
        packet = {
            "next_question": "Which monthly budget should I use?",
            "statements": [{"status": "ASKED", "knowledge_state": "AMBIGUOUS", "importance": "MUST"}],
        }
        state = {"humanIntelligenceV2": {"scoringEngine": {"adaptiveSignals": [{
            "questionKey": "semantic-conflict-monthly_affordability",
            "answer": "$5,000 per month. This replaces both amounts in the original story.",
            "impactExplanation": "Question: Which monthly budget should I use? | explicit client answer",
        }]}}}
        self.assertTrue(_question_reasks_answered_dimension(packet, state, "Budget $50,000 or $500."))

    def test_conflicting_budget_is_not_an_answered_dimension(self):
        packet = {
            "next_question": "Is your monthly budget $50,000 or $500?",
            "statements": [{"status": "ASKED", "knowledge_state": "AMBIGUOUS", "importance": "MUST"}],
        }
        self.assertFalse(_question_reasks_answered_dimension(packet, {}, "My budget is $50,000 or $500."))

    def test_conflicting_memory_is_not_an_answered_dimension(self):
        packet = {
            "next_question": "Does she have dementia or no memory concerns?",
            "statements": [{"status": "ASKED", "knowledge_state": "AMBIGUOUS", "importance": "MUST"}],
        }
        self.assertFalse(_question_reasks_answered_dimension(packet, {}, "She has no dementia. She has severe dementia."))

    def test_unambiguous_answer_still_prevents_redundant_question(self):
        self.assertTrue(_question_reasks_answered_dimension(
            {"next_question": "What is your monthly budget?", "statements": []}, {}, "My budget is $5000."
        ))
