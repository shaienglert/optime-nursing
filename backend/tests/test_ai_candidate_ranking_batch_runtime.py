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


    def test_calibration_reorders_top_window_using_single_shot_adjudication(self):
        rows = self._rows(24)

        def transport(payload):
            role = payload.get("role")
            candidates = payload["must_eligible_candidates"]
            if role == "OPTIME_NURSING_AI_CANDIDATE_SCORER":
                # Batch scores: FAC-01 highest, FAC-24 lowest -- these determine which
                # 20 candidates fall inside the calibration window.
                return {
                    "scored_candidates": [
                        {
                            "canonical_facility_id": item["canonical_facility_id"],
                            "score": 100 - int(item["canonical_facility_id"].split("-")[-1]),
                            "reason": "batch score",
                            "information_deficits": [],
                        }
                        for item in candidates
                    ]
                }
            # Calibration call: deliberately return the window in the OPPOSITE order
            # from the batch scores, so the assertions below can only pass if the
            # final order actually came from this call, not from the batch scores.
            ranked_ids = sorted((item["canonical_facility_id"] for item in candidates), reverse=True)
            return {
                "ranked_candidates": [
                    {"canonical_facility_id": cid, "reason": "calibrated", "information_deficits": []}
                    for cid in ranked_ids
                ]
            }

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
            "OPTIME_AI_RANKING_MAX_WORKERS": "2",
            "OPTIME_AI_RANKING_CALIBRATION_WINDOW": "20",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(status["calibrated_top_candidate_count"], 20)
        expected_calibrated_order = [f"FAC-{i:02d}" for i in range(20, 0, -1)]
        self.assertEqual([row["canonical_facility_id"] for row in ranked[:20]], expected_calibrated_order)
        self.assertEqual([row["canonical_facility_id"] for row in ranked[20:]], ["FAC-21", "FAC-22", "FAC-23", "FAC-24"])
        self.assertTrue(all(row["ai_ranking"]["status"] == "AI_BATCH_SCORED_CALIBRATED" for row in ranked[:20]))
        self.assertTrue(all(row["ai_ranking"]["status"] == "AI_BATCH_SCORED" for row in ranked[20:]))
        # global_score is preserved from the original batch scoring for every calibrated row.
        self.assertTrue(all(row["ai_ranking"]["global_score"] is not None for row in ranked[:20]))

    def test_calibration_failure_keeps_the_original_batch_order(self):
        rows = self._rows(24)
        call_count = {"n": 0}

        def transport(payload):
            role = payload.get("role")
            candidates = payload["must_eligible_candidates"]
            if role == "OPTIME_NURSING_AI_CANDIDATE_SCORER":
                return {
                    "scored_candidates": [
                        {
                            "canonical_facility_id": item["canonical_facility_id"],
                            "score": 100 - int(item["canonical_facility_id"].split("-")[-1]),
                            "reason": "batch score",
                            "information_deficits": [],
                        }
                        for item in candidates
                    ]
                }
            call_count["n"] += 1
            raise RuntimeError("calibration transport unavailable")

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
            "OPTIME_AI_RANKING_MAX_WORKERS": "2",
            "OPTIME_AI_RANKING_CALIBRATION_WINDOW": "20",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(call_count["n"], 1)
        self.assertEqual(status["status"], "AI_BATCH_RANKED")
        self.assertEqual(status["calibrated_top_candidate_count"], 0)
        self.assertEqual([row["canonical_facility_id"] for row in ranked[:3]], ["FAC-01", "FAC-02", "FAC-03"])
        self.assertTrue(all(row["ai_ranking"]["status"] == "AI_BATCH_SCORED" for row in ranked))

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
