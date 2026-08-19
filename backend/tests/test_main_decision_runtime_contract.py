from __future__ import annotations

import importlib
import unittest


class MainDecisionRuntimeContractTests(unittest.TestCase):
    def test_main_imports_integrated_decision_runtime_contract(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        self.assertTrue(hasattr(decision, "_regulatory_index"))
        self.assertTrue(callable(decision._regulatory_index))
        self.assertTrue(callable(decision.build_patient_needs_profile))
        self.assertTrue(callable(decision.build_patient_comparison_context))
        self.assertTrue(callable(decision.run_patient_decision_engine))
        self.assertIsNotNone(main.app)

    def test_decision_context_and_success_factor_trace_survive_fastapi_response_model(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        result = decision.run_patient_decision_engine(
            questionnaire_state={
                "relationship": "Dad",
                "ageGroup": "80-84",
                "assistanceLevel": "Needs assistance with bathing and dressing",
                "memoryStatus": "No",
                "budget": 6500,
                "distanceFromFamily": "Balanced location",
            },
            natural_language_query=(
                "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, "
                "and needs help with bathing, dressing, meals and medication. No dementia."
            ),
            limit=5,
        )
        serialized = main.PatientDecisionEngineOut.model_validate(result).model_dump()
        patient_decision = serialized["patient_needs_profile"]["decision_intelligence"]
        policy_decision = serialized["care_setting_policy"]["decision_intelligence"]

        self.assertEqual(patient_decision["version"], "decision-intelligence-runtime-v2")
        self.assertEqual(policy_decision["version"], "decision-intelligence-runtime-v2")
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


if __name__ == "__main__":
    unittest.main()
