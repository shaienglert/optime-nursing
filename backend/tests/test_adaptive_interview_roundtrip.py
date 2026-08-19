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
                "personalityProfile": {"communitySizePreference": ""},
                "transitionRiskProfile": {
                    "bereavementStatus": "Yes, within 1 year",
                    "lonelinessRisk": "",
                    "socialIsolationConcern": "",
                },
                "independenceProfile": {},
            }
        }

    def test_recent_bereavement_without_preferences_requires_clarification(self) -> None:
        context = build_human_intelligence_context(self._state(), "recently widowed")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(
            [row["question_key"] for row in context["adaptive_questions"]],
            ["community_size_preference", "social_interaction_need_after_loss"],
        )

    def test_explicit_large_community_and_neutral_social_answer_is_ready(self) -> None:
        state = self._state()
        state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "Large community"
        state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Neither"
        context = build_human_intelligence_context(state, "recently widowed")
        self.assertEqual(context["decision_readiness"], "READY")
        self.assertEqual(context["adaptive_questions"], [])
        self.assertEqual(context["signals"]["community_size_preference"]["value"], "LARGE")
        self.assertEqual(context["signals"]["social_transition_priority"]["value"], "NEUTRAL")


if __name__ == "__main__":
    unittest.main()
