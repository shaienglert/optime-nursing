from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class PersonalReportEndpointContractTests(unittest.TestCase):
    """Proves /decision-engine/personal-report's response_model doesn't silently drop fields.

    Same discipline as test_main_decision_runtime_contract.py: run the real pipeline with
    the AI interview mocked to a fixed readiness, then round-trip the result through the
    FastAPI Pydantic response model. A field that exists on the built payload but not on
    the response_model would be silently dropped by FastAPI at serialization time --
    this is exactly the class of bug fixed for market_coverage_notice earlier in this
    codebase's history.
    """

    def _questionnaire(self) -> dict:
        return {
            "relationship": "Father",
            "ageGroup": "80s",
            "assistanceLevel": "Needs help with dressing, bathing, and daily supervision",
            "memoryStatus": "Yes",
            "distanceFromFamily": "Balanced location",
            "budget": 6000,
            "entranceFeeTolerance": "No",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "No preference"},
                "familyProfile": {"socialInteractionNeed": "Neither"},
                "transitionRiskProfile": {"attitudeTowardMove": "Cautious but open"},
            },
        }

    def _query(self) -> str:
        return (
            "My father is 87 and lives in the Las Vegas area. He has moderate dementia. "
            "He needs help with dressing, bathing, and daily supervision."
        )

    def test_ready_report_survives_fastapi_response_model(self) -> None:
        main = importlib.import_module("app.main")
        decision = importlib.import_module("app.services.patient_decision_engine")
        builder = importlib.import_module("app.services.personal_decision_report_builder")

        ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ):
            decision_result = decision.run_patient_decision_engine(self._questionnaire(), self._query(), limit=5)

        payload = builder.build_personal_decision_report(
            questionnaire_state=self._questionnaire(),
            natural_language_query=self._query(),
            decision_result=decision_result,
        )
        serialized_dict = builder.serialize_personal_report_payload(payload)
        serialized = main.PersonalDecisionReportOut.model_validate(serialized_dict).model_dump()

        self.assertIn(serialized["user_role"], {"SELF", "FAMILY_MEMBER", "OTHER"})
        self.assertIn("YOUR_ROLE", serialized["sections"])
        self.assertIn("YOUR_SITUATION", serialized["sections"])
        if serialized["report_ready"]:
            self.assertGreater(len(serialized["candidates"]), 0)
            self.assertIn("WHY_THIS_PLACE", serialized["candidates"][0]["sections"])
        self.assertEqual(["SUCCESSFUL_TRANSITION"], serialized["omitted_sections"])

    def test_main_wires_personal_report_endpoint(self) -> None:
        main = importlib.import_module("app.main")
        self.assertTrue(callable(main.post_personal_decision_report))
        route_paths = {route.path for route in main.app.routes}
        self.assertIn("/decision-engine/personal-report", route_paths)


if __name__ == "__main__":
    unittest.main()
