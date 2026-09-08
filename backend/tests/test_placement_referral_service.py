from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from app.database import Base, SessionLocal, engine
import app.models.placement_referral  # noqa: F401 -- registers tables on Base
from app.services.placement_referral_service import (
    billable_status,
    commission_due_cents,
    confirm_entry,
    create_referral,
    get_referral_by_code,
    report_departure,
)

Base.metadata.create_all(bind=engine)


def _db():
    return SessionLocal()


class PlacementReferralServiceTests(unittest.TestCase):
    def test_create_referral_starts_pending_entry(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-a", commission_amount_cents=150000)
            self.assertTrue(referral.referral_code)
            self.assertEqual(len(referral.referral_code), 32)
            self.assertIsNone(referral.entry_confirmed_at)
            self.assertEqual(billable_status(referral), "PENDING_ENTRY")
            self.assertEqual(commission_due_cents(referral), 0)

            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.id, referral.id)
        finally:
            db.close()

    def test_unknown_referral_code_returns_none(self) -> None:
        db = _db()
        try:
            self.assertIsNone(get_referral_by_code(db, "does-not-exist"))
        finally:
            db.close()

    def test_confirmed_entry_before_day_60_is_tracking(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-b", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=10)
            confirm_entry(db, referral.referral_code, entry_date=entry, confirmed_by="admissions@example.com")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "TRACKING")
            self.assertEqual(commission_due_cents(loaded), 0)
        finally:
            db.close()

    def test_no_departure_report_bills_automatically_at_day_60(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-c", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=61)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "DUE")
            self.assertEqual(commission_due_cents(loaded), 150000)
        finally:
            db.close()

    def test_exactly_day_60_is_due(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-c2", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=60)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "DUE")
        finally:
            db.close()

    def test_voluntary_departure_before_day_60_waives_commission(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-d", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=70)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=45), reason="VOLUNTARY")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "WAIVED_VOLUNTARY_DEPARTURE")
            self.assertEqual(commission_due_cents(loaded), 0)
        finally:
            db.close()

    def test_voluntary_departure_after_day_60_does_not_undo_billing(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-e", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=90)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=75), reason="VOLUNTARY")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "DUE")
        finally:
            db.close()

    def test_death_between_30_and_60_days_still_bills(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-f", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=45)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            # Died on day 40 -- inside the 30-60 window. Billable immediately, no
            # need to wait for the day-60 mark to chronologically pass.
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=40), reason="DECEASED")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded, now=entry + timedelta(days=41)), "DUE")
        finally:
            db.close()

    def test_death_exactly_on_day_30_or_60_counts(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-g", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=61)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=30), reason="DECEASED")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "DUE")
        finally:
            db.close()

    def test_death_before_day_30_is_waived(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-h", commission_amount_cents=150000)
            entry = datetime.now(timezone.utc) - timedelta(days=61)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=10), reason="DECEASED")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(loaded), "WAIVED_EARLY_DECEASED")
            self.assertEqual(commission_due_cents(loaded), 0)
        finally:
            db.close()

    def test_invalid_departure_reason_rejected(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-i", commission_amount_cents=150000)
            confirm_entry(db, referral.referral_code, entry_date=datetime.now(timezone.utc))
            with self.assertRaises(ValueError):
                report_departure(db, referral.referral_code, departure_date=datetime.now(timezone.utc), reason="MOVED_TO_ANOTHER_STATE")
        finally:
            db.close()

    def test_confirm_entry_unknown_code_raises(self) -> None:
        db = _db()
        try:
            with self.assertRaises(ValueError):
                confirm_entry(db, "not-a-real-code", entry_date=datetime.now(timezone.utc))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
