from __future__ import annotations

import unittest

from app.services.client_intent_runtime import evaluate_candidate_intent, intent_rank_key


class PreferenceConsistencyGuardTests(unittest.TestCase):
    def _intent(self) -> dict:
        return {
            "must_haves": [],
            "nice_to_haves": [
                {"key": "COMMUNITY_ENVIRONMENT_MATCH", "reason": "Explicit client preference"},
            ],
        }

    def _row(self, name: str, fit_score: float) -> dict:
        return {
            "facility_name": name,
            "canonical_type": "ASSISTED_LIVING_RFG",
            "housing_modalities": [],
            "care_setting_fit": {"status": "PRIMARY_FIT"},
            "human_person_fit": {
                "community_size": {
                    "preference": "LARGE",
                    "fit_score": fit_score,
                }
            },
            "matched_needs": [],
            "unknown_critical_needs": [],
            "regulatory_history": {},
        }

    def test_known_poor_fit_is_mismatch_not_match_or_unknown(self) -> None:
        row = self._row("Micro home", 20.0)
        fit = evaluate_candidate_intent(row, self._intent())
        self.assertEqual([], fit["nice_match"])
        self.assertEqual([], fit["nice_unknown"])
        self.assertEqual(["COMMUNITY_ENVIRONMENT_MATCH"], fit["nice_mismatch"])
        self.assertEqual("MISMATCH", fit["preference_consistency"])

    def test_explicit_large_preference_survives_final_ranking(self) -> None:
        large = self._row("Large community", 100.0)
        micro = self._row("Micro home", 20.0)
        large["client_intent_fit"] = evaluate_candidate_intent(large, self._intent())
        micro["client_intent_fit"] = evaluate_candidate_intent(micro, self._intent())
        ranked = sorted([micro, large], key=intent_rank_key)
        self.assertEqual("Large community", ranked[0]["facility_name"])
        self.assertEqual("MATCH", ranked[0]["client_intent_fit"]["preference_consistency"])
        self.assertEqual("MISMATCH", ranked[1]["client_intent_fit"]["preference_consistency"])


if __name__ == "__main__":
    unittest.main()
