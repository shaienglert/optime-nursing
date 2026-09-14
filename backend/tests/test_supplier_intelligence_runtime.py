from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class SupplierIntelligenceRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.admin = patch.dict(os.environ, {"OPTIME_ADMIN_TOKEN": "supplier-test-token"})
        self.admin.start()
        self.addCleanup(self.admin.stop)
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)

    def test_live_cycle_accepts_seed_inventory(self) -> None:
        response = self.client.post("/supplier-intelligence/run-now", headers={"X-Admin-Token": "supplier-test-token"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["records_rejected"], 0)
        self.assertGreaterEqual(payload["records_accepted"], 26)
        self.assertEqual(len(payload["sector_counts"]), 23)

    def test_live_cycle_is_admin_protected(self) -> None:
        self.assertEqual(self.client.post("/supplier-intelligence/run-now").status_code, 401)

    def test_catalog_returns_only_public_records_and_filters_sector(self) -> None:
        response = self.client.get("/supplier-intelligence/catalog?sector=HOSPICE_PALLIATIVE")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 3)
        for record in payload["records"]:
            self.assertIn("HOSPICE_PALLIATIVE", record["sector_ids"])
            self.assertIn(record["publication"]["status"], {"LIMITED", "VERIFIED"})
        nathan = next(record for record in payload["records"] if record["supplier_id"] == "nathan-adelson-hospice")
        self.assertEqual(nathan["licenses"][0]["identifier"], "291500")
        self.assertEqual(nathan["ratings"][0]["source"], "CMS Hospice CAHPS")

    def test_coverage_proves_agent_has_started(self) -> None:
        response = self.client.get("/supplier-intelligence/coverage")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["supplier_count"], 0)
        self.assertEqual(payload["sector_count"], 23)
        self.assertEqual(payload["coverage_gaps"], [])
        self.assertGreaterEqual(payload["official_credentials"], 5)
        self.assertGreaterEqual(payload["records_with_official_credentials"], 5)
        self.assertGreaterEqual(payload["records_with_quality_evidence"], 3)
        self.assertIsNotNone(payload["last_cycle_at"])

    def test_dme_catalog_keeps_license_evidence_separate_from_case_readiness(self) -> None:
        response = self.client.get("/supplier-intelligence/catalog?sector=DME_MOBILITY")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 3)
        guardian = next(record for record in payload["records"] if record["supplier_id"] == "guardian-dme-las-vegas")
        self.assertEqual(guardian["licenses"][0]["identifier"], "MP03188")
        self.assertEqual(guardian["publication"]["status"], "LIMITED")
        self.assertFalse(guardian["critical_readiness"]["capacity_confirmed"])
        partner = next(record for record in payload["records"] if record["supplier_id"] == "dme-healthcare-partners-las-vegas")
        self.assertEqual(partner["licenses"][0]["identifier"], "MP03105")
        self.assertTrue(partner["conflicts"])


if __name__ == "__main__":
    unittest.main()
