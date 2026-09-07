from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401 -- registers every model so create_all resolves all FKs
from app.database import Base
from app.models.deferred_report import DeferredDecisionReport, DeferredReportStatus
from app.services.canonical_decision_state import (
    DecisionFinality,
    apply_canonical_decision_state_authority,
    DecisionPhase,
    RankingState,
    derive_canonical_decision_state,
)
from app.services.decision_pipeline_trace import attach_decision_pipeline_trace
from app.services.degraded_result_notice import build_degraded_notice
from app.services.deferred_report_service import (
    MAX_ATTEMPTS,
    process_pending_reports,
    request_deferred_report,
)


def _payload(ranking_status: str, *, eligible: int = 12, pending: int = 0, results: int = 0) -> dict:
    return {
        "results": [{"facility_name": f"Community {i}"} for i in range(results)],
        "must_eligible_count": eligible,
        "must_pending_verification_count": pending,
        "must_rejected_count": 3,
        "total_candidates_scored": eligible + pending + 3,
        "decision_intelligence": {
            "recommendation_execution_allowed": False,
            "recommendation_visibility": "UNKNOWN",
            "decision_finality": "UNKNOWN",
            "human_intelligence": {"decision_readiness": "READY"},
            "facility_selection_pipeline": {
                "ai_ranking": {"status": ranking_status, "fallback_reason": "AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION"},
            },
        },
    }


class DegradedStateTests(unittest.TestCase):
    """Hard criteria carried the result; the model did not run."""

    def test_unavailable_model_yields_a_shown_but_unordered_set(self) -> None:
        state = derive_canonical_decision_state(_payload("DETERMINISTIC_FALLBACK"))
        self.assertIs(state.phase, DecisionPhase.UNRANKED_ELIGIBLE_SET)
        self.assertIs(state.ranking, RankingState.UNAVAILABLE_HARD_CRITERIA_ONLY)
        self.assertIs(state.finality, DecisionFinality.DEGRADED_UNRANKED)
        self.assertTrue(state.can_show_recommendations)
        self.assertTrue(state.is_degraded_result)

    def test_a_degraded_result_is_never_final_or_provisional(self) -> None:
        # PROVISIONAL means ranked and awaiting verification. Reusing it here would let a
        # degraded answer be read as an ordinary one that just needs confirming.
        state = derive_canonical_decision_state(_payload("DETERMINISTIC_FALLBACK"))
        self.assertNotIn(state.finality, {DecisionFinality.FINAL, DecisionFinality.PROVISIONAL})

    def test_required_but_unavailable_degrades_the_same_way(self) -> None:
        state = derive_canonical_decision_state(_payload("REQUIRED_BUT_UNAVAILABLE"))
        self.assertIs(state.phase, DecisionPhase.UNRANKED_ELIGIBLE_SET)
        self.assertTrue(state.can_show_recommendations)

    def test_nothing_verified_means_nothing_to_show(self) -> None:
        # Every candidate unverified: there is no hard-criteria result to fall back on, so
        # a family who needs medication support is not sent to communities whose ability to
        # provide it is merely unknown.
        state = derive_canonical_decision_state(_payload("DETERMINISTIC_FALLBACK", eligible=0, pending=9))
        self.assertIsNot(state.phase, DecisionPhase.UNRANKED_ELIGIBLE_SET)
        self.assertFalse(state.can_show_recommendations)

    def test_a_mixed_set_shows_the_verified_and_withholds_the_rest(self) -> None:
        # Requiring pending==0 was too blunt: an ADL search with 350 eligible and 24
        # unverified hid all 350. The 24 are dropped from the list, not the other 350.
        payload = _payload("DETERMINISTIC_FALLBACK", eligible=12, pending=3)
        payload["results"] = [
            {"facility_name": "verified", "must_eligibility": "MUST_ELIGIBLE"},
            {"facility_name": "unverified", "must_eligibility": "MUST_PENDING_VERIFICATION"},
        ]
        state = derive_canonical_decision_state(payload)
        self.assertIs(state.phase, DecisionPhase.UNRANKED_ELIGIBLE_SET)

        apply_canonical_decision_state_authority(payload)
        shown = [row["facility_name"] for row in payload["results"]]
        self.assertEqual(shown, ["verified"])
        self.assertEqual(payload["result_count"], 1)

    def test_a_real_ranking_is_unaffected(self) -> None:
        state = derive_canonical_decision_state(_payload("AI_BATCH_RANKED"))
        self.assertFalse(state.is_degraded_result)
        self.assertIn(state.phase, {DecisionPhase.PROVISIONAL_RECOMMENDATION, DecisionPhase.FINAL_RECOMMENDATION})

    def test_a_genuine_ranking_failure_still_blocks(self) -> None:
        state = derive_canonical_decision_state(_payload("AI_RANKING_ERROR"))
        self.assertIs(state.ranking, RankingState.FAILED)
        self.assertFalse(state.can_show_recommendations)

    def test_no_eligible_candidates_is_not_a_degraded_result(self) -> None:
        state = derive_canonical_decision_state(_payload("DETERMINISTIC_FALLBACK", eligible=0, pending=0))
        self.assertFalse(state.is_degraded_result)


class DegradedNoticeTests(unittest.TestCase):
    def test_the_notice_states_the_list_is_unordered(self) -> None:
        result = _payload("DETERMINISTIC_FALLBACK", results=5)
        result["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(result).to_dict()
        notice = build_degraded_notice(result)

        self.assertIsNotNone(notice)
        self.assertFalse(notice["results_are_ordered"])
        self.assertTrue(notice["governance"]["noCandidateIsRecommendedOverAnother"])
        self.assertEqual(notice["what_ran"], "HARD_CRITERIA_ONLY")
        self.assertEqual(notice["eligible_candidates"], 12)
        self.assertEqual(notice["shown_candidates"], 5)

    def test_the_notice_offers_retry_wait_and_email(self) -> None:
        result = _payload("DETERMINISTIC_FALLBACK", results=5)
        result["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(result).to_dict()
        actions = {a["action"] for a in build_degraded_notice(result)["recovery_actions"]}
        self.assertEqual(actions, {"RETRY_NOW", "RETRY_LATER", "EMAIL_REPORT_WHEN_READY"})

    def test_an_ordinary_result_carries_no_notice_at_all(self) -> None:
        # Absent, not present-and-false: a caller that forgets the flag should find nothing
        # to render rather than a notice quietly claiming all is well.
        result = _payload("AI_BATCH_RANKED", results=5)
        result["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(result).to_dict()
        self.assertIsNone(build_degraded_notice(result))
        attach_decision_pipeline_trace(result)
        self.assertNotIn("degraded_result_notice", result)

    def test_the_trace_names_the_degraded_outcome_distinctly(self) -> None:
        result = _payload("DETERMINISTIC_FALLBACK", results=5)
        result["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(result).to_dict()
        attach_decision_pipeline_trace(result)
        self.assertEqual(result["decision_pipeline_trace"]["outcome"], "VISIBLE_UNRANKED_ELIGIBLE_SET")
        self.assertIn("degraded_result_notice", result)


class DeferredReportTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.questionnaire = {"relationship": "My mother", "budget": 8000, "locationCity": "Las Vegas"}
        self.query = "My mother is 82 in Las Vegas, fully independent, budget $8,000."

    def _request(self, email: str = "family@example.com") -> dict:
        return request_deferred_report(
            self.db, email=email, questionnaire=self.questionnaire, query_text=self.query,
            market="las-vegas", degraded_reason="AI_BATCHED_RANKING_CLOSED_WORLD_VIOLATION",
            eligible_at_request=374,
        )

    def test_a_request_stores_everything_needed_to_reproduce_the_search(self) -> None:
        out = self._request()
        self.assertTrue(out["created"])
        row = self.db.query(DeferredDecisionReport).one()
        self.assertEqual(row.email, "family@example.com")
        self.assertEqual(json.loads(row.questionnaire_json), self.questionnaire)
        self.assertEqual(row.query_text, self.query)
        self.assertEqual(row.market, "las-vegas")
        self.assertEqual(row.eligible_at_request, 374)
        self.assertIs(row.status, DeferredReportStatus.PENDING)

    def test_pressing_the_button_twice_is_asking_once(self) -> None:
        first = self._request()
        second = self._request()
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["request_id"], second["request_id"])
        self.assertEqual(self.db.query(DeferredDecisionReport).count(), 1)

    def test_an_undeliverable_address_is_refused(self) -> None:
        for bad in ("", "   ", "not-an-email", "a@b", "two words@example.com"):
            with self.assertRaises(ValueError):
                request_deferred_report(self.db, email=bad, questionnaire={}, query_text=self.query)

    def test_a_search_with_no_text_cannot_be_reproduced_so_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            request_deferred_report(self.db, email="a@example.com", questionnaire={}, query_text="   ")

    def test_a_retry_that_degrades_again_sends_nothing(self) -> None:
        self._request()
        degraded = _payload("DETERMINISTIC_FALLBACK", results=5)
        degraded["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(degraded).to_dict()

        with patch("app.services.patient_decision_engine.run_patient_decision_engine", return_value=degraded), \
             patch("app.services.email_service.send_email_detailed") as mail:
            outcome = process_pending_reports(self.db)

        mail.assert_not_called()
        self.assertEqual(outcome["still_degraded"], 1)
        self.assertEqual(outcome["sent"], 0)
        self.assertIs(self.db.query(DeferredDecisionReport).one().status, DeferredReportStatus.PENDING)

    def test_a_ranked_retry_is_delivered_once(self) -> None:
        self._request()
        ranked = _payload("AI_BATCH_RANKED", results=3)
        ranked["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(ranked).to_dict()

        class Sent:
            success = True
            error = None

        with patch("app.services.patient_decision_engine.run_patient_decision_engine", return_value=ranked), \
             patch("app.services.email_service.send_email_detailed", return_value=Sent()) as mail:
            outcome = process_pending_reports(self.db)
            self.assertEqual(outcome["sent"], 1)
            row = self.db.query(DeferredDecisionReport).one()
            self.assertIs(row.status, DeferredReportStatus.SENT)
            self.assertIsNotNone(row.delivered_at)
            self.assertEqual(mail.call_args.kwargs["recipients"], ["family@example.com"])
            self.assertIn("ready", mail.call_args.kwargs["subject"].lower())

            # A sent row is done; a second sweep must not mail the family again.
            again = process_pending_reports(self.db)
            self.assertEqual(again["sent"], 0)
            self.assertEqual(mail.call_count, 1)

    def test_a_failed_send_leaves_the_request_recoverable(self) -> None:
        self._request()
        ranked = _payload("AI_BATCH_RANKED", results=3)
        ranked["decision_intelligence"]["canonical_decision_state"] = derive_canonical_decision_state(ranked).to_dict()

        class Failed:
            success = False
            error = "SMTP host is not configured"

        with patch("app.services.patient_decision_engine.run_patient_decision_engine", return_value=ranked), \
             patch("app.services.email_service.send_email_detailed", return_value=Failed()):
            outcome = process_pending_reports(self.db)

        self.assertEqual(outcome["failed"], 1)
        row = self.db.query(DeferredDecisionReport).one()
        self.assertIs(row.status, DeferredReportStatus.PENDING)
        self.assertIn("SMTP", row.last_error)

    def test_an_engine_crash_does_not_lose_the_request(self) -> None:
        self._request()
        with patch("app.services.patient_decision_engine.run_patient_decision_engine", side_effect=RuntimeError("boom")):
            outcome = process_pending_reports(self.db)
        self.assertEqual(outcome["failed"], 1)
        row = self.db.query(DeferredDecisionReport).one()
        self.assertIs(row.status, DeferredReportStatus.PENDING)
        self.assertIn("RuntimeError", row.last_error)

    def test_a_stale_request_is_abandoned_rather_than_retried_forever(self) -> None:
        self._request()
        row = self.db.query(DeferredDecisionReport).one()
        row.requested_at = datetime.now(timezone.utc) - timedelta(days=30)
        self.db.commit()

        with patch("app.services.email_service.send_email_detailed") as mail:
            outcome = process_pending_reports(self.db)

        mail.assert_not_called()
        self.assertEqual(outcome["abandoned"], 1)
        self.assertIs(self.db.query(DeferredDecisionReport).one().status, DeferredReportStatus.ABANDONED)

    def test_a_request_retried_too_many_times_is_abandoned(self) -> None:
        self._request()
        row = self.db.query(DeferredDecisionReport).one()
        row.attempts = MAX_ATTEMPTS
        self.db.commit()
        outcome = process_pending_reports(self.db)
        self.assertEqual(outcome["abandoned"], 1)


if __name__ == "__main__":
    unittest.main()
