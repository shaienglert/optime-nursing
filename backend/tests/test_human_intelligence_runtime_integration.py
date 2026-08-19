from __future__ import annotations

import unittest

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
        },
    }


class HumanIntelligenceRuntimeIntegrationTests(unittest.TestCase):
    def test_recent_widow_case_requires_person_fit_clarification(self):
        result = run_patient_decision_engine(_questionnaire(), BASE_QUERY, limit=5)
        intelligence = result["decision_intelligence"]
        human = intelligence["human_intelligence"]
        self.assertEqual("YES", human["signals"]["recent_bereavement"]["value"])
        self.assertEqual("NEEDS_CLARIFICATION", human["decision_readiness"])
        self.assertEqual("WAITING_FOR_EXPLICIT_PREFERENCE_OR_EVIDENCE", intelligence["person_fit_rank_effect"])
        self.assertEqual(
            [q["question_key"] for q in human["adaptive_questions"]],
            ["community_size_preference", "social_interaction_need_after_loss", "move_participation"],
        )
        self.assertEqual(5, result["result_count"])
        self.assertTrue(all("human_person_fit" in row for row in result["results"]))
        self.assertTrue(all(row["explanation"].get("decision_readiness") == "NEEDS_CLARIFICATION" for row in result["results"]))

    def test_explicit_large_community_preference_affects_rank(self):
        result = run_patient_decision_engine(
            _questionnaire(
                community_size="Larger senior community with more people and activities",
                social_need="Neither",
                move_attitude="Cautious but open",
            ),
            BASE_QUERY,
            limit=5,
        )
        intelligence = result["decision_intelligence"]
        human = intelligence["human_intelligence"]
        self.assertEqual("ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE", intelligence["person_fit_rank_effect"])
        self.assertEqual("READY", human["decision_readiness"])
        self.assertEqual([], human["adaptive_questions"])
        top = result["results"][0]
        size = top["human_person_fit"]["community_size"]
        self.assertEqual("LARGE_COMMUNITY", size["community_size_band"])
        self.assertEqual(100.0, size["fit_score"])
        self.assertEqual("REGULATORY_VERIFIED", size["evidence_class"])
        self.assertTrue(size["not_a_quality_factor"])
        self.assertEqual([1, 2, 3, 4, 5], [row["rank_position"] for row in result["results"]])

    def test_explicit_small_home_preference_affects_rank(self):
        result = run_patient_decision_engine(
            _questionnaire(
                community_size="Small intimate home-like setting",
                social_need="Neither",
                move_attitude="Cautious but open",
            ),
            BASE_QUERY,
            limit=5,
        )
        intelligence = result["decision_intelligence"]
        self.assertEqual("ACTIVE_EXPLICIT_PREFERENCE_CONGRUENCE", intelligence["person_fit_rank_effect"])
        top = result["results"][0]
        size = top["human_person_fit"]["community_size"]
        self.assertIn(size["community_size_band"], {"MICRO_HOME", "SMALL_COMMUNITY"})
        self.assertEqual(100.0, size["fit_score"])
        self.assertEqual("REGULATORY_VERIFIED", size["evidence_class"])
        self.assertTrue(size["not_a_quality_factor"])


if __name__ == "__main__":
    unittest.main()
