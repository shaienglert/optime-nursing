from __future__ import annotations

import unittest
from unittest.mock import patch

from app.database import Base, SessionLocal, engine
import app.models.competitive_intelligence  # noqa: F401 -- registers tables on Base
from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
from app.models.competitive_intelligence import MarketSupplySignal
from app.services.competitive_intelligence_service import AGENT_KEY
from app.services.market_supply_intelligence_service import QUERIES, run_market_supply_intelligence_cycle

Base.metadata.create_all(bind=engine)

_CONSTRUCTION_HTML = """
<html><head><title>New Senior Living Community Breaks Ground in Austin, TX</title></head>
<body><p>Developers broke ground on a new 120-unit assisted living community
in Austin, TX this week, with completion expected in 2027.</p></body></html>
"""

_OPENING_HTML = """
<html><head><title>Willow Creek Senior Living Now Open in Denver, CO</title></head>
<body><p>Willow Creek Senior Living, a 90-bed memory care community, is now open
in Denver, CO after an 18-month construction timeline.</p></body></html>
"""

_IRRELEVANT_HTML = "<html><head><title>Unrelated Article</title></head><body><p>Nothing relevant here.</p></body></html>"


def _db():
    return SessionLocal()


class MarketSupplyIntelligenceServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        db = _db()
        try:
            db.query(MarketSupplySignal).delete()
            db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).delete()
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).delete()
            db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).delete()
            db.commit()
        finally:
            db.close()

    def test_finds_and_persists_a_real_construction_start_with_city_state(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.market_supply_intelligence_service._search_result_urls",
                return_value=[("https://example-news.com/austin-groundbreaking", "New community breaks ground")],
            ), patch(
                "app.services.market_supply_intelligence_service._fetch",
                return_value=(_CONSTRUCTION_HTML, 200),
            ):
                result = run_market_supply_intelligence_cycle(db)

            self.assertEqual(result["errors"], 0)
            self.assertGreater(result["items_added"], 0)

            rows = db.query(MarketSupplySignal).filter(MarketSupplySignal.category == "CONSTRUCTION_START").all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].city_state, "Austin, TX")
            self.assertIn("broke ground", rows[0].snippet.lower())
            self.assertEqual(rows[0].source_url, "https://example-news.com/austin-groundbreaking")
        finally:
            db.close()

    def test_skip_domains_are_never_fetched(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.market_supply_intelligence_service._search_result_urls",
                return_value=[("https://www.facebook.com/some-post", "irrelevant")],
            ), patch("app.services.market_supply_intelligence_service._fetch") as mock_fetch:
                run_market_supply_intelligence_cycle(db)
            mock_fetch.assert_not_called()
        finally:
            db.close()

    def test_same_url_is_not_added_twice_across_cycles(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.market_supply_intelligence_service._search_result_urls",
                return_value=[("https://example-news.com/denver-opening", "Now open")],
            ), patch(
                "app.services.market_supply_intelligence_service._fetch",
                return_value=(_OPENING_HTML, 200),
            ):
                first = run_market_supply_intelligence_cycle(db)
                second = run_market_supply_intelligence_cycle(db)

            self.assertGreater(first["items_added"], 0)
            self.assertEqual(second["items_added"], 0)
            rows = db.query(MarketSupplySignal).filter(MarketSupplySignal.source_url == "https://example-news.com/denver-opening").all()
            self.assertEqual(len(rows), 1)
        finally:
            db.close()

    def test_irrelevant_article_yields_zero_items_honestly(self) -> None:
        db = _db()
        try:
            with patch(
                "app.services.market_supply_intelligence_service._search_result_urls",
                return_value=[("https://example-news.com/unrelated", "Unrelated")],
            ), patch(
                "app.services.market_supply_intelligence_service._fetch",
                return_value=(_IRRELEVANT_HTML, 200),
            ):
                result = run_market_supply_intelligence_cycle(db)

            self.assertEqual(result["items_added"], 0)
            for category in result["categories"]:
                self.assertEqual(category["items"], [])
        finally:
            db.close()

    def test_search_failure_for_one_category_does_not_block_others(self) -> None:
        db = _db()
        try:
            call_count = {"n": 0}

            def fake_search(query: str):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise Exception("search down")
                return [("https://example-news.com/denver-opening", "Now open")]

            with patch("app.services.market_supply_intelligence_service._search_result_urls", side_effect=fake_search), patch(
                "app.services.market_supply_intelligence_service._fetch", return_value=(_OPENING_HTML, 200)
            ):
                result = run_market_supply_intelligence_cycle(db)

            self.assertEqual(result["errors"], 1)
            self.assertEqual(len(result["categories"]), len(QUERIES))
        finally:
            db.close()

    def test_registers_agent_worker_and_job_run(self) -> None:
        db = _db()
        try:
            db.add(AgentWorker(agent_key=AGENT_KEY, name="Competitive Intelligence Agent", mission="x", data_sources="[]", queue_type="competitive_intelligence"))
            db.commit()

            with patch("app.services.market_supply_intelligence_service._search_result_urls", return_value=[]):
                run_market_supply_intelligence_cycle(db)

            job = db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).order_by(AgentJobRun.id.desc()).first()
            self.assertIsNotNone(job)
            self.assertEqual(job.status, "SUCCESS")

            knowledge = db.query(AgentKnowledgeRecord).filter(
                AgentKnowledgeRecord.agent_key == AGENT_KEY,
                AgentKnowledgeRecord.record_type == "market_supply_intelligence_cycle",
            ).all()
            self.assertEqual(len(knowledge), 1)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
