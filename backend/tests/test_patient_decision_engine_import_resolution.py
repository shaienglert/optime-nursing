from __future__ import annotations

import importlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache


class PatientDecisionEngineImportResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("import_resolution_test_setup")

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("import_resolution_test_teardown")

    def test_public_import_resolves_to_integrated_runtime(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        module_file = Path(module.__file__).as_posix()
        self.assertTrue(module_file.endswith("/app/services/patient_decision_engine_runtime/__init__.py"), module_file)

    def test_memory_supervision_does_not_become_skilled_nursing(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        profile = module.build_patient_needs_profile(
            {"assistanceLevel": "Help with bathing, 24/7 support required", "memoryStatus": "Significant memory issues"},
            "Severe dementia requiring 24/7 supervision in a secure memory setting.",
        )
        ids = {item["parameter_id"] for item in profile["needs"]}
        self.assertIn("memory_care", ids)
        self.assertNotIn("skilled_nursing_capabilities", ids)
        self.assertNotIn("nursing_24_7", ids)

    def test_clinical_free_text_creates_case_relevant_parameters(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        profile = module.build_patient_needs_profile(
            {"assistanceLevel": "Help with medications", "memoryStatus": "No"},
            "Needs dialysis, daily wound care, and continuous oxygen.",
        )
        by_id = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertEqual("REQUIRED", by_id["dialysis_arrangements"]["requirement_level"])
        self.assertEqual("HIGH", by_id["wound_care"]["requirement_level"])
        self.assertEqual("HIGH", by_id["respiratory_trach_vent"]["requirement_level"])

    def test_governed_setting_routes_memory_and_rehab_separately(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        governed = module._governed
        memory = governed._care_setting_fit(
            {"requires_memory": True, "requires_skilled": False, "requires_rehab": False, "requires_stroke": False, "needs_residential_assistance": True},
            {"canonical_type": "ASSISTED_LIVING_RFG"},
            {"memory_care_classification": "CONFIRMED", "synthetic_archetype": "MEMORY_CARE"},
        )
        rehab = governed._care_setting_fit(
            {"requires_memory": False, "requires_skilled": False, "requires_rehab": True, "requires_stroke": False, "needs_residential_assistance": True},
            {"canonical_type": "SKILLED_NURSING"},
            {"synthetic_archetype": "REHABILITATION"},
        )
        self.assertEqual("PRIMARY_FIT", memory["status"])
        self.assertEqual("PRIMARY_FIT", rehab["status"])

    def test_ineligible_candidate_cannot_enter_visible_ranking(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        self.assertFalse(module._is_rankable_candidate({
            "eligibility_status": "INELIGIBLE",
            "client_intent_fit": {"hard_gate": "PASS"},
        }))
        self.assertTrue(module._is_rankable_candidate({
            "eligibility_status": "INSUFFICIENT_EVIDENCE",
            "client_intent_fit": {"hard_gate": "PENDING_VERIFICATION"},
        }))

    def test_synthetic_memory_only_archetype_is_not_forced_on_cognitively_intact_resident(self) -> None:
        from app.services.client_intent_runtime import evaluate_candidate_intent

        fit = evaluate_candidate_intent(
            {
                "canonical_type": "ASSISTED_LIVING_RFG",
                "synthetic_archetype": "MEMORY_CARE",
                "city": "LAS VEGAS",
                "state": "NV",
            },
            {"must_haves": [{"key": "NO_FORCED_MEMORY_PLACEMENT"}], "nice_to_haves": []},
        )
        self.assertEqual("FAIL", fit["hard_gate"])
        self.assertIn("NO_FORCED_MEMORY_PLACEMENT", fit["must_fail"])

    def test_public_import_exposes_nevada_governed_behavior_after_ai_ready(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
        # The fixture states a budget (a required minimum client dimension), which is now
        # also a facility-owned MUST (see semantic_facility_requirements.py's
        # SEMANTIC_BUDGET_VERIFICATION). No facility in the real, unmocked Las Vegas data
        # this test runs against has verified pricing evidence, so without this mock every
        # candidate would gate to PENDING_VERIFICATION on budget alone.
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ), patch(
            "app.services.governed_evidence_runtime.agent_and_provider_payloads", return_value=[{"published_rates_verified": True}]
        ):
            result = module.run_patient_decision_engine(
                {
                    "relationship": "Dad",
                    "ageGroup": "80-84",
                    "assistanceLevel": "Needs assistance with bathing and dressing",
                    "memoryStatus": "No",
                    "budget": 6500,
                    "distanceFromFamily": "Balanced location",
                },
                "My father is 84, lives in Las Vegas, is mentally alert and mobile, and needs help with bathing, dressing and meals. No dementia.",
                limit=5,
            )
        self.assertEqual(result["patient_needs_profile"]["location_city"], "LAS VEGAS")
        self.assertEqual(result["care_setting_policy"]["version"], "v1.1")
        self.assertEqual(result["decision_intelligence"]["version"], "decision-intelligence-runtime-v3.1")
        # The ranking model is unavailable in this environment, so the hard criteria carry
        # the result: the eligible set is shown, explicitly unordered, with a degradation
        # notice. It used to be hidden entirely, which told the family nothing.
        self.assertTrue(result["decision_intelligence"]["recommendation_execution_allowed"])
        self.assertTrue(result["decision_intelligence"]["canonical_decision_state"]["is_degraded_result"])
        self.assertEqual("SEMANTIC_AI", result["decision_intelligence"]["interview_owner"])
        self.assertIn("living_strategy", result["decision_intelligence"])
        self.assertIn("client_intent", result["decision_intelligence"])
        self.assertIn("must_gate", result["decision_intelligence"])
        self.assertEqual(len(result["decision_intelligence"]["success_factor_policy"]["factors"]), 16)
        self.assertFalse(result["degraded_result_notice"]["results_are_ordered"])


if __name__ == "__main__":
    unittest.main()
