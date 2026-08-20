from __future__ import annotations

import unittest

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


class AdaptiveInterviewRoundTripTests(unittest.TestCase):
    def _state(self) -> dict:
        return {"humanIntelligenceV2": {"familyProfile": {"widowStatus": "Yes", "lossTiming": "Within 6 months", "socialInteractionNeed": ""}, "socialProfile": {"newFriendsImportance": "", "preferredSocialIntensity": ""}, "familyCultureProfile": {"decisionRole": ""}, "personalityProfile": {"communitySizePreference": ""}, "transitionRiskProfile": {"bereavementStatus": "Yes, within 1 year", "lonelinessRisk": "", "socialIsolationConcern": "", "attitudeTowardMove": ""}, "independenceProfile": {}}}

    def _assisted_state(self) -> dict:
        return {"relationship": "Dad", "ageGroup": "80-84", "assistanceLevel": "Needs assistance with bathing and dressing", "memoryStatus": "No", "humanIntelligenceV2": {"familyProfile": {"socialInteractionNeed": ""}, "socialProfile": {}, "familyCultureProfile": {}, "personalityProfile": {"communitySizePreference": ""}, "transitionRiskProfile": {}, "independenceProfile": {}}}

    def test_recent_bereavement_without_preferences_requires_high_value_clarifications(self) -> None:
        context = build_human_intelligence_context(self._state(), "recently widowed")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual([row["question_key"] for row in context["adaptive_questions"]], ["community_size_preference", "social_interaction_need_after_loss", "move_participation"])
        self.assertTrue(all(row["information_gain"] == "HIGH" for row in context["adaptive_questions"]))
        self.assertTrue(all(row.get("answer_options") for row in context["adaptive_questions"]))

    def test_material_assisted_living_unknowns_trigger_questions_without_bereavement(self) -> None:
        context = build_human_intelligence_context(self._assisted_state(), "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual([row["question_key"] for row in context["adaptive_questions"]], ["community_size_preference", "social_interaction_preference"])
        self.assertTrue(context["material_unknown_policy"]["unknown_is_not_default"])

    def test_material_assisted_living_answers_close_questions(self) -> None:
        state = self._assisted_state(); state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "Large community"; state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Very important"
        context = build_human_intelligence_context(state, "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.")
        self.assertEqual(context["decision_readiness"], "READY"); self.assertEqual(context["adaptive_questions"], []); self.assertEqual(context["signals"]["community_size_preference"]["value"], "LARGE"); self.assertEqual(context["signals"]["social_transition_priority"]["value"], "HIGH")

    def test_material_not_sure_is_acknowledged_without_loop(self) -> None:
        state = self._assisted_state(); state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "No preference"; state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Not sure"
        context = build_human_intelligence_context(state, "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.")
        self.assertEqual(context["decision_readiness"], "READY"); self.assertEqual(context["adaptive_questions"], [])

    def test_answers_close_round_trip_without_inference(self) -> None:
        state = self._state(); state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "Large community"; state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Neither"; state["humanIntelligenceV2"]["transitionRiskProfile"]["attitudeTowardMove"] = "Cautious but open"
        context = build_human_intelligence_context(state, "recently widowed")
        self.assertEqual(context["decision_readiness"], "READY"); self.assertEqual(context["adaptive_questions"], []); self.assertEqual(context["signals"]["community_size_preference"]["value"], "LARGE"); self.assertEqual(context["signals"]["social_transition_priority"]["value"], "NEUTRAL"); self.assertEqual(context["signals"]["decision_participation"]["value"], "CAUTIOUS"); self.assertEqual(context["transition_support"]["level"], "ENHANCED_SUPPORT_RECOMMENDED")

    def test_not_sure_is_acknowledged_and_does_not_loop_forever(self) -> None:
        state = self._state(); state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "No preference"; state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Neither"; state["humanIntelligenceV2"]["transitionRiskProfile"]["attitudeTowardMove"] = "Not sure"
        context = build_human_intelligence_context(state, "recently widowed")
        self.assertEqual(context["decision_readiness"], "READY"); self.assertEqual(context["signals"]["decision_participation"]["value"], "ACKNOWLEDGED_UNKNOWN"); self.assertEqual(context["transition_support"]["level"], "ENHANCED_SUPPORT_RECOMMENDED")

    def test_walker_100m_wheelchair_refusal_asks_compact_layout_first(self) -> None:
        state = {"relationship": "Myself", "ageGroup": "80-84", "mobilityStatus": "Uses walker", "humanIntelligenceV2": {"independenceProfile": {}}}
        context = build_human_intelligence_context(state, "I am 80, use a walker, can walk only 100 meters, and refuse wheelchair use. Otherwise independent. I want senior living in Las Vegas.")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(context["adaptive_questions"][0]["question_key"], "compact_central_layout_preference")
        self.assertIn("short walking distances", context["adaptive_questions"][0]["question"].lower())

    def test_compact_layout_answer_closes_mobility_question(self) -> None:
        state = {"relationship": "Myself", "ageGroup": "80-84", "mobilityStatus": "Uses walker", "humanIntelligenceV2": {"independenceProfile": {"compactLayoutPreference": "Yes"}}}
        context = build_human_intelligence_context(state, "I am 80, use a walker, can walk only 100 meters, and refuse wheelchair use. Otherwise independent. I want senior living in Las Vegas.")
        self.assertFalse(any(q["question_key"] == "compact_central_layout_preference" for q in context["adaptive_questions"]))
        self.assertEqual(context["signals"]["compact_central_layout_preference"]["value"], "REQUIRED")


if __name__ == "__main__": unittest.main()
