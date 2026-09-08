from __future__ import annotations

import importlib
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


class PlacementReferralEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)
        index = self.main.get_canonical_facility_index()
        self.assertGreater(len(index), 0)
        self.real_canonical_id = next(iter(index))

    def tearDown(self) -> None:
        from app.models.placement_referral import PlacementReferral

        db = self.main.SessionLocal()
        try:
            db.query(PlacementReferral).filter(PlacementReferral.canonical_facility_id == self.real_canonical_id).delete(
                synchronize_session=False
            )
            db.commit()
        finally:
            db.close()

    def test_create_referral_unknown_facility_is_404(self) -> None:
        response = self.client.post("/placement-referrals", json={"canonical_facility_id": "not-a-real-facility"})
        self.assertEqual(response.status_code, 404)

    def test_create_referral_starts_pending_entry(self) -> None:
        response = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["referral_code"])
        self.assertEqual(body["billable_status"], "PENDING_ENTRY")
        self.assertEqual(body["commission_due"], 0)
        self.assertEqual(body["benefit_amount"], 500.0)
        self.assertEqual(body["facility_credit_amount"], 250.0)

    def test_unknown_referral_code_is_404(self) -> None:
        response = self.client.get("/placement-referrals/not-a-real-code")
        self.assertEqual(response.status_code, 404)

    def test_full_lifecycle_confirm_entry_then_due_at_day_60(self) -> None:
        created = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id}).json()
        referral_code = created["referral_code"]

        entry_date = (datetime.now(timezone.utc) - timedelta(days=61)).isoformat()
        confirm_response = self.client.post(
            f"/placement-referrals/{referral_code}/confirm-entry",
            json={"entry_date": entry_date, "confirmed_by": "admissions@example.com"},
        )
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["billable_status"], "DUE")
        self.assertEqual(confirm_response.json()["commission_due"], confirm_response.json()["commission_amount"])

        status_response = self.client.get(f"/placement-referrals/{referral_code}")
        self.assertEqual(status_response.json()["billable_status"], "DUE")

    def test_voluntary_departure_before_day_60_waives_via_endpoint(self) -> None:
        created = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id}).json()
        referral_code = created["referral_code"]
        entry_date = datetime.now(timezone.utc) - timedelta(days=40)
        self.client.post(
            f"/placement-referrals/{referral_code}/confirm-entry",
            json={"entry_date": entry_date.isoformat()},
        )
        departure_response = self.client.post(
            f"/placement-referrals/{referral_code}/report-departure",
            json={"departure_date": (entry_date + timedelta(days=20)).isoformat(), "reason": "VOLUNTARY"},
        )
        self.assertEqual(departure_response.status_code, 200)
        self.assertEqual(departure_response.json()["billable_status"], "WAIVED_VOLUNTARY_DEPARTURE")
        self.assertEqual(departure_response.json()["commission_due"], 0)

    def test_invalid_departure_reason_is_422(self) -> None:
        created = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id}).json()
        referral_code = created["referral_code"]
        self.client.post(
            f"/placement-referrals/{referral_code}/confirm-entry",
            json={"entry_date": datetime.now(timezone.utc).isoformat()},
        )
        response = self.client.post(
            f"/placement-referrals/{referral_code}/report-departure",
            json={"departure_date": datetime.now(timezone.utc).isoformat(), "reason": "MOVED_AWAY"},
        )
        self.assertEqual(response.status_code, 422)

    def test_confirm_entry_unknown_code_is_404(self) -> None:
        response = self.client.post(
            "/placement-referrals/not-a-real-code/confirm-entry",
            json={"entry_date": datetime.now(timezone.utc).isoformat()},
        )
        self.assertEqual(response.status_code, 404)

    def test_confirm_entry_bad_date_format_is_422(self) -> None:
        created = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id}).json()
        response = self.client.post(
            f"/placement-referrals/{created['referral_code']}/confirm-entry",
            json={"entry_date": "not-a-date"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
