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
        intelligence = serialized["decision_intelligence"]
        self.assertEqual(intelligence["version"], "decision-intelligence-runtime-v3.1")
        self.assertIn("client_intent", intelligence)
        self.assertEqual(len(intelligence["success_factor_policy"]["factors"]), 16)
        self.assertEqual(
            [q["question_key"] for q in intelligence["adaptive_questions"]],
            ["community_size_preference", "social_interaction_need_after_loss", "move_participation"],
        )

    def test_decision_context_and_success_factor_trace_survive_fastapi_response_model(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        result = decision.run_patient_decision_engine(self._questionnaire(), self._query(), limit=5)
        serialized = main.PatientDecisionEngineOut.model_validate(result).model_dump()
        patient_decision = serialized["patient_needs_profile"]["decision_intelligence"]
        policy_decision = serialized["care_setting_policy"]["decision_intelligence"]
        top_decision = serialized["decision_intelligence"]

        for ctx in (patient_decision, policy_decision, top_decision):
            self.assertEqual(ctx["version"], "decision-intelligence-runtime-v3.1")
            self.assertIn("client_intent", ctx)
        self.assertEqual(
            top_decision["ranking_order"],
            ["CLIENT_INTENT", "MUST_GATE", "NICE_TO_HAVE", "GOVERNMENT_REGULATORY_DATA", "PUBLIC_REPUTATION", "RELEVANT_EVIDENCE_COMPLETENESS"],
        )
        self.assertEqual(len(patient_decision["success_factor_policy"]["factors"]), 16)
        human = patient_decision["human_intelligence"]
        self.assertEqual(human["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(human["signals"]["recent_bereavement"]["value"], "YES")
        self.assertEqual(
            [row["question_key"] for row in human["adaptive_questions"]],
            ["community_size_preference", "social_interaction_need_after_loss", "move_participation"],
        )

        self.assertTrue(serialized["results"])
        first = serialized["results"][0]
        self.assertIn("client_intent_fit", first)
        self.assertIn(first["client_intent_fit"]["hard_gate"], {"PASS", "PENDING_VERIFICATION"})
        self.assertEqual(len(first["success_factor_trace"]["factors"]), 16)
        self.assertIn("success_factor_summary", first["explanation"])
        self.assertEqual(serialized["recommendation_audit_trace"]["model_version"], "decision-intelligence-runtime-v3.1")

    def test_couple_spine_rehab_chooses_strategy_and_must_gate_before_facility(self) -> None:
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
        intent = intelligence["client_intent"]
        self.assertEqual(strategy["household"]["type"], "COUPLE")
        self.assertTrue(strategy["signals"]["spine_or_back_surgery"])
        self.assertTrue(strategy["signals"]["expected_recovery"])
        self.assertEqual(strategy["signals"]["temporary_support_duration_months"], 3)
        strategy_ids = [row["strategy_id"] for row in strategy["strategy_candidates"]]
        self.assertIn("INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE", strategy_ids)
        self.assertIn("POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING", strategy_ids)
        self.assertIn("LIFE_PLAN_CCRC", strategy_ids)
        self.assertIn("ASSISTED_LIVING", strategy_ids)
        must_keys = {row["key"] for row in intent["must_haves"]}
        self.assertTrue({"LAS_VEGAS", "COUPLE_CORESIDENCE", "ADL_SUPPORT_AVAILABLE", "REHAB_PATH_AVAILABLE", "RECOVERY_TRANSITION_COMPATIBLE"}.issubset(must_keys))
        nice_keys = {row["key"] for row in intent["nice_to_haves"]}
        self.assertIn("RICH_CULTURE_AND_ACTIVITIES", nice_keys)
        question_keys = [row["question_key"] for row in intelligence["human_intelligence"]["adaptive_questions"]]
        for required in ("medicare_status", "move_timing_vs_rehab", "monthly_budget", "ccrc_entrance_fee_tolerance"):
            self.assertIn(required, question_keys)
        self.assertTrue(intelligence["decision_finality"].startswith("PROVISIONAL_"))
        need_ids = {row["parameter_id"] for row in result["patient_needs_profile"]["needs"]}
        self.assertTrue({"pt", "ot", "adl_support"}.issubset(need_ids))
        self.assertGreaterEqual(result["must_gate_survivor_count"], len(result["results"]))
        self.assertTrue(all((row["client_intent_fit"]["hard_gate"] != "FAIL") for row in result["results"]))


if __name__ == "__main__":
    unittest.main()
