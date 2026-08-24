from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.ai_candidate_ranking_runtime import rank_must_eligible_candidates
from app.services.must_ai_nice_pipeline import apply_must_ai_nice_pipeline


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

    def test_only_must_pass_enters_ai_ranking_and_legacy_nice_is_not_authoritative(self):
        packet = {
            "ranked_candidates": [
                {"canonical_facility_id": "B", "reason": "overall evidence", "information_deficits": []},
                {"canonical_facility_id": "A", "reason": "overall evidence", "information_deficits": []},
            ]
        }
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "1"}, clear=False), patch(
            "app.services.ai_candidate_ranking_runtime._default_transport", return_value=packet
        ):
            result = apply_must_ai_nice_pipeline(self._result(), {}, "", 5)

        self.assertEqual([r["canonical_facility_id"] for r in result["results"]], ["B", "A"])
        self.assertEqual(result["must_eligible_count"], 2)
        self.assertEqual(result["must_pending_verification_count"], 1)
        self.assertEqual(result["must_rejected_count"], 1)
        self.assertEqual(result["results"][0]["must_eligibility"], "MUST_ELIGIBLE")
        self.assertEqual(result["results"][0]["nice_to_have_coverage"]["status"], "NO_EXPLICIT_DYNAMIC_NICE")
        self.assertEqual(result["results"][1]["nice_to_have_coverage"]["status"], "NO_EXPLICIT_DYNAMIC_NICE")
        self.assertEqual(result["results"][0]["legacy_structured_nice_fit"]["nice_unknown"], ["SOCIAL"])
        self.assertEqual(result["results"][1]["legacy_structured_nice_fit"]["nice_match"], ["SOCIAL"])
        pipeline = result["decision_intelligence"]["facility_selection_pipeline"]
        self.assertEqual(pipeline["ai_ranking"]["status"], "AI_RANKED")
        self.assertFalse(pipeline["legacy_structured_nice_authoritative"])
        self.assertEqual(result["decision_intelligence"]["ranking_order"][0], "DETERMINISTIC_MUST_GATE")

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


if __name__ == "__main__":
    unittest.main()
