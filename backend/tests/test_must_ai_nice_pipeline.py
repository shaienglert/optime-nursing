from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.ai_candidate_ranking_runtime import rank_must_eligible_candidates
from app.services.must_ai_nice_pipeline import apply_must_ai_nice_pipeline, _has_differentiating_evidence


def _row(cid: str, gate: str, nice_match=None, nice_unknown=None, grade="A"):
    return {
        "canonical_facility_id": cid,
        "facility_name": cid,
        "canonical_type": "ASSISTED_LIVING_RFG",
        "care_setting_fit": {"status": "PRIMARY_FIT"},
        "client_intent_fit": {
            "hard_gate": gate,
            "must_pass": ["LAS_VEGAS", "ADL_SUPPORT_AVAILABLE"] if gate == "PASS" else [],
            "must_unknown": ["ADL_SUPPORT_AVAILABLE"] if gate == "PENDING_VERIFICATION" else [],
            "must_fail": ["ADL_SUPPORT_AVAILABLE"] if gate == "FAIL" else [],
            "nice_match": nice_match or [],
            "nice_unknown": nice_unknown or [],
            "nice_fit_scores": {},
            "public_reputation": {"rating": "UNKNOWN", "review_count": "UNKNOWN"},
            "relevant_evidence_known_count": 3,
            "relevant_evidence_unknown_count": 1,
        },
        "regulatory_history": {"latest_known_grade": grade, "disciplinary_action": "N", "grade_counts": {grade: 1}},
    }


def _thin_row(cid: str, gate: str = "PASS"):
    """A row with no NICE match/unknown, no known rating/review count, no known
    regulatory grade, and no confirmed disciplinary action -- nothing for AI-blended
    judgment to differentiate on."""
    row = _row(cid, gate, grade=None)
    row["regulatory_history"]["disciplinary_action"] = "N"
    return row


class MustAiNicePipelineTests(unittest.TestCase):
    def _result(self):
        return {
            "results": [
                _row("A", "PASS", ["SOCIAL"], []),
                _row("B", "PASS", [], ["SOCIAL"]),
                _row("C", "PENDING_VERIFICATION", ["SOCIAL"], []),
                _row("D", "FAIL", ["SOCIAL"], []),
            ],
            "decision_intelligence": {
                "client_intent": {"nice_to_haves": [{"key": "SOCIAL"}]},
                "human_intelligence": {},
                "living_strategy": {},
                "must_gate": {},
            },
        }

    def test_must_pass_and_must_pending_both_enter_ai_ranking_and_legacy_nice_is_not_authoritative(self):
        # A, B are MUST_ELIGIBLE; C is MUST_PENDING_VERIFICATION (still ranked, not
        # excluded); D is MUST_REJECTED (a real MUST failure -- correctly excluded).
        packet = {
            "ranked_candidates": [
                {"canonical_facility_id": "B", "reason": "overall evidence", "information_deficits": []},
                {"canonical_facility_id": "C", "reason": "overall evidence", "information_deficits": []},
                {"canonical_facility_id": "A", "reason": "overall evidence", "information_deficits": []},
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", return_value=packet
        ):
            result = apply_must_ai_nice_pipeline(self._result(), {}, "", 5)

        self.assertEqual([r["canonical_facility_id"] for r in result["results"]], ["B", "C", "A"])
        self.assertEqual(result["must_eligible_count"], 2)
        self.assertEqual(result["must_pending_verification_count"], 1)
        self.assertEqual(result["must_rejected_count"], 1)
        self.assertEqual(result["results"][0]["must_eligibility"], "MUST_ELIGIBLE")
        self.assertEqual(result["results"][0]["nice_to_have_coverage"]["status"], "NO_EXPLICIT_DYNAMIC_NICE")
        self.assertEqual(result["results"][2]["nice_to_have_coverage"]["status"], "NO_EXPLICIT_DYNAMIC_NICE")
        self.assertEqual(result["results"][0]["legacy_structured_nice_fit"]["nice_unknown"], ["SOCIAL"])
        self.assertEqual(result["results"][2]["legacy_structured_nice_fit"]["nice_match"], ["SOCIAL"])
        pipeline = result["decision_intelligence"]["facility_selection_pipeline"]
        self.assertEqual(pipeline["ai_ranking"]["status"], "AI_RANKED")
        self.assertFalse(pipeline["legacy_structured_nice_authoritative"])
        self.assertEqual(result["decision_intelligence"]["ranking_order"][0], "DETERMINISTIC_MUST_GATE")

        # C is MUST_PENDING_VERIFICATION: shown, not excluded, with an explicit note
        # of what remains unverified and a promise it can only hold or improve rank.
        pending_row = result["results"][1]
        self.assertEqual(pending_row["canonical_facility_id"], "C")
        self.assertEqual(pending_row["must_eligibility"], "MUST_PENDING_VERIFICATION")
        note = pending_row["provisional_ranking_note"]
        self.assertEqual(note["status"], "MUST_VERIFICATION_PENDING")
        self.assertEqual(note["still_unverified"], ["ADL_SUPPORT_AVAILABLE"])
        self.assertIn("never get worse", note["statement"])
        self.assertNotIn("provisional_ranking_note", result["results"][0])
        self.assertNotIn("provisional_ranking_note", result["results"][2])

    def test_ai_cannot_introduce_or_drop_must_eligible_candidate(self):
        rows = [_row("A", "PASS"), _row("B", "PASS")]
        bad = {"ranked_candidates": [{"canonical_facility_id": "A", "reason": "x", "information_deficits": []}, {"canonical_facility_id": "X", "reason": "x", "information_deficits": []}]}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", return_value=bad
        ):
            with self.assertRaisesRegex(RuntimeError, "AI_CANDIDATE_RANKING_REQUIRED_FAILED"):
                rank_must_eligible_candidates(rows, {}, {}, {}, lambda row: (row["canonical_facility_id"],))

    def test_top_n_is_cut_after_ai_ordering(self):
        rows = [_row("A", "PASS"), _row("B", "PASS"), _row("C", "PASS")]
        result = {"results": rows, "decision_intelligence": {"client_intent": {"nice_to_haves": []}, "human_intelligence": {}, "living_strategy": {}}}
        packet = {"ranked_candidates": [
            {"canonical_facility_id": "C", "reason": "first", "information_deficits": []},
            {"canonical_facility_id": "B", "reason": "second", "information_deficits": []},
            {"canonical_facility_id": "A", "reason": "third", "information_deficits": []},
        ]}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", return_value=packet
        ):
            out = apply_must_ai_nice_pipeline(result, {}, "", 2)
        self.assertEqual([r["canonical_facility_id"] for r in out["results"]], ["C", "B"])
        self.assertEqual(out["must_eligible_count"], 3)

    def test_ai_ranking_failure_never_turns_verified_candidates_into_zero_results(self):
        rows = [_row("A", "PASS"), _row("B", "PASS"), _row("C", "PENDING_VERIFICATION")]
        result = {"results": rows, "decision_intelligence": {"client_intent": {"nice_to_haves": []}, "human_intelligence": {}, "living_strategy": {}}}
        failed_status = {"status": "AI_RANKING_ERROR", "error": "temporary model failure"}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"}, clear=False), patch(
            "app.services.must_ai_nice_pipeline.rank_must_eligible_candidates",
            return_value=(rows, failed_status),
        ):
            out = apply_must_ai_nice_pipeline(result, {}, "", 5)
        self.assertEqual(3, out["result_count"])
        self.assertEqual(["A", "B", "C"], [row["canonical_facility_id"] for row in out["results"]])
        pipeline = out["decision_intelligence"]["facility_selection_pipeline"]
        self.assertTrue(pipeline["ai_ranking_degraded"])
        self.assertFalse(pipeline["ai_ranking_fail_closed"])
        self.assertTrue(out["decision_intelligence"]["ai_ranking_failure"]["deterministic_order_exposed"])

    def test_zero_eligible_but_pending_candidates_are_still_ranked_and_shown(self):
        # No candidate has fully passed MUST yet, but two have unresolved (not
        # failed) evidence -- these must not be dropped to an empty shortlist.
        rows = [_row("E", "PENDING_VERIFICATION"), _row("F", "PENDING_VERIFICATION")]
        result = {"results": rows, "decision_intelligence": {"client_intent": {"nice_to_haves": []}, "human_intelligence": {}, "living_strategy": {}}}
        packet = {"ranked_candidates": [
            {"canonical_facility_id": "F", "reason": "first", "information_deficits": []},
            {"canonical_facility_id": "E", "reason": "second", "information_deficits": []},
        ]}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", return_value=packet
        ):
            out = apply_must_ai_nice_pipeline(result, {}, "", 5)

        self.assertEqual(out["must_eligible_count"], 0)
        self.assertEqual(out["must_pending_verification_count"], 2)
        self.assertEqual([r["canonical_facility_id"] for r in out["results"]], ["F", "E"])
        self.assertEqual(out["result_count"], 2)
        for row in out["results"]:
            self.assertEqual(row["must_eligibility"], "MUST_PENDING_VERIFICATION")
            self.assertIn("provisional_ranking_note", row)
        self.assertIn("still have at least one MUST requirement pending", out["decision_intelligence"]["facility_selection_pipeline"]["client_statement"])

    def test_live_search_ai_is_bounded_to_the_display_shortlist(self):
        rows = [_row(f"F-{index:02d}", "PASS") for index in range(15)]
        result = {
            "results": rows,
            "decision_intelligence": {
                "client_intent": {"nice_to_haves": []},
                "human_intelligence": {},
                "living_strategy": {},
            },
        }
        captured = []

        def rank_shortlist(candidate_rows, **_kwargs):
            captured.extend(row["canonical_facility_id"] for row in candidate_rows)
            return list(reversed(candidate_rows)), {"status": "AI_RANKED"}

        with patch("app.services.must_ai_nice_pipeline.rank_must_eligible_candidates", side_effect=rank_shortlist):
            out = apply_must_ai_nice_pipeline(result, {}, "", 50)

        self.assertEqual(len(captured), 10)
        self.assertEqual(out["result_count"], 10)
        pipeline = out["decision_intelligence"]["facility_selection_pipeline"]
        self.assertEqual(pipeline["full_rankable_candidate_count"], 15)
        self.assertEqual(pipeline["interactive_shortlist_limit"], 10)
        self.assertEqual(pipeline["ranking_scope"], "LIVE_SHORTLIST_ONLY_FULL_UNIVERSE_RESEARCH_CONTINUES")

    def test_rank_group_key_groups_by_ai_global_score_when_present(self):
        # ai_ranking.global_score (set by the batched-scoring path -- see
        # ai_candidate_ranking_runtime._batch_ai_rank) is the real signal two rows
        # must share to be a genuine tie in an AI-ranked result: the deterministic
        # fallback key is only ever consulted as *its* tiebreaker, not the client-
        # visible ranking driver, so it must not itself define what counts as a tie
        # once an AI score exists.
        from app.services.must_ai_nice_pipeline import _rank_group_key

        row_a = _row("A", "PASS")
        row_a["ai_ranking"] = {"status": "AI_BATCH_SCORED", "global_score": 70.0}
        row_b = _row("B", "PASS", grade="D")  # deliberately different deterministic key
        row_b["ai_ranking"] = {"status": "AI_BATCH_SCORED", "global_score": 70.0}
        row_c = _row("C", "PASS")
        row_c["ai_ranking"] = {"status": "AI_BATCH_SCORED", "global_score": 55.0}

        self.assertEqual(_rank_group_key(row_a), _rank_group_key(row_b))
        self.assertNotEqual(_rank_group_key(row_a), _rank_group_key(row_c))

    def test_rank_group_key_falls_back_to_deterministic_key_without_an_ai_score(self):
        from app.services.must_ai_nice_pipeline import _rank_group_key

        identical_a = _row("A", "PASS")
        identical_b = _row("B", "PASS")  # same grade/rating/evidence as A, different name only
        different = _row("C", "PASS", grade="D")

        self.assertEqual(_rank_group_key(identical_a), _rank_group_key(identical_b))
        self.assertNotEqual(_rank_group_key(identical_a), _rank_group_key(different))

    def test_deterministic_fallback_rows_that_differ_only_by_name_are_reported_as_joint_rank(self):
        # AI disabled entirely -> pure deterministic fallback path (no ai_ranking
        # global_score at all). Two rows identical on every real ranking signal
        # should still be recognized as tied, not hidden behind the alphabetical
        # tiebreaker that only exists to make sort() deterministic.
        rows = [_row("A", "PASS"), _row("B", "PASS")]
        result = {"results": rows, "decision_intelligence": {"client_intent": {"nice_to_haves": []}, "human_intelligence": {}, "living_strategy": {}}}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "0"}, clear=False):
            out = apply_must_ai_nice_pipeline(result, {}, "", 5)

        for row in out["results"]:
            self.assertEqual(row["ai_ranking"]["status"], "DETERMINISTIC_FALLBACK")
            self.assertNotIn("global_score", row["ai_ranking"])
            self.assertEqual(row["rank_tie_status"], "JOINT_RANK")
        self.assertEqual(set(out["results"][0]["tied_with"] + out["results"][1]["tied_with"]), {"A", "B"})


class DeterministicWaterfallThinEvidenceTests(unittest.TestCase):
    def test_has_differentiating_evidence_is_false_for_a_wholly_thin_pool(self):
        rows = [_thin_row("A"), _thin_row("B"), _thin_row("C")]
        self.assertFalse(_has_differentiating_evidence(rows, {"preference_count": 0}))

    def test_has_differentiating_evidence_is_true_with_nice_preferences(self):
        rows = [_thin_row("A"), _thin_row("B")]
        self.assertTrue(_has_differentiating_evidence(rows, {"preference_count": 2}))

    def test_has_differentiating_evidence_is_true_if_any_row_has_a_known_rating(self):
        rows = [_thin_row("A"), _thin_row("B")]
        rows[1]["client_intent_fit"]["public_reputation"]["rating"] = 3.5
        self.assertTrue(_has_differentiating_evidence(rows, {"preference_count": 0}))

    def test_has_differentiating_evidence_is_true_if_any_row_has_a_known_grade(self):
        rows = [_thin_row("A"), _row("B", "PASS", grade="C")]
        self.assertTrue(_has_differentiating_evidence(rows, {"preference_count": 0}))

    def test_has_differentiating_evidence_is_true_with_confirmed_disciplinary_action(self):
        rows = [_thin_row("A")]
        rows[0]["regulatory_history"]["disciplinary_action"] = "Y"
        self.assertTrue(_has_differentiating_evidence(rows, {"preference_count": 0}))

    def test_thin_evidence_pool_skips_ai_and_uses_the_deterministic_waterfall(self):
        rows = [_thin_row("A"), _thin_row("B"), _thin_row("C")]
        result = {"results": rows, "decision_intelligence": {"client_intent": {"nice_to_haves": []}, "human_intelligence": {}, "living_strategy": {}}}
        with patch.dict(
            os.environ,
            {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"},
            clear=False,
        ), patch("app.services.must_ai_nice_pipeline.rank_must_eligible_candidates") as mock_rank:
            out = apply_must_ai_nice_pipeline(result, {}, "", 5)

        mock_rank.assert_not_called()
        self.assertEqual(out["result_count"], 3)
        for row in out["results"]:
            self.assertEqual(row["ai_ranking"]["status"], "DETERMINISTIC_THIN_EVIDENCE_WATERFALL")
        pipeline = out["decision_intelligence"]["facility_selection_pipeline"]
        self.assertEqual(pipeline["ai_ranking"]["status"], "DETERMINISTIC_THIN_EVIDENCE_WATERFALL")
        self.assertNotIn("ai_ranking_failure", out["decision_intelligence"])

    def test_one_facility_with_a_known_rating_is_enough_to_call_ai_for_the_whole_pool(self):
        rows = [_thin_row("A"), _thin_row("B")]
        rows[1]["client_intent_fit"]["public_reputation"]["rating"] = 4.2
        result = {"results": rows, "decision_intelligence": {"client_intent": {"nice_to_haves": []}, "human_intelligence": {}, "living_strategy": {}}}
        packet = {"ranked_candidates": [
            {"canonical_facility_id": "B", "reason": "x", "information_deficits": []},
            {"canonical_facility_id": "A", "reason": "x", "information_deficits": []},
        ]}
        with patch.dict(
            os.environ,
            {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"},
            clear=False,
        ), patch("app.services.ai_candidate_ranking_runtime._default_transport", return_value=packet):
            out = apply_must_ai_nice_pipeline(result, {}, "", 5)

        self.assertEqual([r["canonical_facility_id"] for r in out["results"]], ["B", "A"])
        self.assertEqual(out["results"][0]["ai_ranking"]["status"], "AI_RANKED")


if __name__ == "__main__":
    unittest.main()
