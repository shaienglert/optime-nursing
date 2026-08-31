from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.ai_candidate_ranking_runtime import rank_must_eligible_candidates
from app.services.semantic_preference_runtime import build_facility_claim_ledger


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


    def test_single_shot_ranking_accepts_a_real_claim_citation(self):
        row = {
            "canonical_facility_id": "FAC-01",
            "facility_name": "Facility 1",
            "must_eligibility": "MUST_ELIGIBLE",
            "client_intent_fit": {"hard_gate": "PASS"},
            "care_setting_fit": {"status": "PRIMARY_FIT"},
            "regulatory_history": {"latest_known_grade": "A"},
        }
        real_claim_id = build_facility_claim_ledger(row)["claims"][0]["claim_id"]

        def transport(payload):
            return {
                "ranked_candidates": [
                    {
                        "canonical_facility_id": "FAC-01",
                        "reason": "governed single-shot rank",
                        "information_deficits": [],
                        "rank_drivers": [real_claim_id],
                        "rank_risks": [],
                    }
                ]
            }

        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport
        ):
            ranked, status = rank_must_eligible_candidates(
                [row],
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda r: (str(r["canonical_facility_id"]),),
            )

        self.assertEqual(status["status"], "AI_RANKED")
        self.assertEqual(ranked[0]["ai_ranking"]["rank_drivers"], [real_claim_id])
        self.assertEqual(ranked[0]["ai_ranking"]["rank_risks"], [])

    def test_fabricated_claim_citation_is_rejected_and_falls_back(self):
        rows = self._rows(1)

        def transport(payload):
            return {
                "ranked_candidates": [
                    {
                        "canonical_facility_id": "FAC-01",
                        "reason": "governed single-shot rank",
                        "information_deficits": [],
                        "rank_drivers": ["claim:does-not-exist-in-the-ledger"],
                        "rank_risks": [],
                    }
                ]
            }

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda r: (str(r["canonical_facility_id"]),),
            )

        self.assertEqual(status["status"], "DETERMINISTIC_FALLBACK")
        self.assertEqual(ranked[0]["ai_ranking"]["status"], "DETERMINISTIC_FALLBACK")

    def test_fabricated_claim_citation_fails_closed_when_ranking_required(self):
        rows = self._rows(1)

        def transport(payload):
            return {
                "ranked_candidates": [
                    {
                        "canonical_facility_id": "FAC-01",
                        "reason": "governed single-shot rank",
                        "information_deficits": [],
                        "rank_drivers": ["claim:does-not-exist-in-the-ledger"],
                        "rank_risks": [],
                    }
                ]
            }

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            with self.assertRaisesRegex(RuntimeError, "AI_CANDIDATE_RANKING_REQUIRED_FAILED"):
                rank_must_eligible_candidates(
                    rows,
                    client_intent={},
                    human_context={"dynamic_preference_model": {"preferences": []}},
                    strategy={},
                    deterministic_fallback_key=lambda r: (str(r["canonical_facility_id"]),),
                )


if __name__ == "__main__":
    unittest.main()
