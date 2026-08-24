from __future__ import annotations

import unittest

from app.services.ai_candidate_ranking_runtime import attach_nice_coverage
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent


class SpecificNicePreferenceTests(unittest.TestCase):
    def _intent(self) -> dict:
        return build_client_intent(
            {"locationCity": "Las Vegas"},
            "My mother is 90. She loves classical music and being around people. We are looking in the Las Vegas Valley.",
            {"signals": {"high_social_culture_priority": True}, "household": {}},
            {"signals": {}},
        )

    def _row(self, evidence: dict) -> dict:
        return {
            "canonical_facility_id": "TEST-1",
            "facility_name": "Test Community",
            "city": "Las Vegas",
            "state": "NV",
            "canonical_type": "ASSISTED_LIVING_RFG",
            "housing_modalities": ["ASSISTED_LIVING"],
            "provider_housing_evidence": {"evidence": evidence},
            "matched_needs": [],
            "unknown_critical_needs": [],
        }

    def test_classical_music_is_preserved_as_separate_nice(self) -> None:
        intent = self._intent()
        keys = [item["key"] for item in intent["nice_to_haves"]]
        self.assertIn("RICH_CULTURE_AND_ACTIVITIES", keys)
        self.assertIn("CLASSICAL_MUSIC_ACCESS", keys)
        self.assertNotEqual(keys.index("RICH_CULTURE_AND_ACTIVITIES"), keys.index("CLASSICAL_MUSIC_ACCESS"))

    def test_generic_social_programming_cannot_satisfy_classical_music(self) -> None:
        intent = self._intent()
        fit = evaluate_candidate_intent(self._row({"social_engagement_verified": True}), intent)
        self.assertIn("RICH_CULTURE_AND_ACTIVITIES", fit["nice_match"])
        self.assertIn("CLASSICAL_MUSIC_ACCESS", fit["nice_unknown"])
        row = self._row({"social_engagement_verified": True})
        row["client_intent_fit"] = fit
        summary = attach_nice_coverage([row], intent)
        self.assertEqual(row["nice_to_have_coverage"]["status"], "NICE_PARTIAL")
        self.assertEqual(summary["nice_complete_candidate_count"], 0)

    def test_exact_verified_classical_music_can_complete_that_preference(self) -> None:
        intent = self._intent()
        fit = evaluate_candidate_intent(
            self._row({"social_engagement_verified": True, "classical_music_verified": True}),
            intent,
        )
        self.assertIn("CLASSICAL_MUSIC_ACCESS", fit["nice_match"])
        self.assertNotIn("CLASSICAL_MUSIC_ACCESS", fit["nice_unknown"])


if __name__ == "__main__":
    unittest.main()
