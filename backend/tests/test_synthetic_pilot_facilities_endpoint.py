from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


PILOT_ROWS = {
    "PILOT-NV-001": {
        "canonical_id": "PILOT-NV-001",
        "facility_name": "Desert Gardens Independent Living",
        "address": "1137 Pilot Mesa Avenue",
        "city": "LAS VEGAS",
        "state": "NV",
        "zip": "89101",
        "phone": "+1-702-555-0101",
        "canonical_type": "INDEPENDENT_LIVING",
        "licensed_capacity": 29,
        "pilot_exposure_order": 1,
    },
    "PILOT-NV-002": {
        "canonical_id": "PILOT-NV-002",
        "facility_name": "Canyon House Memory Care",
        "address": "2200 Pilot Canyon Road",
        "city": "HENDERSON",
        "state": "NV",
        "zip": "89002",
        "canonical_type": "MEMORY_CARE",
        "licensed_capacity": 42,
        "pilot_exposure_order": 2,
    },
}


class SyntheticPilotFacilitiesEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)

    def _patch_pilot(self):
        return (
            patch.object(self.main, "configured_canonical_market", return_value="synthetic-pilot"),
            patch.object(self.main, "get_canonical_facility_index", return_value=PILOT_ROWS),
            patch.object(self.main, "get_facility_media_record", return_value=None),
        )

    def test_list_uses_canonical_pilot_without_running_intelligence(self) -> None:
        market, index, media = self._patch_pilot()
        with market, index, media, patch.object(self.main, "run_intelligence_collection") as intelligence:
            response = self.client.get("/facilities")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["cms_id"], "PILOT-NV-001")
        self.assertEqual(response.json()[1]["name"], "Canyon House Memory Care")
        intelligence.assert_not_called()

    def test_list_searches_the_pilot_index(self) -> None:
        market, index, media = self._patch_pilot()
        with market, index, media:
            response = self.client.get("/facilities?q=memory")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["cms_id"] for row in response.json()], ["PILOT-NV-002"])

    def test_pilot_card_detail_uses_exposure_order_id(self) -> None:
        market, index, media = self._patch_pilot()
        with market, index, media:
            response = self.client.get("/facilities/2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["canonical_facility_id"], "PILOT-NV-002")
        self.assertEqual(response.json()["beds"], 42)


if __name__ == "__main__":
    unittest.main()
