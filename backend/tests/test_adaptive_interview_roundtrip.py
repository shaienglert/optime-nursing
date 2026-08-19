from __future__ import annotations

import unittest

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


class AdaptiveInterviewRoundTripTests(unittest.TestCase):
    def _state(self) -> dict:
        return {
            "humanIntelligenceV2": {
                "familyProfile": {
                    "widowStatus": "Yes",
                    "lossTiming": "Within 6 months",
                    "socialInteractionNeed": "",
                },
                "socialProfile": {
                    "newFriendsImportance": "",
                    "preferredSocialIntensity": "",
                },
                "familyCultureProfile": {"decisionRole": ""},
                "personalityProfile": {"communitySizePreference": ""},
                "transitionRiskProfile": {
                    "bereavementStatus": "Yes, within 1 year",
                    "lonelinessRisk": "",
                    "socialIsolationConcern": "",
                    "attitudeTowardMove": "",
                },
                "independenceProfile": {},
            }
        }

    def test_recent_bereavement_without_preferences_requires_high_value_clarifications(self) -> None:
        context = build_human_intelligence_context(self._state(), "recently widowed")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(
            [row["question_key"] for row in context["adaptive_questions"]],
            ["community_size_preference", "social_interaction_need_after_loss", "move_participation"],
        )
        self.assertTrue(all(row["information_gain"] == "HIGH" for row in context["adaptive_questions"]))
        self.assertTrue(all(row.get("answer_options") for row in context["adaptive_questions"]))

    def test_answers_close_round_trip_without_inference(self) -> None:
        state = self._state()
        state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "Large community"
        state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Neither"
        state["humanIntelligenceV2"]["transitionRiskProfile"]["attitudeTowardMove"] = "Cautious but open"
        context = build_human_intelligence_context(state, "recently widowed")
        self.assertEqual(context["decision_readiness"], "READY")
        self.assertEqual(context["adaptive_questions"], [])
        self.assertEqual(context["signals"]["community_size_preference"]["value"], "LARGE")
        self.assertEqual(context["signals"]["social_transition_priority"]["value"], "NEUTRAL")
        self.assertEqual(context["signals"]["decision_participation"]["value"], "CAUTIOUS")
        self.assertEqual(context["transition_support"]["level"], "ENHANCED_SUPPORT_RECOMMENDED")

    def test_not_sure_is_acknowledged_and_does_not_loop_forever(self) -> None:
        state = self._state()
        state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "No preference"
        state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Neither"
        state["humanIntelligenceV2"]["transitionRiskProfile"]["attitudeTowardMove"] = "Not sure"
        context = build_human_intelligence_context(state, "recently widowed")
        self.assertEqual(context["decision_readiness"], "READY")
        self.assertEqual(context["signals"]["decision_participation"]["value"], "ACKNOWLEDGED_UNKNOWN")
        self.assertEqual(context["transition_support"]["level"], "ENHANCED_SUPPORT_RECOMMENDED")


if __name__ == "__main__":
    unittest.main()
