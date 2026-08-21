from __future__ import annotations

import json
import unittest

from app.services.human_intelligence_runtime_verified import build_human_intelligence_context
from app.services.patient_decision_engine import run_patient_decision_engine


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

    def _assisted_state(self) -> dict:
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
            },
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

    def test_material_assisted_living_unknowns_trigger_questions_without_bereavement(self) -> None:
        context = build_human_intelligence_context(
            self._assisted_state(),
            "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.",
        )
        self.assertEqual(context["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(
            [row["question_key"] for row in context["adaptive_questions"]],
            ["community_size_preference", "social_interaction_preference"],
        )
        self.assertTrue(context["material_unknown_policy"]["unknown_is_not_default"])

    def test_material_assisted_living_answers_close_questions(self) -> None:
        state = self._assisted_state()
        state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "Large community"
        state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Very important"
        context = build_human_intelligence_context(
            state,
            "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.",
        )
        self.assertEqual(context["decision_readiness"], "READY")
        self.assertEqual(context["adaptive_questions"], [])
        self.assertEqual(context["signals"]["community_size_preference"]["value"], "LARGE")
        self.assertEqual(context["signals"]["social_transition_priority"]["value"], "HIGH")

    def test_material_not_sure_is_acknowledged_without_loop(self) -> None:
        state = self._assisted_state()
        state["humanIntelligenceV2"]["personalityProfile"]["communitySizePreference"] = "No preference"
        state["humanIntelligenceV2"]["familyProfile"]["socialInteractionNeed"] = "Not sure"
        context = build_human_intelligence_context(
            state,
            "My father is 84, mentally alert and mobile, has no dementia, and needs help with bathing, dressing, meals and medication.",
        )
        self.assertEqual(context["decision_readiness"], "READY")
        self.assertEqual(context["adaptive_questions"], [])

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

    def test_benchmark_independent_couple_food_gardens_activities_trips(self) -> None:
        state = {
            "relationship": "Myself",
            "memoryStatus": "No",
            "assistanceLevel": "Independent",
            "humanIntelligenceV2": {
                "familyProfile": {"socialInteractionNeed": "Very important"},
                "personalityProfile": {"communitySizePreference": ""},
                "transitionRiskProfile": {},
            },
        }
        query = (
            "Married couple, both fully independent today, want to move to senior living in Las Vegas because they expect they may need help someday. "
            "They love activities and outings. Excellent food is very important to them. They value beautifully maintained landscaping and gardens and trips/excursions. They want to live together."
        )
        result = run_patient_decision_engine(state, query, limit=5)
        human = result["decision_intelligence"]["human_intelligence"]
        payload = {
            "case": "independent_couple",
            "decision_readiness": human["decision_readiness"],
            "questions": [{"key": q.get("question_key"), "question": q.get("question")} for q in human.get("adaptive_questions", [])],
            "must": [m.get("key") for m in result["decision_intelligence"]["client_intent"].get("must_haves", [])],
            "nice": [n.get("key") for n in result["decision_intelligence"]["client_intent"].get("nice_to_haves", [])],
            "top5": [r.get("facility_name") for r in result.get("results", [])],
            "finality": result["decision_intelligence"].get("decision_finality"),
        }
        print("BENCHMARK_CASE_1=" + json.dumps(payload, ensure_ascii=False))
        self.assertGreater(result.get("result_count", 0), 0)

    def test_benchmark_walker_100m_refuses_wheelchair_requires_compact_layout_question(self) -> None:
        state = {
            "relationship": "Myself",
            "ageGroup": "80+",
            "memoryStatus": "No",
            "assistanceLevel": "Independent except mobility",
            "humanIntelligenceV2": {"familyProfile": {}, "personalityProfile": {}, "transitionRiskProfile": {}},
        }
        query = (
            "I am an 80-year-old man in Las Vegas, cognitively intact and otherwise independent. I walk only with a walker, cannot comfortably walk more than about 100 meters, and strongly do not want to be seen using a wheelchair. I am looking for senior living."
        )
        result = run_patient_decision_engine(state, query, limit=5)
        human = result["decision_intelligence"]["human_intelligence"]
        questions = [{"key": q.get("question_key"), "question": q.get("question")} for q in human.get("adaptive_questions", [])]
        payload = {
            "case": "walker_100m_no_wheelchair",
            "decision_readiness": human["decision_readiness"],
            "questions": questions,
            "must": [m.get("key") for m in result["decision_intelligence"]["client_intent"].get("must_haves", [])],
            "nice": [n.get("key") for n in result["decision_intelligence"]["client_intent"].get("nice_to_haves", [])],
            "top5": [r.get("facility_name") for r in result.get("results", [])],
            "finality": result["decision_intelligence"].get("decision_finality"),
        }
        print("BENCHMARK_CASE_2=" + json.dumps(payload, ensure_ascii=False))
        question_text = " ".join((q.get("question") or "") for q in questions).lower()
        compact_signal = any(token in question_text for token in ("compact", "walking distance", "central", "close together", "short distances"))
        self.assertTrue(compact_signal, f"Missing compact-layout/high-value mobility question: {questions}")


if __name__ == "__main__":
    unittest.main()
