from __future__ import annotations

import os
import unittest
from unittest.mock import patch

if __package__:
    from .priced_candidate_fixture import priced_payloads
else:
    from priced_candidate_fixture import priced_payloads

from app.services.patient_decision_engine import run_patient_decision_engine


BASE_QUERY = (
    "My father is 84, recently widowed, and lives in Las Vegas. "
    "He has difficulty with bathing, dressing and meals. "
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
        # Every fixture here states a budget (a required minimum client dimension), which
        # is now also a facility-owned MUST (see semantic_facility_requirements.py's
        # SEMANTIC_BUDGET_VERIFICATION). No facility in the real, unmocked Las Vegas data
        # these tests run against has verified pricing evidence, so without this mock every
        # candidate would gate to PENDING_VERIFICATION on budget alone -- unrelated to what
        # these tests actually verify (preference/ranking behavior).
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False):
            with patch("app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result):
                with patch("app.services.governed_evidence_runtime.agent_and_provider_payloads", side_effect=priced_payloads([{"published_rates_verified": True}])):
                    return run_patient_decision_engine(questionnaire, BASE_QUERY, limit=limit)

    def test_ai_preference_question_cannot_block_facility_ranking(self):
        question = "What kind of community environment would feel most comfortable for him?"
        result = self._run(_questionnaire(), {
            "decision_readiness": "NEEDS_CLARIFICATION",
            "next_question": question,
            "statements": [{
                "raw_text": "Community environment preference is unknown.",
                "meaning": "Community size is a preference.",
                "importance": "NICE",
                "knowledge_state": "UNKNOWN",
                "status": "ASKED",
                "gap_key": "community_size_preference",
                "mapped_parameters": ["community_size_preference"],
                "clarification_question": question,
                "research_task": None,
            }],
        })
        intelligence = result["decision_intelligence"]
        human = intelligence["human_intelligence"]
        self.assertEqual("READY", human["decision_readiness"])
        self.assertEqual("SEMANTIC_AI", intelligence["interview_owner"])
        self.assertTrue(intelligence["recommendation_execution_allowed"])
        self.assertNotEqual("PENDING_CLIENT_INPUT_REQUIRED", intelligence["decision_finality"])
        self.assertGreater(result["result_count"], 0)
        self.assertEqual([], human["adaptive_questions"])
        self.assertTrue(any(
            row["gap_key"] == "community_size_preference" and row["classification"] == "PREFERENCE"
            for row in human["canonical_gap_policy"]["assessments"]
        ))

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
        # The ranking model is unavailable in this environment, so the hard criteria carry
        # the result: the eligible set is shown, explicitly unordered, with a degradation
        # notice. It used to be hidden entirely, which told the family nothing.
        self.assertTrue(intelligence["recommendation_execution_allowed"])
        self.assertTrue(intelligence["canonical_decision_state"]["is_degraded_result"])
        self.assertEqual("ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE", intelligence["person_fit_rank_effect"])
        self.assertEqual([], human["adaptive_questions"])
        self.assertFalse(result["degraded_result_notice"]["results_are_ordered"])

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
        # The ranking model is unavailable in this environment, so the hard criteria carry
        # the result: the eligible set is shown, explicitly unordered, with a degradation
        # notice. It used to be hidden entirely, which told the family nothing.
        self.assertTrue(intelligence["recommendation_execution_allowed"])
        self.assertTrue(intelligence["canonical_decision_state"]["is_degraded_result"])
        self.assertEqual("ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE", intelligence["person_fit_rank_effect"])
        self.assertFalse(result["degraded_result_notice"]["results_are_ordered"])


if __name__ == "__main__":
    unittest.main()
