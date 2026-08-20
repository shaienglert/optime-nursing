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
        self.assertTrue(all(row["information_gain"] == "HIGH" for row in context["adaptive_questions"]))
        self.assertTrue(all(row.get("answer_options") for row in context["adaptive_questions"]))

    def test_material_assisted_living_unknowns_trigger_questions_without_bereavement(self) -> None:
        context = build_human_intelligence_context(self._assisted_state(), "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        keys = [row["question_key"] for row in context["adaptive_questions"]]
        self.assertIn("community_size_preference", keys)
        self.assertIn("social_interaction_preference", keys)
        self.assertTrue(context["material_unknown_policy"]["unknown_is_not_default"])

    def test_material_assisted_living_answers_close_known_questions(self) -> None:
        state = self._assisted_state(); state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "Large community"; state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Very important"
        context = build_human_intelligence_context(state, "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.")
        self.assertFalse(any(q["question_key"] in {"community_size_preference", "social_interaction_preference"} for q in context["adaptive_questions"]))
        self.assertEqual(context["signals"]["community_size_preference"]["value"], "LARGE")
        self.assertEqual(context["signals"]["social_transition_priority"]["value"], "HIGH")

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

    def test_every_meaningful_user_clause_is_accounted_and_nothing_is_dropped(self) -> None:
        query = "We are a married independent couple, food is very important, we love activities, beautiful gardens, outings, and a pottery studio with evening glazing sessions."
        context = build_human_intelligence_context({}, query)
        accounting = context["user_statement_accounting"]
        self.assertEqual(accounting["coverage_percent"], 100.0)
        self.assertEqual(accounting["dropped_count"], 0)
        self.assertTrue(all(row["status"] in {"USED", "ASKED", "RESEARCH_REQUIRED", "NOT_DECISION_RELEVANT"} for row in accounting["statements"]))
        unresolved = accounting["unresolved_parameters"]
        self.assertTrue(any("pottery studio" in row["statement"].lower() for row in unresolved))
        self.assertTrue(any(q["question_key"] == "unresolved_client_parameter" for q in context["adaptive_questions"]))

    def test_unknown_parameter_blocks_readiness_instead_of_being_ignored(self) -> None:
        context = build_human_intelligence_context({}, "I need a moonlight ceramics room with kiln access")
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(context["user_statement_accounting"]["dropped_count"], 0)
        self.assertEqual(context["user_statement_accounting"]["unresolved_parameters"][0]["status"], "ASKED")
        question = next(q for q in context["adaptive_questions"] if q["question_key"] == "unresolved_client_parameter")
        self.assertIn("do not want to ignore", question["question"])

    def test_known_and_unknown_hebrew_preferences_are_both_accounted(self) -> None:
        context = build_human_intelligence_context({}, "חשוב לנו אוכל טוב, גינון מטופח, וסטודיו לקרמיקה עם תנור בערב")
        accounting = context["user_statement_accounting"]
        self.assertEqual(accounting["coverage_percent"], 100.0)
        self.assertEqual(accounting["dropped_count"], 0)
        self.assertTrue(any("סטודיו" in row["statement"] for row in accounting["unresolved_parameters"]))


if __name__ == "__main__":
    unittest.main()
