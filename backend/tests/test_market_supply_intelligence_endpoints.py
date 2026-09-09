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
        from app.models.facility import Facility, FacilityLicenseRecord
        from app.services.competitive_intelligence_service import AGENT_KEY

        db = self.main.SessionLocal()
        try:
            db.query(MarketSupplySignal).delete()
            db.query(AgentJobRun).filter(AgentJobRun.agent_key == AGENT_KEY).delete()
            db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).delete()
            db.query(FacilityLicenseRecord).filter(FacilityLicenseRecord.state_care_type == "ASSISTED_LIVING").delete()
            db.query(Facility).filter(Facility.cms_id == "NV-REPORT-1").delete()
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

    def test_official_cms_collection_is_admin_protected_and_returns_collector_result(self) -> None:
        denied = self.client.post("/market-intelligence/collect/cms")
        self.assertEqual(denied.status_code, 401)
        expected = {
            "source": "CMS",
            "provider_rows": 12,
            "quality_rows": 34,
            "observations_written": 8,
            "provider_source_url": "https://data.cms.gov/provider-data/dataset/4pq5-n9py",
            "quality_source_url": "https://data.cms.gov/provider-data/dataset/djen-97ju",
        }
        with patch("app.main.collect_cms_market_metrics", return_value=expected):
            response = self.client.post("/market-intelligence/collect/cms", headers=_ADMIN_HEADERS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_market_report_marks_uncollected_metrics_missing_not_zero(self) -> None:
        response = self.client.get("/market-intelligence/report?geography_key=NEVADA", headers=_ADMIN_HEADERS)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["ranking_input"])
        occupancy = next(row for row in payload["metrics"] if row["metric_key"] == "OCCUPANCY_RATE")
        self.assertEqual(occupancy["status"], "MISSING")
        self.assertEqual(occupancy["observations"], [])

    def test_market_report_derives_nevada_licensed_counts_without_claiming_independent_living(self) -> None:
        from app.models.facility import Facility, FacilityLicenseRecord

        db = self.main.SessionLocal()
        try:
            facility = Facility(cms_id="NV-REPORT-1", name="Report Test", address="1 Test Way", city="Las Vegas", state="NV", zip_code="89101", beds=42)
            db.add(facility)
            db.flush()
            db.add(FacilityLicenseRecord(facility_id=facility.id, status="VERIFIED", state_care_type="ASSISTED_LIVING"))
            db.commit()
        finally:
            db.close()

        response = self.client.get("/market-intelligence/report?geography_key=NEVADA", headers=_ADMIN_HEADERS)
        self.assertEqual(response.status_code, 200)
        rows = response.json()["metrics"]
        facility_count = next(row for row in rows if row["metric_key"] == "FACILITY_COUNT")
        self.assertEqual(facility_count["status"], "AVAILABLE")
        self.assertEqual(facility_count["observations"][0]["value"], "1")
        self.assertIn("excludes unlicensed independent living", facility_count["observations"][0]["source_scope"])


if __name__ == "__main__":
    unittest.main()
