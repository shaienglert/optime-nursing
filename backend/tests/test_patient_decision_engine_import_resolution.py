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

    def test_public_import_exposes_nevada_governed_behavior_after_ai_ready(self) -> None:
        module = importlib.import_module("app.services.patient_decision_engine")
        ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
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
        self.assertFalse(result["decision_intelligence"]["recommendation_execution_allowed"])
        self.assertEqual("DETERMINISTIC_FALLBACK", result["decision_intelligence"]["ai_ranking"]["status"])
        self.assertEqual("SEMANTIC_AI", result["decision_intelligence"]["interview_owner"])
        self.assertIn("living_strategy", result["decision_intelligence"])
        self.assertIn("client_intent", result["decision_intelligence"])
        self.assertIn("must_gate", result["decision_intelligence"])
        self.assertEqual(len(result["decision_intelligence"]["success_factor_policy"]["factors"]), 16)
        self.assertEqual([], result["results"])


if __name__ == "__main__":
    unittest.main()
