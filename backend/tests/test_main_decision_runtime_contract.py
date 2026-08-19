from __future__ import annotations

import importlib
import unittest


class MainDecisionRuntimeContractTests(unittest.TestCase):
    def _questionnaire(self) -> dict:
        return {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 6500,
            "distanceFromFamily": "Balanced location",
        }

    def _query(self) -> str:
        return (
            "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, "
            "and needs help with bathing, dressing, meals and medication. No dementia."
        )

    def _couple_rehab_query(self) -> str:
        return (
            "A couple age 80+ wants to move to senior living in Las Vegas with lots of culture, classes and activities. "
            "The husband had spinal surgery and needs rehabilitation. He is expected to return to walking, but for the next "
            "3 months he needs help with bathing and dressing. The wife is independent and they want to live together."
        )

    def test_main_imports_integrated_decision_runtime_contract(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        self.assertTrue(hasattr(decision, "_regulatory_index"))
        self.assertTrue(callable(decision._regulatory_index))
        self.assertTrue(callable(decision.build_patient_needs_profile))
        self.assertTrue(callable(decision.build_patient_comparison_context))
        self.assertTrue(callable(decision.run_patient_decision_engine))
        self.assertIsNotNone(main.app)

    def test_pre_ranking_decision_intelligence_survives_patient_needs_response_model(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        profile = decision.build_patient_needs_profile(self._questionnaire(), self._query())
        serialized = main.PatientNeedsProfileOut.model_validate(profile).model_dump()
        self.assertIn("decision_intelligence", serialized)
        intelligence = serialized["decision_intelligence"]
        self.assertEqual(intelligence["version"], "decision-intelligence-runtime-v3")
        self.assertEqual(len(intelligence["success_factor_policy"]["factors"]), 16)
        self.assertEqual(
            [q["question_key"] for q in intelligence["adaptive_questions"]],
            ["community_size_preference", "social_interaction_need_after_loss", "move_participation"],
        )

    def test_decision_context_and_success_factor_trace_survive_fastapi_response_model(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        result = decision.run_patient_decision_engine(
            questionnaire_state=self._questionnaire(),
            natural_language_query=self._query(),
            limit=5,
        )
        serialized = main.PatientDecisionEngineOut.model_validate(result).model_dump()
        self.assertIn("decision_intelligence", serialized)
        self.assertIn("recommendation_audit_trace", serialized)
        patient_decision = serialized["patient_needs_profile"]["decision_intelligence"]
        policy_decision = serialized["care_setting_policy"]["decision_intelligence"]
        top_decision = serialized["decision_intelligence"]

        self.assertEqual(patient_decision["version"], "decision-intelligence-runtime-v3")
        self.assertEqual(policy_decision["version"], "decision-intelligence-runtime-v3")
        self.assertEqual(top_decision["version"], "decision-intelligence-runtime-v3")
        self.assertEqual(len(patient_decision["success_factor_policy"]["factors"]), 16)
        human = patient_decision["human_intelligence"]
        self.assertEqual(human["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(human["signals"]["recent_bereavement"]["value"], "YES")
        question_keys = [row["question_key"] for row in human["adaptive_questions"]]
        self.assertEqual(question_keys, ["community_size_preference", "social_interaction_need_after_loss", "move_participation"])

        self.assertTrue(serialized["results"])
        first = serialized["results"][0]
        self.assertEqual(len(first["success_factor_trace"]["factors"]), 16)
        self.assertIn("success_factor_summary", first["explanation"])
        self.assertIn("facility_size_as_independent_quality_factor", first["success_factor_trace"]["research_only_not_ranked"])
        self.assertEqual(serialized["recommendation_audit_trace"]["model_version"], "decision-intelligence-runtime-v3")

    def test_couple_spine_rehab_chooses_strategy_before_facility(self) -> None:
        decision = importlib.import_module("app.services.patient_decision_engine")
        state = {
            "relationship": "Dad",
            "ageGroup": "80+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "distanceFromFamily": "Balanced location",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "Large community"},
                "familyProfile": {"socialInteractionNeed": "Very important"},
            },
        }
        result = decision.run_patient_decision_engine(state, self._couple_rehab_query(), limit=5)
        intelligence = result["decision_intelligence"]
        strategy = intelligence["living_strategy"]
        self.assertEqual(strategy["household"]["type"], "COUPLE")
        self.assertTrue(strategy["signals"]["spine_or_back_surgery"])
        self.assertTrue(strategy["signals"]["expected_recovery"])
        self.assertEqual(strategy["signals"]["temporary_support_duration_months"], 3)
        ids = [row["strategy_id"] for row in strategy["strategy_candidates"]]
        self.assertIn("INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE", ids)
        self.assertIn("POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING", ids)
        self.assertIn("LIFE_PLAN_CCRC", ids)
        self.assertIn("ASSISTED_LIVING", ids)
        question_keys = [row["question_key"] for row in intelligence["human_intelligence"]["adaptive_questions"]]
        self.assertIn("medicare_status", question_keys)
        self.assertIn("move_timing_vs_rehab", question_keys)
        self.assertIn("monthly_budget", question_keys)
        self.assertIn("ccrc_entrance_fee_tolerance", question_keys)
        self.assertNotEqual(intelligence["decision_finality"], "FINAL")
        need_ids = {row["parameter_id"] for row in result["patient_needs_profile"]["needs"]}
        self.assertIn("pt", need_ids)
        self.assertIn("ot", need_ids)
        self.assertIn("adl_support", need_ids)


if __name__ == "__main__":
    unittest.main()
