from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

_TEST_ADMIN_TOKEN = "test-admin-token"
_ADMIN_HEADERS = {"X-Admin-Token": _TEST_ADMIN_TOKEN}
_admin_env = patch.dict(os.environ, {"OPTIME_ADMIN_TOKEN": _TEST_ADMIN_TOKEN})

_SAMPLE_HTML = """
<html><head><title>Find Senior Living</title></head>
<body><h1>Find a community at no cost to your family</h1>
<p>We are compensated by our partner communities. Compare pricing and photos.</p>
<p>60,000 communities nationwide.</p></body></html>
"""


class CompetitiveIntelligenceEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        _admin_env.start()
        self.addCleanup(_admin_env.stop)
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)

    def tearDown(self) -> None:
        from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
        from app.models.competitive_intelligence import CompetitiveIntelligenceSignal
        from app.services.competitive_intelligence_service import AGENT_KEY

        db = self.main.SessionLocal()
        try:
            db.query(CompetitiveIntelligenceSignal).delete()
            db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).delete()
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).delete()
            db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).delete()
            db.commit()
        finally:
            db.close()

    def test_signals_requires_admin_token(self) -> None:
        response = self.client.get("/competitive-intelligence/signals")
        self.assertEqual(response.status_code, 401)

    def test_run_now_requires_admin_token(self) -> None:
        response = self.client.post("/competitive-intelligence/run-now")
        self.assertEqual(response.status_code, 401)

    def test_run_now_then_list_signals_with_admin_token(self) -> None:
        with patch("app.main.run_competitive_intelligence_cycle") as mock_run:
            mock_run.return_value = {
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "runtime_ms": 1000,
                "items_added": 3,
                "items_updated": 0,
                "errors": 0,
                "results": [],
            }
            run_response = self.client.post("/competitive-intelligence/run-now", headers=_ADMIN_HEADERS)
        self.assertEqual(run_response.status_code, 200)
        self.assertEqual(run_response.json()["items_added"], 3)
        mock_run.assert_called_once()

    def test_real_cycle_via_endpoint_populates_signals_list(self) -> None:
        with patch("app.services.competitive_intelligence_service._fetch", return_value=(_SAMPLE_HTML, 200)):
            run_response = self.client.post("/competitive-intelligence/run-now", headers=_ADMIN_HEADERS)
        self.assertEqual(run_response.status_code, 200)
        self.assertGreater(run_response.json()["items_added"], 0)

        list_response = self.client.get("/competitive-intelligence/signals", headers=_ADMIN_HEADERS)
        self.assertEqual(list_response.status_code, 200)
        rows = list_response.json()
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["competitor_name"] for row in rows))


if __name__ == "__main__":
    unittest.main()
