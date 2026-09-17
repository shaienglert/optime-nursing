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
        # Every batch splits all the way down to individual candidates trying to
        # recover from "boom" (see ai_ranking_batch_split_retry warnings), and only
        # once every single one is unrecoverable does the whole set fall back. The
        # fallback reason must still survive into the returned status -- otherwise a
        # caller (including the API response) has no way to see why ranking degraded,
        # only that it did.
        self.assertIn("CLOSED_WORLD_VIOLATION", status["fallback_reason"])

    def test_fallback_reason_reflects_a_closed_world_violation_that_broke_every_batch(self):
        # A closed-world violation (wrong candidate set returned) is still a hard
        # failure -- unlike a fabricated citation, which is now stripped rather than
        # fatal (see test_fabricated_claim_citation_is_stripped_but_score_and_rank_are_
        # kept). Every batch returning an empty set here forces a full fallback, and
        # the status object must say why, not just that it happened.
        rows = self._rows(24)

        def transport(payload):
            return {"scored_candidates": []}

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(status["status"], "DETERMINISTIC_FALLBACK")
        self.assertIn("CLOSED_WORLD_VIOLATION", status["fallback_reason"])

    def test_one_persistently_confused_batch_no_longer_erases_every_other_batchs_valid_scores(self):
        # Reproduces the real production pattern: a large batch returns a closed-world
        # violation (candidates confused with each other), but the same candidates
        # score cleanly once split into smaller groups -- exactly what happened when
        # production's 13-batch, 374-candidate run failed on one batch and lost all
        # 373 other, perfectly valid scores with it.
        rows = self._rows(24)
        calls = []

        def transport(payload):
            candidates = payload["must_eligible_candidates"]
            calls.append(len(candidates))
            ids = [item["canonical_facility_id"] for item in candidates]
            if "FAC-07" in ids and len(candidates) > 2:
                # This group confuses the model into returning duplicates for the
                # batch containing FAC-07, but only when grouped with 3+ others.
                return {"scored_candidates": [
                    {"canonical_facility_id": ids[0], "score": 50, "reason": "r", "information_deficits": []}
                    for _ in candidates
                ]}
            return {"scored_candidates": [
                {"canonical_facility_id": item["canonical_facility_id"], "score": 100 - int(item["canonical_facility_id"].split("-")[-1]), "reason": "r", "information_deficits": []}
                for item in candidates
            ]}

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        # Every one of the 24 candidates -- including the ones that shared a batch
        # with FAC-07 -- got a real AI score, not a full-set deterministic fallback.
        self.assertEqual(status["status"], "AI_BATCH_RANKED")
        self.assertEqual(len(ranked), 24)
        self.assertTrue(all(row["ai_ranking"]["status"] == "AI_BATCH_SCORED" for row in ranked))
        # It took more than the original 4 batch calls to get there.
        self.assertGreater(len(calls), 4)


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
            # Zero margin: this test isolates "did the reorder come from the calibration
            # call", not near-boundary window extension (covered separately below).
            "OPTIME_AI_RANKING_CALIBRATION_MARGIN": "0",
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

    def test_calibration_window_extends_to_near_boundary_candidates(self):
        rows = self._rows(24)

        def transport(payload):
            role = payload.get("role")
            candidates = payload["must_eligible_candidates"]
            if role == "OPTIME_NURSING_AI_CANDIDATE_SCORER":
                # FAC-01..FAC-20 score 1 point apart (80..99); FAC-21..FAC-23 sit within
                # the default 3-point margin of FAC-20's score (80); FAC-24 sits well
                # outside it. Only FAC-21..FAC-23 should be pulled into the window.
                scores = {f"FAC-{i:02d}": 100 - i for i in range(1, 21)}
                scores.update({"FAC-21": 79, "FAC-22": 78, "FAC-23": 77, "FAC-24": 50})
                return {
                    "scored_candidates": [
                        {"canonical_facility_id": item["canonical_facility_id"], "score": scores[item["canonical_facility_id"]], "reason": "batch score", "information_deficits": []}
                        for item in candidates
                    ]
                }
            supplied_ids = {item["canonical_facility_id"] for item in candidates}
            return {
                "ranked_candidates": [
                    {"canonical_facility_id": cid, "reason": "calibrated", "information_deficits": []}
                    for cid in sorted(supplied_ids)
                ]
            }

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_RANKING_BATCH_THRESHOLD": "20",
            "OPTIME_AI_RANKING_BATCH_SIZE": "6",
            "OPTIME_AI_RANKING_MAX_WORKERS": "2",
            "OPTIME_AI_RANKING_CALIBRATION_WINDOW": "20",
            "OPTIME_AI_RANKING_CALIBRATION_MARGIN": "3",
        }, clear=False), patch("app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        # Window extended from 20 to 23 (FAC-21/22/23 within margin of FAC-20's score 80;
        # FAC-24 at 50 is not), so exactly 23 rows carry the calibrated status.
        self.assertEqual(status["calibrated_top_candidate_count"], 23)
        self.assertTrue(all(row["ai_ranking"]["status"] == "AI_BATCH_SCORED_CALIBRATED" for row in ranked[:23]))
        self.assertEqual(ranked[23]["canonical_facility_id"], "FAC-24")
        self.assertEqual(ranked[23]["ai_ranking"]["status"], "AI_BATCH_SCORED")

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

    def test_single_shot_repairs_one_closed_world_omission(self):
        rows = self._rows(2)
        calls = []

        def transport(payload):
            calls.append(payload)
            candidates = payload["must_eligible_candidates"]
            if len(calls) == 1:
                candidates = candidates[:1]
            return {"ranked_candidates": [
                {"canonical_facility_id": item["canonical_facility_id"], "reason": "governed rank", "information_deficits": [], "rank_drivers": [], "rank_risks": []}
                for item in candidates
            ]}

        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport
        ):
            ranked, status = rank_must_eligible_candidates(
                rows, client_intent={}, human_context={"dynamic_preference_model": {"preferences": []}}, strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(2, len(calls))
        self.assertTrue(status["contract_repair_applied"])
        self.assertEqual(["FAC-01", "FAC-02"], [row["canonical_facility_id"] for row in ranked])
        self.assertEqual(["FAC-01", "FAC-02"], calls[1]["contract_repair"]["candidate_ids_required_exactly_once"])

    def test_fabricated_claim_citation_is_stripped_but_score_and_rank_are_kept(self):
        # rank_drivers/rank_risks are optional supporting detail ("may be empty"), so a
        # single fabricated claim_id is not grounds to discard the whole candidate's
        # score -- it is stripped and the candidate is marked citation_validation:
        # PARTIAL, distinct from a closed-world violation (wrong candidate set), which
        # is still a hard failure.
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

        self.assertEqual(status["status"], "AI_RANKED")
        self.assertEqual(ranked[0]["ai_ranking"]["status"], "AI_RANKED")
        self.assertEqual(ranked[0]["ai_ranking"]["rank_drivers"], [])
        self.assertEqual(ranked[0]["ai_ranking"]["citation_validation"], "PARTIAL")

    def test_required_single_shot_contract_failure_recovers_with_closed_world_batch_scoring(self):
        rows = self._rows(2)
        calls = []

        def transport(payload):
            calls.append(payload)
            candidates = payload["must_eligible_candidates"]
            if "ranked_candidates" in payload["required_output"]:
                first_id = candidates[0]["canonical_facility_id"]
                return {"ranked_candidates": [
                    {"canonical_facility_id": first_id, "reason": "duplicate", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
                    {"canonical_facility_id": first_id, "reason": "duplicate", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
                ]}
            return {"scored_candidates": [
                {
                    "canonical_facility_id": item["canonical_facility_id"],
                    "score": 90 - index,
                    "reason": "governed recovery score",
                    "information_deficits": [],
                    "rank_drivers": [],
                    "rank_risks": [],
                }
                for index, item in enumerate(candidates)
            ]}

        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1",
        }, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport
        ):
            ranked, status = rank_must_eligible_candidates(
                rows,
                client_intent={},
                human_context={"dynamic_preference_model": {"preferences": []}},
                strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual("AI_BATCH_RANKED_RECOVERY", status["status"])
        self.assertTrue(status["closed_world_validated"])
        self.assertEqual(["FAC-01", "FAC-02"], [row["canonical_facility_id"] for row in ranked])
        self.assertGreaterEqual(len(calls), 3)

    def test_single_shot_close_scores_are_resolved_by_the_governed_key_not_ai_order(self):
        # Reproduces the live production finding: two back-to-back calls with the same
        # 10-candidate set swapped the bottom two positions even at temperature=0,
        # because single-shot mode has no per-candidate score to stabilize on. Two
        # candidates scored 2 points apart (inside the default 3-point tie band) must
        # land in governed-key order regardless of which order the AI listed them in.
        rows = self._rows(2)

        def transport(payload):
            candidates = payload["must_eligible_candidates"]
            ids = [item["canonical_facility_id"] for item in candidates]
            # AI lists FAC-02 before FAC-01 and scores them within the tie band.
            return {"ranked_candidates": [
                {"canonical_facility_id": ids[1], "score": 41, "reason": "r2", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
                {"canonical_facility_id": ids[0], "score": 39, "reason": "r1", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
            ]}

        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport
        ):
            ranked, status = rank_must_eligible_candidates(
                rows, client_intent={}, human_context={"dynamic_preference_model": {"preferences": []}}, strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(status["status"], "AI_RANKED")
        # The governed key is alphabetical by ID here, so FAC-01 must lead despite the
        # AI listing FAC-02 first and scoring it higher.
        self.assertEqual(["FAC-01", "FAC-02"], [row["canonical_facility_id"] for row in ranked])
        self.assertEqual(ranked[0]["ai_ranking"]["global_score"], 39)

    def test_single_shot_well_separated_scores_keep_the_ai_order(self):
        # Candidates scored well outside the tie band are not close matches -- the
        # AI's own explicit ordering (which may reflect evidence a coarse governed key
        # cannot see) must not be overridden.
        rows = self._rows(2)

        def transport(payload):
            candidates = payload["must_eligible_candidates"]
            ids = [item["canonical_facility_id"] for item in candidates]
            return {"ranked_candidates": [
                {"canonical_facility_id": ids[1], "score": 90, "reason": "r2", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
                {"canonical_facility_id": ids[0], "score": 20, "reason": "r1", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
            ]}

        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport
        ):
            ranked, status = rank_must_eligible_candidates(
                rows, client_intent={}, human_context={"dynamic_preference_model": {"preferences": []}}, strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(["FAC-02", "FAC-01"], [row["canonical_facility_id"] for row in ranked])

    def test_single_shot_missing_scores_fall_back_to_ai_order_unchanged(self):
        # Older/partial responses without the score field must behave exactly as
        # before this fix -- no regression for a contract-repair pass that omits it.
        rows = self._rows(2)

        def transport(payload):
            candidates = payload["must_eligible_candidates"]
            ids = [item["canonical_facility_id"] for item in candidates]
            return {"ranked_candidates": [
                {"canonical_facility_id": ids[1], "reason": "r2", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
                {"canonical_facility_id": ids[0], "reason": "r1", "information_deficits": [], "rank_drivers": [], "rank_risks": []},
            ]}

        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", side_effect=transport
        ):
            ranked, status = rank_must_eligible_candidates(
                rows, client_intent={}, human_context={"dynamic_preference_model": {"preferences": []}}, strategy={},
                deterministic_fallback_key=lambda row: (str(row["canonical_facility_id"]),),
            )

        self.assertEqual(["FAC-02", "FAC-01"], [row["canonical_facility_id"] for row in ranked])
        self.assertNotIn("global_score", ranked[0]["ai_ranking"])

    def test_closed_world_violation_still_fails_closed_when_ranking_required(self):
        # Unlike a fabricated citation, a closed-world violation means the AI did not
        # return the exact supplied candidate set -- that is still a hard failure.
        rows = self._rows(1)

        def transport(payload):
            return {"ranked_candidates": []}

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
