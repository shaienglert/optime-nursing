from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

_TEST_ADMIN_TOKEN = "test-admin-token"
_ADMIN_HEADERS = {"X-Admin-Token": _TEST_ADMIN_TOKEN}
_admin_env = patch.dict(os.environ, {"OPTIME_ADMIN_TOKEN": _TEST_ADMIN_TOKEN})

_OPENING_HTML = """
<html><head><title>Willow Creek Senior Living Now Open in Denver, CO</title></head>
<body><p>Willow Creek Senior Living is now open in Denver, CO.</p></body></html>
"""


class MarketSupplyIntelligenceEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        _admin_env.start()
        self.addCleanup(_admin_env.stop)
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)

    def tearDown(self) -> None:
        from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord
        from app.models.competitive_intelligence import MarketSupplySignal
        from app.services.competitive_intelligence_service import AGENT_KEY

        db = self.main.SessionLocal()
        try:
            db.query(MarketSupplySignal).delete()
            db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).delete()
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).delete()
            db.commit()
        finally:
            db.close()

    def test_signals_requires_admin_token(self) -> None:
        response = self.client.get("/market-supply-intelligence/signals")
        self.assertEqual(response.status_code, 401)

    def test_run_now_requires_admin_token(self) -> None:
        response = self.client.post("/market-supply-intelligence/run-now")
        self.assertEqual(response.status_code, 401)

    def test_run_now_then_list_signals_with_admin_token(self) -> None:
        with patch(
            "app.services.market_supply_intelligence_service._search_result_urls",
            return_value=[("https://example-news.com/denver-opening", "Now open")],
        ), patch(
            "app.services.market_supply_intelligence_service._fetch",
            return_value=(_OPENING_HTML, 200),
        ):
            run_response = self.client.post("/market-supply-intelligence/run-now", headers=_ADMIN_HEADERS)
        self.assertEqual(run_response.status_code, 200)
        self.assertGreater(run_response.json()["items_added"], 0)

        list_response = self.client.get("/market-supply-intelligence/signals", headers=_ADMIN_HEADERS)
        self.assertEqual(list_response.status_code, 200)
        rows = list_response.json()
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0]["city_state"], "Denver, CO")

    def test_las_vegas_run_now_is_admin_protected(self) -> None:
        response = self.client.post("/market-supply-intelligence/las-vegas/run-now")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
