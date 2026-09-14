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
        self.assertGreaterEqual(payload["records_accepted"], 10)
        self.assertGreaterEqual(len(payload["sector_counts"]), 8)

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
            self.assertEqual(record["ratings"], [])

    def test_coverage_proves_agent_has_started(self) -> None:
        response = self.client.get("/supplier-intelligence/coverage")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["supplier_count"], 0)
        self.assertGreater(payload["sector_count"], 0)
        self.assertIsNotNone(payload["last_cycle_at"])


if __name__ == "__main__":
    unittest.main()
