from __future__ import annotations

import unittest
from unittest.mock import patch

from app.database import Base, SessionLocal, engine
import app.models.competitive_intelligence  # noqa: F401 -- registers tables on Base
from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
from app.models.competitive_intelligence import CompetitiveIntelligenceSignal
from app.services.competitive_intelligence_service import (
    AGENT_KEY,
    COMPETITORS,
    extract_signals,
    run_competitive_intelligence_cycle,
)

Base.metadata.create_all(bind=engine)

_SAMPLE_HTML = """
<html><head><title>Find Senior Living | Example Co</title></head>
<body>
<h1>Find the right senior living community, at no cost to your family</h1>
<p>Example Co partners with 60,000 senior living communities nationwide.
We are compensated by our partner communities when you move in.</p>
<p>Compare communities, see pricing, view photos, and schedule a tour today.</p>
<p>Over 375,000 reviews from real families.</p>
</body></html>
"""

_SAMPLE_HTML_EMPTY = "<html><head><title></title></head><body><p>Coming soon.</p></body></html>"


def _db():
    return SessionLocal()


class ExtractSignalsTests(unittest.TestCase):
    def test_extracts_headline_monetization_features_and_scale(self) -> None:
        signals = extract_signals(_SAMPLE_HTML)
        by_type = {s.signal_type: s.detail_text for s in signals}

        self.assertIn("positioning_headline", by_type)
        self.assertIn("no cost", by_type["positioning_headline"].lower())

        self.assertIn("monetization_language", by_type)
        self.assertTrue(
            "compensated" in by_type["monetization_language"].lower()
            or "at no cost" in by_type["monetization_language"].lower()
        )

        self.assertIn("feature_mentions", by_type)
        for keyword in ("compare", "pricing", "photos", "schedule a tour"):
            self.assertIn(keyword, by_type["feature_mentions"])

        self.assertIn("scale_claims", by_type)
        self.assertTrue(any("60,000" in entry for entry in by_type["scale_claims"].split("; ")))

    def test_empty_page_yields_only_whatever_is_actually_present(self) -> None:
        signals = extract_signals(_SAMPLE_HTML_EMPTY)
        types = {s.signal_type for s in signals}
        # No fabricated signals for content that isn't there.
        self.assertNotIn("monetization_language", types)
        self.assertNotIn("feature_mentions", types)
        self.assertNotIn("scale_claims", types)


class RunCycleTests(unittest.TestCase):
    def tearDown(self) -> None:
        db = _db()
        try:
            db.query(CompetitiveIntelligenceSignal).delete()
            db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).delete()
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).delete()
            db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).delete()
            db.commit()
        finally:
            db.close()

    def test_first_run_creates_new_signals_and_registers_the_agent(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.competitive_intelligence_service._fetch",
                return_value=(_SAMPLE_HTML, 200),
            ) as mock_fetch:
                result = run_competitive_intelligence_cycle(db)

            self.assertEqual(mock_fetch.call_count, len(COMPETITORS))
            self.assertEqual(result["errors"], 0)
            self.assertGreater(result["items_added"], 0)
            self.assertEqual(result["items_updated"], 0)

            signals = db.query(CompetitiveIntelligenceSignal).all()
            self.assertEqual(len(signals), len(COMPETITORS) * 4)  # headline, monetization, features, scale

            job = db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).order_by(AgentJobRun.id.desc()).first()
            self.assertIsNotNone(job)
            self.assertEqual(job.status, "SUCCESS")

            worker = db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).first()
            self.assertIsNotNone(worker)
            self.assertIsNotNone(worker.last_run)

            knowledge = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).all()
            self.assertEqual(len(knowledge), 1)
        finally:
            db.close()

    def test_second_identical_run_reports_unchanged_not_new(self) -> None:
        db = _db()
        try:
            with patch("app.services.competitive_intelligence_service._fetch", return_value=(_SAMPLE_HTML, 200)):
                run_competitive_intelligence_cycle(db)
                second = run_competitive_intelligence_cycle(db)

            self.assertEqual(second["items_added"], 0)
            self.assertEqual(second["items_updated"], 0)

            signals = db.query(CompetitiveIntelligenceSignal).all()
            self.assertEqual(len(signals), len(COMPETITORS) * 4)  # no duplicates
            self.assertTrue(all(s.last_changed_at is None for s in signals))
        finally:
            db.close()

    def test_changed_content_is_detected_and_flagged(self) -> None:
        db = _db()
        try:
            with patch("app.services.competitive_intelligence_service._fetch", return_value=(_SAMPLE_HTML, 200)):
                run_competitive_intelligence_cycle(db)

            changed_html = _SAMPLE_HTML.replace("60,000", "70,000")
            with patch("app.services.competitive_intelligence_service._fetch", return_value=(changed_html, 200)):
                second = run_competitive_intelligence_cycle(db)

            self.assertEqual(second["items_added"], 0)
            self.assertGreater(second["items_updated"], 0)

            scale_signal = (
                db.query(CompetitiveIntelligenceSignal)
                .filter(CompetitiveIntelligenceSignal.signal_type == "scale_claims")
                .first()
            )
            self.assertIsNotNone(scale_signal.last_changed_at)
            self.assertIn("70,000", scale_signal.detail_text)
        finally:
            db.close()

    def test_fetch_failure_is_recorded_honestly_not_silently_skipped(self) -> None:
        db = _db()
        try:
            with patch("app.services.competitive_intelligence_service._fetch", side_effect=Exception("network down")):
                result = run_competitive_intelligence_cycle(db)

            self.assertEqual(result["errors"], len(COMPETITORS))
            for row in result["results"]:
                self.assertFalse(row["fetch_ok"])
                self.assertEqual(row["error"], "network down")

            job = db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).order_by(AgentJobRun.id.desc()).first()
            self.assertEqual(job.status, "FAILED")
        finally:
            db.close()

    def test_non_200_status_is_recorded_not_treated_as_success(self) -> None:
        db = _db()
        try:
            with patch("app.services.competitive_intelligence_service._fetch", return_value=("", 403)):
                result = run_competitive_intelligence_cycle(db)

            self.assertEqual(result["errors"], len(COMPETITORS))
            for row in result["results"]:
                self.assertFalse(row["fetch_ok"])
                self.assertEqual(row["http_status"], 403)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
