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

    def test_human_decision_context_survives_fastapi_response_model(self) -> None:
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

        self.assertEqual(patient_decision["version"], "decision-intelligence-runtime-v1")
        self.assertEqual(policy_decision["version"], "decision-intelligence-runtime-v1")
        human = patient_decision["human_intelligence"]
        self.assertEqual(human["decision_readiness"], "NEEDS_CLARIFICATION")
        self.assertEqual(human["signals"]["recent_bereavement"]["value"], "YES")
        question_keys = {row["question_key"] for row in human["adaptive_questions"]}
        self.assertIn("community_size_preference", question_keys)
        self.assertIn("social_interaction_need_after_loss", question_keys)


if __name__ == "__main__":
    unittest.main()
