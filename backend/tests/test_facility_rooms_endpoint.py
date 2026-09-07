from __future__ import annotations

import importlib
import unittest

from fastapi.testclient import TestClient


class FacilityRoomsEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)

        index = self.main.get_canonical_facility_index()
        self.assertGreater(len(index), 0)
        self.real_canonical_id = next(iter(index))

    def test_unknown_canonical_facility_is_404(self) -> None:
        response = self.client.get("/canonical-facilities/not-a-real-facility/rooms")
        self.assertEqual(response.status_code, 404)

    def test_facility_with_no_room_data_reports_has_data_false(self) -> None:
        response = self.client.get(f"/canonical-facilities/{self.real_canonical_id}/rooms")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["canonical_facility_id"], self.real_canonical_id)
        self.assertFalse(body["has_data"])
        self.assertEqual(body["room_types"], [])

    def test_facility_with_seeded_room_data_is_returned(self) -> None:
        from app.services.facility_room_service import upsert_room_type

        db = self.main.SessionLocal()
        try:
            upsert_room_type(
                db,
                canonical_facility_id=self.real_canonical_id,
                room_type_name="Private Suite",
                description="A private room with an ensuite bathroom.",
                monthly_price_cents=580000,
                availability_status="AVAILABLE",
                source="MANUAL",
                photo_urls=["https://example.com/suite.jpg"],
            )
        finally:
            db.close()

        response = self.client.get(f"/canonical-facilities/{self.real_canonical_id}/rooms")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["has_data"])
        self.assertEqual(len(body["room_types"]), 1)
        room = body["room_types"][0]
        self.assertEqual(room["room_type_name"], "Private Suite")
        self.assertEqual(room["monthly_price"], 5800.0)
        self.assertEqual(room["availability_status"], "AVAILABLE")
        self.assertEqual(len(room["photos"]), 1)
        self.assertEqual(room["photos"][0]["url"], "https://example.com/suite.jpg")


if __name__ == "__main__":
    unittest.main()
