from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.patient_decision_engine import run_patient_decision_engine


BASE_QUERY = (
    "My father is 84, recently widowed, and lives in Las Vegas. "
    "He has difficulty with bathing, dressing, meals and medication. "
    "He is mentally alert, has no dementia, is still mobile, and needs daily help."
)


def _questionnaire(*, community_size: str = "", social_need: str = "", move_attitude: str = "") -> dict:
    return {
        "relationship": "Dad",
        "ageGroup": "80-84",
        "assistanceLevel": "Needs assistance with bathing and dressing",
        "memoryStatus": "No",
        "budget": 6500,
        "distanceFromFamily": "Balanced location",
        "humanIntelligenceV2": {
            "personalityProfile": {"communitySizePreference": community_size},
            "familyProfile": {
                "widowStatus": "Recently widowed",
                "lossTiming": "Recent",
                "socialInteractionNeed": social_need,
            },
            "transitionRiskProfile": {
                "bereavementStatus": "Recent bereavement",
                "lonelinessRisk": "",
                "socialIsolationConcern": "",
                "attitudeTowardMove": move_attitude,
            },
            "socialProfile": {"newFriendsImportance": "", "preferredSocialIntensity": ""},
            "independenceProfile": {"abilityToLeaveIndependently": "Very important"},
            "scoringEngine": {"adaptiveSignals": []},
        },
    }


class HumanIntelligenceRuntimeIntegrationTests(unittest.TestCase):
    def _run(self, questionnaire: dict, ai_result: dict, limit: int = 5) -> dict:
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False):
            with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result):
                return run_patient_decision_engine(questionnaire, BASE_QUERY, limit=limit)

    def test_clarification_blocks_all_facility_ranking(self):
        question = "What kind of community environment would feel most comfortable for him?"
        result = self._run(_questionnaire(), {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [],
        })
        intelligence = result["decision_intelligence"]
        human = intelligence["human_intelligence"]
        self.assertEqual("NEEDS_CLARIFICATION", human["decision_readiness"])
        self.assertEqual("SEMANTIC_AI", intelligence["interview_owner"])
        self.assertFalse(intelligence["recommendation_execution_allowed"])
        self.assertEqual("BLOCKED_PENDING_AI_INTERVIEW", intelligence["decision_finality"])
        self.assertEqual([], result["results"])
        self.assertEqual(0, result["result_count"])
        self.assertEqual(0, result["total_candidates_scored"])
        self.assertEqual(1, len(human["adaptive_questions"]))
        self.assertTrue(human["adaptive_questions"][0]["question_key"].startswith("semantic_ai_high_information_question:"))

    def test_explicit_large_community_preference_affects_rank_after_ai_ready(self):
        result = self._run(
            _questionnaire(
                community_size="Larger senior community with more people and activities",
                social_need="Neither",
                move_attitude="Cautious but open",
            ),
            {"decision_readiness": "READY", "next_question": None, "statements": []},
        )
        intelligence = result["decision_intelligence"]
        human = intelligence["human_intelligence"]
        self.assertEqual("READY", human["decision_readiness"])
        self.assertTrue(intelligence["recommendation_execution_allowed"])
        self.assertEqual("ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE", intelligence["person_fit_rank_effect"])
        self.assertEqual([], human["adaptive_questions"])
        top = result["results"][0]
        size = top["human_person_fit"]["community_size"]
        self.assertEqual("LARGE_COMMUNITY", size["community_size_band"])
        self.assertEqual(100.0, size["fit_score"])
        self.assertEqual("REGULATORY_VERIFIED", size["evidence_class"])
        self.assertTrue(size["not_a_quality_factor"])

    def test_explicit_small_home_preference_affects_rank_after_ai_ready(self):
        result = self._run(
            _questionnaire(
                community_size="Small intimate home-like setting",
                social_need="Neither",
                move_attitude="Cautious but open",
            ),
            {"decision_readiness": "READY", "next_question": None, "statements": []},
        )
        intelligence = result["decision_intelligence"]
        self.assertTrue(intelligence["recommendation_execution_allowed"])
        self.assertEqual("ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE", intelligence["person_fit_rank_effect"])
        top = result["results"][0]
        size = top["human_person_fit"]["community_size"]
        self.assertIn(size["community_size_band"], {"MICRO_HOME", "SMALL_COMMUNITY"})
        self.assertEqual(100.0, size["fit_score"])
        self.assertEqual("REGULATORY_VERIFIED", size["evidence_class"])
        self.assertTrue(size["not_a_quality_factor"])


if __name__ == "__main__":
    unittest.main()
