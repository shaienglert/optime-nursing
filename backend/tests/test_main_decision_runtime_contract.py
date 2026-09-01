from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class MainDecisionRuntimeContractTests(unittest.TestCase):
    def _questionnaire(self) -> dict:
        return {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 6500,
            "distanceFromFamily": "Balanced location",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "No preference"},
                "familyProfile": {"socialInteractionNeed": "Neither"},
                "transitionRiskProfile": {"attitudeTowardMove": "Cautious but open"},
            },
        }

    def _query(self) -> str:
        return (
            "My father is 84, recently widowed, lives in Las Vegas, is mentally alert and mobile, "
            "and needs help with bathing, dressing and meals. No dementia."
        )

    def _couple_rehab_query(self) -> str:
        return (
            "A couple age 80+ wants to move to senior living in Las Vegas with lots of culture, classes and activities. "
            "The husband had spinal surgery and needs rehabilitation. He is expected to return to walking, but for the next "
            "3 months he needs help with bathing and dressing. The wife is independent and they want to live together."
        )

    def _ai(self, readiness: str, next_question: str | None = None):
        return patch.multiple(
            "app.services.human_intelligence_runtime_verified",
            interpret_client_intent_with_ai=unittest.mock.DEFAULT,
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
        question = "What would make the move feel most comfortable for him?"
        ai_result = {"decision_readiness": "NEEDS_CLARIFICATION", "next_question": question, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ):
            profile = decision.build_patient_needs_profile(self._questionnaire(), self._query())
        serialized = main.PatientNeedsProfileOut.model_validate(profile).model_dump()
        intelligence = serialized["decision_intelligence"]
        self.assertEqual(intelligence["version"], "decision-intelligence-runtime-v3.1")
        self.assertIn("client_intent", intelligence)
        self.assertEqual(len(intelligence["success_factor_policy"]["factors"]), 16)
        self.assertEqual("NEEDS_CLARIFICATION", intelligence["decision_readiness"])
        self.assertEqual(1, len(intelligence["adaptive_questions"]))
        self.assertTrue(intelligence["adaptive_questions"][0]["question_key"].startswith("semantic_ai_high_information_question:"))
        self.assertEqual(question, intelligence["adaptive_questions"][0]["question"])

    def test_non_ready_interview_survives_fastapi_response_model_without_recommendations(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        question = "Which part of the transition needs clarification first?"
        ai_result = {"decision_readiness": "NEEDS_CLARIFICATION", "next_question": question, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ):
            result = decision.run_patient_decision_engine(self._questionnaire(), self._query(), limit=5)
        serialized = main.PatientDecisionEngineOut.model_validate(result).model_dump()
        top_decision = serialized["decision_intelligence"]
        self.assertEqual("PENDING_CLIENT_INPUT_REQUIRED", top_decision["decision_finality"])
        self.assertFalse(top_decision["recommendation_execution_allowed"])
        self.assertEqual("SEMANTIC_AI", top_decision["interview_owner"])
        self.assertEqual([], serialized["results"])
        self.assertEqual(0, serialized["result_count"])
        self.assertEqual(0, serialized["total_candidates_scored"])
        self.assertTrue(serialized["recommendation_audit_trace"]["blocked_before_facility_ranking"])

    def test_ready_decision_context_and_success_factor_trace_survive_fastapi_response_model(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ):
            result = decision.run_patient_decision_engine(self._questionnaire(), self._query(), limit=5)
        serialized = main.PatientDecisionEngineOut.model_validate(result).model_dump()
        patient_decision = serialized["patient_needs_profile"]["decision_intelligence"]
        policy_decision = serialized["care_setting_policy"]["decision_intelligence"]
        top_decision = serialized["decision_intelligence"]

        for ctx in (patient_decision, policy_decision, top_decision):
            self.assertEqual(ctx["version"], "decision-intelligence-runtime-v3.1")
            self.assertIn("client_intent", ctx)
        self.assertFalse(top_decision["recommendation_execution_allowed"])
        self.assertEqual("DETERMINISTIC_FALLBACK", top_decision["ai_ranking"]["status"])
        self.assertEqual(
            top_decision["ranking_order"],
            [
                "DETERMINISTIC_MUST_GATE",
                "SEMANTIC_AI_DYNAMIC_PREFERENCES",
                "SEMANTIC_AI_ALL_GOVERNED_EVIDENCE",
                "EVIDENCE_GROUNDED_PREFERENCE_COVERAGE",
                "PROVIDER_VERIFICATION",
                "AI_RERANK",
            ],
        )
        self.assertEqual(len(patient_decision["success_factor_policy"]["factors"]), 16)
        human = patient_decision["human_intelligence"]
        self.assertEqual(human["decision_readiness"], "READY")
        self.assertEqual(human["signals"]["recent_bereavement"]["value"], "YES")
        self.assertEqual([], human["adaptive_questions"])
        self.assertEqual([], serialized["results"])
        self.assertEqual(serialized["recommendation_audit_trace"]["model_version"], "decision-intelligence-runtime-v3.1")

    def test_couple_spine_rehab_unknowns_are_guardian_inputs_not_scripted_questions(self) -> None:
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
        question = "Which unresolved care-strategy issue should we clarify first?"
        ai_result = {"decision_readiness": "NEEDS_CLARIFICATION", "next_question": question, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ):
            profile = decision.build_patient_needs_profile(state, self._couple_rehab_query())
            result = decision.run_patient_decision_engine(state, self._couple_rehab_query(), limit=5)
        human = profile["decision_intelligence"]["human_intelligence"]
        strategy_guardian = human["living_strategy_guardian"]
        unknowns = set(strategy_guardian["material_unknowns"])
        for required in ("medicare_status", "move_timing_vs_rehab", "monthly_budget", "ccrc_entrance_fee_tolerance"):
            self.assertIn(required, unknowns)
        self.assertEqual(1, len(human["adaptive_questions"]))
        self.assertTrue(human["adaptive_questions"][0]["question_key"].startswith("semantic_ai_high_information_question:"))
        self.assertTrue(human["adaptive_questions"][0].get("target_fact_key"))
        self.assertEqual([], result["results"])
        self.assertEqual("PENDING_CLIENT_INPUT_REQUIRED", result["decision_intelligence"]["decision_finality"])


if __name__ == "__main__":
    unittest.main()
