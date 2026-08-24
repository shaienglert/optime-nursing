from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.ai_candidate_ranking_runtime import rank_must_eligible_candidates


class BatchedAIRankingRuntimeTests(unittest.TestCase):
    def _rows(self, count: int):
        return [
            {
                "canonical_facility_id": f"FAC-{index:02d}",
                "facility_name": f"Facility {index}",
                "must_eligibility": "MUST_ELIGIBLE",
                "client_intent_fit": {"hard_gate": "PASS"},
                "care_setting_fit": {"status": "PRIMARY_FIT"},
            }
            for index in range(1, count + 1)
        ]

    def test_large_candidate_set_is_batch_scored_and_globally_sorted(self):
        rows = self._rows(24)

        def transport(payload):
            candidates = payload["must_eligible_candidates"]
            return {
                "scored_candidates": [
                    {
                        "canonical_facility_id": item["canonical_facility_id"],
                        "score": 100 - int(item["canonical_facility_id"].split("-")[-1]),
                        "reason": "governed batch score",
                        "information_deficits": [],
                    }
                    for item in candidates
                ]
            }

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
            "OPTIME_AI_RANKING_MAX_WORKERS": "2",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(status["status"], "AI_BATCH_RANKED")
        self.assertEqual([row["canonical_facility_id"] for row in ranked], [f"FAC-{index:02d}" for index in range(1, 25)])
        self.assertTrue(all(row["ai_ranking"]["status"] == "AI_BATCH_SCORED" for row in ranked))
        self.assertTrue(all("global_score" in row["ai_ranking"] for row in ranked))

    def test_failed_batch_falls_back_for_entire_set_when_ai_not_required(self):
        rows = self._rows(24)

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=RuntimeError("boom")):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(status["status"], "DETERMINISTIC_FALLBACK")
        self.assertEqual(len(ranked), 24)
        self.assertTrue(all(row["ai_ranking"]["status"] == "DETERMINISTIC_FALLBACK" for row in ranked))


if __name__ == "__main__":
    unittest.main()
