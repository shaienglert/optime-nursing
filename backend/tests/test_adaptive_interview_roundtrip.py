from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


class AdaptiveInterviewRoundTripTests(unittest.TestCase):
    def _state(self) -> dict:
        return {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "humanIntelligenceV2": {
                "familyProfile": {"socialInteractionNeed": ""},
                "socialProfile": {},
                "familyCultureProfile": {},
                "personalityProfile": {"communitySizePreference": ""},
                "transitionRiskProfile": {},
                "independenceProfile": {},
                "scoringEngine": {"adaptiveSignals": []},
            },
        }

    def _run(self, state: dict, ai_result: dict, query: str = "") -> dict:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False):
            with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result):
                return build_human_intelligence_context(state, query)

    def test_ai_chooses_exactly_one_next_question(self) -> None:
        question = "Which daily social environment would feel most comfortable?"
        context = self._run(self._state(), {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [],
        })
        self.assertEqual("SEMANTIC_AI", context["interview_policy"]["owner"])
        self.assertTrue(context["interview_policy"]["hard_coded_question_generation_forbidden"])
        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])
        self.assertEqual(1, len(context["adaptive_questions"]))
        row = context["adaptive_questions"][0]
        self.assertTrue(row["question_key"].startswith("semantic_ai_high_information_question:"))
        self.assertEqual(question, row["question"])
        self.assertTrue(row.get("target_fact_key"))
        self.assertNotIn(row["question_key"], {"community_size_preference", "social_interaction_preference", "move_participation"})

    def test_guardian_rejects_ai_ready_when_material_client_fact_is_unresolved(self) -> None:
        context = self._run(self._state(), {
            "decision_readiness": "READY",
            "next_question": None,
            "statements": [],
        }, "My father needs help bathing and dressing and has no dementia.")
        self.assertEqual("NEEDS_RESEARCH", context["decision_readiness"])
        self.assertEqual([], context["adaptive_questions"])
        self.assertTrue(context["readiness_guardian"]["veto_applied"])
        self.assertEqual("AI_DID_NOT_RESOLVE_GUARDIAN_VETO", context["readiness_guardian"]["veto_resolution"])
        self.assertTrue(context["readiness_guardian"]["client_owned_blockers"])
        self.assertEqual("SEMANTIC_AI", context["interview_policy"]["owner"])

    def test_explicit_semantic_fact_answer_resolves_guardian_blocker_without_scripted_question(self) -> None:
        state = self._state()
        state["budget"] = 6500
        state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "No preference"
        state["humanIntelligenceV2"]["scoringEngine"]["adaptiveSignals"] = [
            {
                "questionKey": "semantic-ai-answer-1",
                "answer": "No preference",
                "signalType": "decision-interview",
                "impactExplanation": "Question: What type of community would suit him? | Target fact: community_size_preference | explicit answer",
            }
        ]
        context = self._run(state, {
            "decision_readiness": "READY",
            "next_question": None,
            "statements": [],
        }, "My father lives in Las Vegas, needs help bathing and dressing, has no dementia, and has a $6,500 monthly budget.")
        self.assertIn("community_size_preference", context["readiness_guardian"]["acknowledged_fact_keys"])

    def test_needs_research_blocks_without_scripted_question(self) -> None:
        context = self._run(self._state(), {
            "decision_readiness": "NEEDS_RESEARCH",
            "next_question": None,
            "statements": [],
        })
        self.assertEqual("NEEDS_RESEARCH", context["decision_readiness"])
        self.assertEqual([], context["adaptive_questions"])

    def test_required_ai_unavailable_never_falls_back_to_fixed_questions(self) -> None:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "0", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False):
            context = build_human_intelligence_context(self._state(), "recently widowed")
        self.assertEqual("NEEDS_RESEARCH", context["decision_readiness"])
        self.assertEqual([], context["adaptive_questions"])
        self.assertEqual("REQUIRED_BUT_DISABLED", context["semantic_ai"]["status"])

    def test_answered_semantic_question_is_not_reissued(self) -> None:
        question = "What matters most about the social environment?"
        first = self._run(self._state(), {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [],
        })
        key = first["adaptive_questions"][0]["question_key"]
        target = first["adaptive_questions"][0].get("target_fact_key")
        state = self._state()
        state["humanIntelligenceV2"]["scoringEngine"]["adaptiveSignals"] = [
            {"questionKey": key, "answer": "Quiet but friendly", "signalType": "decision-interview", "impactExplanation": f"Target fact: {target}"}
        ]
        second = self._run(state, {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [],
        })
        self.assertEqual([], second["adaptive_questions"])


if __name__ == "__main__":
    unittest.main()
