from __future__ import annotations

import importlib
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class FacilityOutreachEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)
        index = self.main.get_canonical_facility_index()
        self.assertGreater(len(index), 0)
        self.real_canonical_id = next(iter(index))

    def tearDown(self) -> None:
        # This id is deterministic (next(iter(index))) and other test modules (e.g.
        # test_facility_rooms_endpoint.py) use the same lookup -- without cleanup,
        # whichever module runs first leaves rows the other reads back, making
        # pass/fail depend on pytest's file ordering instead of each test's own setup.
        from app.models.facility_outreach import FacilityContact, FacilityOutreachRequest
        from app.models.facility_room_offering import FacilityRoomPhoto, FacilityRoomType

        db = self.main.SessionLocal()
        try:
            room_ids = [
                row.id
                for row in db.query(FacilityRoomType.id).filter(FacilityRoomType.canonical_facility_id == self.real_canonical_id)
            ]
            if room_ids:
                db.query(FacilityRoomPhoto).filter(FacilityRoomPhoto.room_type_id.in_(room_ids)).delete(synchronize_session=False)
                db.query(FacilityRoomType).filter(FacilityRoomType.id.in_(room_ids)).delete(synchronize_session=False)
            db.query(FacilityOutreachRequest).filter(FacilityOutreachRequest.canonical_facility_id == self.real_canonical_id).delete(
                synchronize_session=False
            )
            db.query(FacilityContact).filter(FacilityContact.canonical_facility_id == self.real_canonical_id).delete(
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()

    def test_request_outreach_unknown_facility_is_404(self) -> None:
        response = self.client.post("/canonical-facilities/not-a-real-facility/request-outreach")
        self.assertEqual(response.status_code, 404)

    def test_request_outreach_no_contact_found_reports_honestly(self) -> None:
        with patch("app.main.facility_outreach_service.discover_contact", return_value=None):
            response = self.client.post(f"/canonical-facilities/{self.real_canonical_id}/request-outreach")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "FAILED_NO_CONTACT")
        self.assertIsNone(body["draft"])

    def test_request_outreach_with_contact_returns_draft_and_sends_nothing(self) -> None:
        fake_contact = MagicMock(email="marketing@example.com")
        with patch("app.main.facility_outreach_service.discover_contact", return_value=fake_contact), patch(
            "app.main.facility_outreach_service.email_service.send_email_detailed"
        ) as mock_send:
            response = self.client.post(f"/canonical-facilities/{self.real_canonical_id}/request-outreach")
        mock_send.assert_not_called()
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "AWAITING_APPROVAL")
        self.assertEqual(body["contact_email"], "marketing@example.com")
        self.assertIsNotNone(body["draft"])
        self.assertEqual(body["draft"]["to"], "marketing@example.com")

    def test_approve_send_rejects_non_awaiting_request(self) -> None:
        with patch("app.main.facility_outreach_service.discover_contact", return_value=None):
            created = self.client.post(f"/canonical-facilities/{self.real_canonical_id}/request-outreach").json()
        response = self.client.post(f"/facility-outreach-requests/{created['id']}/approve-send")
        self.assertEqual(response.status_code, 400)

    def test_approve_send_success_actually_calls_email_service(self) -> None:
        fake_contact = MagicMock(email="marketing@example.com")
        with patch("app.main.facility_outreach_service.discover_contact", return_value=fake_contact):
            created = self.client.post(f"/canonical-facilities/{self.real_canonical_id}/request-outreach").json()

        ok_result = MagicMock(ok=True, message="sent")
        with patch("app.main.facility_outreach_service.email_service.send_email_detailed", return_value=ok_result) as mock_send:
            response = self.client.post(f"/facility-outreach-requests/{created['id']}/approve-send")
        mock_send.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "SENT")

    def test_public_status_unknown_token_is_404(self) -> None:
        response = self.client.get("/facility-outreach/not-a-real-token")
        self.assertEqual(response.status_code, 404)

    def test_public_submit_writes_rooms_and_public_status_reflects_it(self) -> None:
        with patch("app.main.facility_outreach_service.discover_contact", return_value=None):
            created = self.client.post(f"/canonical-facilities/{self.real_canonical_id}/request-outreach").json()

        db = self.main.SessionLocal()
        try:
            outreach = self.main.facility_outreach_service.get_request_by_id(db, created["id"])
            token = outreach.response_token
        finally:
            db.close()

        status_response = self.client.get(f"/facility-outreach/{token}")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["status"], "FAILED_NO_CONTACT")

        submit_response = self.client.post(
            f"/facility-outreach/{token}/submit",
            json={
                "room_types": [
                    {
                        "room_type_name": "Studio",
                        "description": "A studio room",
                        "monthly_price_cents": 400000,
                        "availability_status": "AVAILABLE",
                        "photo_urls": [],
                    }
                ]
            },
        )
        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.json()["status"], "RESPONDED")

        rooms_response = self.client.get(f"/canonical-facilities/{self.real_canonical_id}/rooms")
        self.assertTrue(rooms_response.json()["has_data"])

    def test_public_submit_unknown_token_is_404(self) -> None:
        response = self.client.post("/facility-outreach/not-a-real-token/submit", json={"room_types": []})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
