from __future__ import annotations

import unittest

from app.services.patient_decision_engine_runtime import build_patient_needs_profile, run_patient_decision_engine
from app.services.success_factor_runtime import FACTOR_POLICY, build_success_factor_trace


class SuccessFactorRuntimeTests(unittest.TestCase):
    def _state(self, size: str = "Large community") -> dict:
        return {
            "relationship": "Dad",
            "ageGroup": "80-84",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "humanIntelligenceV2": {
                "familyProfile": {
                    "widowStatus": "Yes",
                    "lossTiming": "Within 6 months",
                    "socialInteractionNeed": "Neither",
                    "visitFrequencyExpectation": "Weekly",
                },
                "familyCultureProfile": {"decisionRole": "Shared decision"},
                "personalityProfile": {
                    "communitySizePreference": size,
                    "privacyImportance": "High",
                },
                "transitionRiskProfile": {
                    "bereavementStatus": "Yes, within 1 year",
                    "attitudeTowardMove": "Cautious but open",
                },
                "independenceProfile": {"abilityToLeaveIndependently": "Very important"},
                "futureCareProfile": {"avoidFutureMovesPreference": "Important"},
                "languageProfile": {"preferredSpokenLanguage": "English"},
                "foodProfile": {"dietaryPreferences": []},
                "socialProfile": {"preferredSocialIntensity": "Balanced"},
                "culturalProfile": {"whatFeelsLikeHome": ["Family-centered culture"]},
                "distanceProfile": {"familyVisitExpectation": "Weekly"},
            },
        }

    def test_all_approved_v1_factors_are_connected_to_trace(self) -> None:
        profile = build_patient_needs_profile(self._state(), "84-year-old recently widowed man in Las Vegas")
        trace = build_success_factor_trace(self._state(), profile)
        self.assertEqual(len(FACTOR_POLICY), 16)
        self.assertEqual(len(trace["factors"]), 16)
        self.assertTrue(trace["policy"]["unknown_is_not_mismatch"])
        self.assertTrue(trace["policy"]["no_unvalidated_numeric_success_weights"])
        self.assertTrue(trace["policy"]["facility_size_is_not_independent_quality"])
        self.assertIn("facility_size_as_independent_quality_factor", trace["research_only_not_ranked"])

    def test_recommendation_contains_factor_and_audit_trace(self) -> None:
        result = run_patient_decision_engine(
            questionnaire_state=self._state(),
            natural_language_query="My father is 84, recently widowed, mobile and mentally alert in Las Vegas and needs ADL help.",
            limit=2,
        )
        self.assertEqual(result["decision_intelligence"]["version"], "decision-intelligence-runtime-v2")
        self.assertIn("success_factor_policy", result["decision_intelligence"])
        self.assertIn("recommendation_audit_trace", result)
        self.assertEqual(len(result["results"]), 2)
        for row in result["results"]:
            self.assertEqual(len(row["success_factor_trace"]["factors"]), 16)
            self.assertIn("success_factor_summary", row["explanation"])
        rules = result["recommendation_audit_trace"]["decision_rules_applied"]
        self.assertIn("facility_size_not_independent_quality", rules)
        self.assertIn("success_factor_influence_classes_no_unvalidated_numeric_weights", rules)

    def test_explicit_environment_preference_changes_fit_not_quality(self) -> None:
        large = run_patient_decision_engine(self._state("Large community"), "recently widowed in Las Vegas", limit=5)
        small = run_patient_decision_engine(self._state("Small community"), "recently widowed in Las Vegas", limit=5)
        large_ids = [row["canonical_facility_id"] for row in large["results"]]
        small_ids = [row["canonical_facility_id"] for row in small["results"]]
        self.assertNotEqual(large_ids, small_ids)
        for result in (large, small):
            for row in result["results"]:
                size = row["human_person_fit"]["community_size"]
                self.assertTrue(size["not_a_quality_factor"])
                self.assertEqual(size["policy_role"], "EXPLICIT_PREFERENCE_CONGRUENCE_ONLY")


if __name__ == "__main__":
    unittest.main()
