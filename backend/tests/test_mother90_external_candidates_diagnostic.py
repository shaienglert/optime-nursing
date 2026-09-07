from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from app.services.patient_decision_engine import run_patient_decision_engine


class Mother90ExternalCandidateDiagnosticTests(unittest.TestCase):
    def test_medication_need_blocks_unverified_candidates_from_visible_ranking(self) -> None:
        state = {
            "relationship": "Mom",
            "ageGroup": "90+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 8000,
            "distanceFromFamily": "Balanced location",
            "humanIntelligenceV2": {
                "personalityProfile": {"communitySizePreference": "No preference"},
                "familyProfile": {"socialInteractionNeed": "Important"},
                "transitionRiskProfile": {"attitudeTowardMove": "Cautious but open"},
                "scoringEngine": {"adaptiveSignals": []},
            },
        }
        query = (
            "My mother is 90 and we are looking across the Las Vegas Valley. She is mentally alert, "
            "has no dementia, is mobile, but needs daily help with bathing, dressing and medication. "
            "She would like a friendly social environment and we want the least restrictive safe setting."
        )
        ready_ai = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(os.environ, {
            "OPTIME_SEMANTIC_AI_ENABLED": "1",
            "OPTIME_SEMANTIC_AI_REQUIRED": "1",
            "OPTIME_AI_CANDIDATE_RANKING_REQUIRED": "0",
        }, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ready_ai
        ):
            result = run_patient_decision_engine(state, query, limit=500)

        decision = result.get("decision_intelligence") or {}
        pending = result.get("must_pending_verification_candidates") or []
        diagnostics = {
            "visible_recommendation_count": result.get("result_count"),
            "recommendation_execution_allowed": decision.get("recommendation_execution_allowed"),
            "recommendation_visibility": decision.get("recommendation_visibility"),
            "must_eligible_count": result.get("must_eligible_count"),
            "must_pending_verification_count": result.get("must_pending_verification_count"),
            "pending_sample": pending[:10],
            "total_candidates_scored": result.get("total_candidates_scored"),
        }
        print("MOTHER90_MEDICATION_MUST_DIAGNOSTIC=" + json.dumps(diagnostics, indent=2, default=str))

        # What this test is named for still holds: no candidate whose medication support is
        # unverified reaches the visible list. What changed is the other half. Five
        # communities did verify it, and with the ranking model unavailable those five are
        # shown as an unordered set rather than withheld -- a family whose mother needs
        # daily medication is better served by five confirmed options than by a blank page.
        shown = result.get("results") or []
        self.assertTrue(shown, "verified candidates should survive a degraded run")
        for row in shown:
            self.assertEqual("MUST_ELIGIBLE", row.get("must_eligibility"))
            self.assertEqual([], (row.get("client_intent_fit") or {}).get("must_unknown") or [])
        self.assertEqual(len(shown), result.get("result_count"))
        self.assertTrue(decision.get("canonical_decision_state", {}).get("is_degraded_result"))
        self.assertFalse(result["degraded_result_notice"]["results_are_ordered"])
        self.assertTrue(pending)
        self.assertGreater(result.get("must_pending_verification_count") or 0, 0)
        self.assertTrue(
            all("MEDICATION_SUPPORT_AVAILABLE" in (item.get("must_unknown") or []) for item in pending),
            "Every medication-dependent candidate without governed medication evidence must remain pending.",
        )


if __name__ == "__main__":
    unittest.main()
