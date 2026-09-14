from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.database import Base, SessionLocal, engine
import app.models.competitive_intelligence  # noqa: F401 -- registers tables on Base
from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
from app.models.competitive_intelligence import CompetitiveIntelligenceSignal
from app.services.competitive_intelligence_service import AGENT_KEY, COMPETITORS
from app.services.competitor_structural_research_service import (
    RESEARCH_CATEGORIES,
    run_competitor_structural_research_cycle,
)

Base.metadata.create_all(bind=engine)

_HOW_IT_WORKS_HTML = """
<html><head><title>How It Works | Example Senior Living Advisors</title></head>
<body><p>Here's how it works: a local advisor will call you within 24 hours to discuss
your family's needs, then help you compare options and schedule an in-person tour.</p></body></html>
"""

_ABOUT_HTML = """
<html><head><title>About Us</title></head>
<body><p>Founded in 2005 and headquartered in Seattle, our team of 400 senior living
advisors nationwide has helped families for over 15 years.</p></body></html>
"""

_OWNERSHIP_HTML = """
<html><head><title>Company News</title></head>
<body><p>The company, backed by a private equity investment, is a subsidiary of a
larger holding group. Investors include several growth equity firms.</p></body></html>
"""

_IRRELEVANT_HTML = "<html><head><title>Unrelated</title></head><body><p>Nothing relevant here.</p></body></html>"


def _db():
    return SessionLocal()


class CompetitorStructuralResearchServiceTests(unittest.TestCase):
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

    def test_finds_and_persists_real_structural_signals_for_each_category(self) -> None:
        db = _db()
        try:
            # Route fetched HTML by which category is currently being researched via
            # the query text captured just before each _fetch call.
            calls = {"queries": []}

            def fake_search_capture(query: str):
                calls["queries"].append(query)
                return [("https://example-news.com/profile", "profile")]

            def fake_fetch_by_category(url: str):
                query = calls["queries"][-1]
                if "how it works" in query:
                    return (_HOW_IT_WORKS_HTML, 200)
                if "about us" in query:
                    return (_ABOUT_HTML, 200)
                return (_OWNERSHIP_HTML, 200)

            with patch(
                "app.services.competitor_structural_research_service._search_result_urls",
                side_effect=fake_search_capture,
            ), patch(
                "app.services.competitor_structural_research_service._fetch",
                side_effect=fake_fetch_by_category,
            ):
                result = run_competitor_structural_research_cycle(db)

            self.assertEqual(result["errors"], 0)
            self.assertGreater(result["items_added"], 0)

            signals = db.query(CompetitiveIntelligenceSignal).all()
            self.assertEqual(len(signals), len(COMPETITORS) * len(RESEARCH_CATEGORIES))
            signal_types = {s.signal_type for s in signals}
            self.assertEqual(
                signal_types,
                {"service_model_description", "organizational_scale_disclosure", "ownership_or_backing_disclosure"},
            )

            job = db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).order_by(AgentJobRun.id.desc()).first()
            self.assertEqual(job.status, "SUCCESS")

            knowledge = db.query(AgentKnowledgeRecord).filter(
                AgentKnowledgeRecord.agent_key == AGENT_KEY,
                AgentKnowledgeRecord.record_type == "competitor_structural_research_cycle",
            ).all()
            self.assertEqual(len(knowledge), 1)
        finally:
            db.close()

    def test_no_matching_content_is_reported_honestly_as_not_found(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.competitor_structural_research_service._search_result_urls",
                return_value=[("https://example-news.com/unrelated", "unrelated")],
            ), patch(
                "app.services.competitor_structural_research_service._fetch",
                return_value=(_IRRELEVANT_HTML, 200),
            ):
                result = run_competitor_structural_research_cycle(db)

            self.assertEqual(result["items_added"], 0)
            for competitor_row in result["results"]:
                for category_row in competitor_row["categories"]:
                    self.assertFalse(category_row["found"])
                    self.assertIsNone(category_row["error"])
        finally:
            db.close()

    def test_search_failure_for_one_category_does_not_block_the_rest(self) -> None:
        db = _db()
        try:
            call_count = {"n": 0}

            def fake_search(query: str):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise Exception("search down")
                return [("https://example-news.com/profile", "profile")]

            with patch(
                "app.services.competitor_structural_research_service._search_result_urls",
                side_effect=fake_search,
            ), patch(
                "app.services.competitor_structural_research_service._fetch",
                return_value=(_IRRELEVANT_HTML, 200),
            ):
                result = run_competitor_structural_research_cycle(db)

            self.assertEqual(result["errors"], 1)
            self.assertEqual(len(result["results"]), len(COMPETITORS))
        finally:
            db.close()

    def test_low_quality_domains_are_never_fetched(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.competitor_structural_research_service._search_result_urls",
                return_value=[("https://www.facebook.com/some-post", "irrelevant")],
            ), patch("app.services.competitor_structural_research_service._fetch") as mock_fetch:
                run_competitor_structural_research_cycle(db)
            mock_fetch.assert_not_called()
        finally:
            db.close()

    def test_registers_agent_worker_and_job_run(self) -> None:
        db = _db()
        try:
            db.add(AgentWorker(agent_key=AGENT_KEY, name="Competitive Intelligence Agent", mission="x", data_sources="[]", queue_type="competitive_intelligence"))
            db.commit()

            with patch("app.services.competitor_structural_research_service._search_result_urls", return_value=[]):
                run_competitor_structural_research_cycle(db)

            job = db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).order_by(AgentJobRun.id.desc()).first()
            self.assertIsNotNone(job)
            self.assertEqual(job.status, "SUCCESS")

            worker = db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).first()
            self.assertIsNotNone(worker.last_run)
        finally:
            db.close()


class RestartResilienceTests(unittest.TestCase):
    def tearDown(self) -> None:
        db = _db()
        try:
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).delete()
            db.commit()
        finally:
            db.close()

    def test_startup_delay_defers_a_cycle_that_already_ran_recently_this_month(self) -> None:
        from app.services.competitive_intelligence_service import startup_delay_seconds

        db = _db()
        try:
            recent = datetime.now(timezone.utc) - timedelta(days=2)
            db.add(
                AgentKnowledgeRecord(
                    agent_key=AGENT_KEY,
                    record_type="competitor_structural_research_cycle",
                    entity_key="test",
                    summary="test",
                    payload_json="{}",
                    confidence=0.5,
                    source="LIVE_WEB_SEARCH",
                    created_at=recent,
                )
            )
            db.commit()
        finally:
            db.close()

        interval = 30 * 24 * 60 * 60
        delay = startup_delay_seconds("competitor_structural_research_cycle", interval)
        two_days_seconds = 2 * 24 * 60 * 60
        self.assertAlmostEqual(delay, interval - two_days_seconds, delta=30)


if __name__ == "__main__":
    unittest.main()
