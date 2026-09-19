from __future__ import annotations

import unittest

from app.services import patient_decision_engine as production_runtime


class LaunchPracticalConstraintContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Follow the explicit production chain: integrated runtime -> governed
        # facade -> legacy evidence core. Never rely on the ambiguous
        # patient_decision_engine module/package name for private contracts.
        cls.core = production_runtime._governed._legacy

    def test_budget_and_pending_medicaid_survive_the_production_profile(self) -> None:
        profile = production_runtime.build_patient_needs_profile(
            {},
            "Her budget is $5,000 per month and Medicaid eligibility is pending.",
        )
        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertIn("published_rates", needs)
        self.assertIn("medicaid_attributes", needs)
        self.assertIn("budget", profile["natural_language_mapping"]["extraction"]["recognized_tokens"])
        self.assertIn("medicaid", profile["natural_language_mapping"]["extraction"]["recognized_tokens"])

    def test_negated_medicaid_does_not_become_a_preference(self) -> None:
        profile = production_runtime.build_patient_needs_profile(
            {"medicaidStatus": "Not eligible"},
            "He has Medicare and is not applying for Medicaid.",
        )
        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertNotIn("medicaid_attributes", needs)
        self.assertNotIn("medicaid", profile["natural_language_mapping"]["extraction"]["recognized_tokens"])

    def test_structured_medicaid_status_survives_without_keyword_in_story(self) -> None:
        profile = production_runtime.build_patient_needs_profile(
            {"medicaidStatus": "Application pending"},
            "She needs help finding an appropriate community.",
        )
        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertEqual("questionnaire.medicaidStatus", needs["medicaid_attributes"]["user_evidence_source"])

    def test_practical_gaps_are_visible_without_becoming_safety_failures(self) -> None:
        needs = [
            {"parameter_id": "published_rates", "requirement_level": "PREFERENCE", "desired_value": "KNOWN", "acceptable_values": ["KNOWN", "UNKNOWN"]},
            {"parameter_id": "medicaid_attributes", "requirement_level": "PREFERENCE", "desired_value": "YES", "acceptable_values": ["YES", "UNKNOWN"]},
        ]
        eligibility = self.core._eligibility_from_needs(needs, {})
        _strong, verify, _concerns = self.core._top_reasons(
            eligibility,
            [{"parameter_id": "current_availability"}],
        )

        self.assertEqual("ELIGIBLE", eligibility["eligibility_status"])
        self.assertEqual(2, len(eligibility["unknown_preferences"]))
        self.assertIn("Current monthly pricing and fees must be confirmed against your stated budget", verify)
        self.assertIn("Medicaid acceptance and the applicable payment pathway must be confirmed", verify)
        self.assertEqual(
            [
                "Current availability must be confirmed directly with the facility",
                "Current monthly pricing and fees must be confirmed against your stated budget",
                "Medicaid acceptance and the applicable payment pathway must be confirmed",
            ],
            verify[:3],
        )


if __name__ == "__main__":
    unittest.main()
