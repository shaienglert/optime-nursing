from __future__ import annotations

import importlib
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

_TEST_ADMIN_TOKEN = "test-admin-token"
_ADMIN_HEADERS = {"X-Admin-Token": _TEST_ADMIN_TOKEN}
_admin_env = patch.dict(os.environ, {"OPTIME_ADMIN_TOKEN": _TEST_ADMIN_TOKEN})


class PlacementReferralEndpointsTests(unittest.TestCase):
    def setUp(self) -> None:
        _admin_env.start()
        self.addCleanup(_admin_env.stop)
        self.main = importlib.import_module("app.main")
        self.client = TestClient(self.main.app)
        index = self.main.get_canonical_facility_index()
        self.assertGreater(len(index), 0)
        self.real_canonical_id = next(iter(index))

    def tearDown(self) -> None:
        from app.models.placement_referral import PlacementReferral
        from app.models.facility_agreement import FacilityAgreement

        db = self.main.SessionLocal()
        try:
            db.query(PlacementReferral).filter(PlacementReferral.canonical_facility_id == self.real_canonical_id).delete(
                synchronize_session=False
            )
            db.query(FacilityAgreement).filter(FacilityAgreement.canonical_facility_id == self.real_canonical_id).delete(
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
        self.assertIsNone(body["placement_number"])
        self.assertFalse(body["is_founding_facility"])

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
        body = confirm_response.json()
        self.assertEqual(body["billable_status"], "DUE")
        self.assertEqual(body["commission_due"], 1999.0)
        self.assertEqual(body["placement_number"], 1)
        # First placement, no founding facility on record: facility funds the
        # whole Welcome Package alone.
        self.assertEqual(body["facility_welcome_contribution"], 500.0)
        self.assertEqual(body["oomnik_welcome_contribution"], 0.0)
        self.assertEqual(body["net_income"], 1999.0)

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

    def test_death_before_day_60_bills_999_50(self) -> None:
        created = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id}).json()
        referral_code = created["referral_code"]
        entry_date = datetime.now(timezone.utc) - timedelta(days=40)
        self.client.post(
            f"/placement-referrals/{referral_code}/confirm-entry",
            json={"entry_date": entry_date.isoformat()},
        )
        departure_response = self.client.post(
            f"/placement-referrals/{referral_code}/report-departure",
            json={"departure_date": (entry_date + timedelta(days=20)).isoformat(), "reason": "DECEASED"},
        )
        self.assertEqual(departure_response.status_code, 200)
        self.assertEqual(departure_response.json()["billable_status"], "DUE")
        self.assertEqual(departure_response.json()["commission_due"], 999.5)

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

    def test_founding_facility_gets_fee_free_first_placement_via_endpoint(self) -> None:
        launch_at = datetime.now(timezone.utc) - timedelta(days=200)
        with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": launch_at.isoformat()}, clear=False):
            mark_response = self.client.post(
                f"/facility-agreements/{self.real_canonical_id}/mark-onboarding-complete",
                json={"completed_at": (launch_at + timedelta(days=10)).isoformat()},
                headers=_ADMIN_HEADERS,
            )
            self.assertEqual(mark_response.status_code, 200)
            self.assertTrue(mark_response.json()["is_founding_facility"])

            created = self.client.post("/placement-referrals", json={"canonical_facility_id": self.real_canonical_id}).json()
            entry_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            confirm_response = self.client.post(
                f"/placement-referrals/{created['referral_code']}/confirm-entry",
                json={"entry_date": entry_date},
            )
            self.assertEqual(confirm_response.json()["billable_status"], "WAIVED_FOUNDING_FIRST_PLACEMENT")
            self.assertEqual(confirm_response.json()["commission_due"], 0)
            self.assertTrue(confirm_response.json()["is_founding_facility"])

    def test_facility_agreement_endpoints_require_admin_token(self) -> None:
        get_response = self.client.get(f"/facility-agreements/{self.real_canonical_id}")
        self.assertEqual(get_response.status_code, 401)
        post_response = self.client.post(f"/facility-agreements/{self.real_canonical_id}/mark-onboarding-complete", json={})
        self.assertEqual(post_response.status_code, 401)

    def test_facility_agreement_unknown_facility_is_404(self) -> None:
        response = self.client.get("/facility-agreements/not-a-real-facility", headers=_ADMIN_HEADERS)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
