from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.database import Base, SessionLocal, engine
import app.models.placement_referral  # noqa: F401 -- registers tables on Base
import app.models.facility_agreement  # noqa: F401 -- registers tables on Base
from app.services.facility_agreement_service import mark_onboarding_complete
from app.services.placement_referral_service import (
    DEATH_PARTIAL_FEE_CENTS,
    FULL_FEE_CENTS,
    OOMNIK_WELCOME_CONTRIBUTION_CENTS,
    WELCOME_PACKAGE_CENTS,
    billable_status,
    commission_due_cents,
    confirm_entry,
    create_referral,
    facility_welcome_contribution_cents,
    get_referral_by_code,
    is_founding_facility,
    net_income_cents,
    oomnik_welcome_contribution_cents,
    placement_number,
    report_departure,
)

Base.metadata.create_all(bind=engine)

_LAUNCH_AT = "2026-09-15T00:00:00+00:00"


def _db():
    return SessionLocal()


class PlacementReferralServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        db = _db()
        try:
            from app.models.placement_referral import PlacementReferral
            from app.models.facility_agreement import FacilityAgreement

            db.query(PlacementReferral).delete()
            db.query(FacilityAgreement).delete()
            db.commit()
        finally:
            db.close()

    def test_create_referral_starts_pending_entry(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-a")
            self.assertTrue(referral.referral_code)
            self.assertEqual(len(referral.referral_code), 32)
            self.assertIsNone(referral.entry_confirmed_at)
            self.assertEqual(billable_status(db, referral), "PENDING_ENTRY")
            self.assertEqual(commission_due_cents(db, referral), 0)
            self.assertIsNone(placement_number(db, referral))

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
            referral = create_referral(db, canonical_facility_id="canonical-b")
            entry = datetime.now(timezone.utc) - timedelta(days=10)
            confirm_entry(db, referral.referral_code, entry_date=entry, confirmed_by="admissions@example.com")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded), "TRACKING")
            self.assertEqual(commission_due_cents(db, loaded), 0)
            self.assertEqual(placement_number(db, loaded), 1)
        finally:
            db.close()

    def test_no_departure_report_bills_full_fee_automatically_at_day_60(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-c")
            entry = datetime.now(timezone.utc) - timedelta(days=61)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded), "DUE")
            self.assertEqual(commission_due_cents(db, loaded), FULL_FEE_CENTS)
        finally:
            db.close()

    def test_exactly_day_60_is_due(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-c2")
            entry = datetime.now(timezone.utc) - timedelta(days=60)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded), "DUE")
        finally:
            db.close()

    def test_voluntary_departure_before_day_60_waives_commission(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-d")
            entry = datetime.now(timezone.utc) - timedelta(days=70)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=45), reason="VOLUNTARY")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded), "WAIVED_VOLUNTARY_DEPARTURE")
            self.assertEqual(commission_due_cents(db, loaded), 0)
        finally:
            db.close()

    def test_voluntary_departure_after_day_60_does_not_undo_billing(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-e")
            entry = datetime.now(timezone.utc) - timedelta(days=90)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=75), reason="VOLUNTARY")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded), "DUE")
            self.assertEqual(commission_due_cents(db, loaded), FULL_FEE_CENTS)
        finally:
            db.close()

    def test_death_before_day_60_bills_the_50_percent_partial_fee_no_day_30_threshold(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-f")
            entry = datetime.now(timezone.utc) - timedelta(days=45)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            # Died on day 5 -- the superseded 2026-09-08 rule would have waived
            # this (before day 30); the current rule pays 50% regardless of when
            # before day 60 death occurs.
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=5), reason="DECEASED")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded, now=entry + timedelta(days=6)), "DUE")
            self.assertEqual(commission_due_cents(db, loaded, now=entry + timedelta(days=6)), DEATH_PARTIAL_FEE_CENTS)
            self.assertEqual(DEATH_PARTIAL_FEE_CENTS, 99950)  # $999.50 = 50% of $1,999
        finally:
            db.close()

    def test_death_after_day_60_bills_the_full_fee_not_the_partial_one(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-g")
            entry = datetime.now(timezone.utc) - timedelta(days=90)
            confirm_entry(db, referral.referral_code, entry_date=entry)
            report_departure(db, referral.referral_code, departure_date=entry + timedelta(days=70), reason="DECEASED")
            loaded = get_referral_by_code(db, referral.referral_code)
            self.assertEqual(billable_status(db, loaded), "DUE")
            self.assertEqual(commission_due_cents(db, loaded), FULL_FEE_CENTS)
        finally:
            db.close()

    def test_invalid_departure_reason_rejected(self) -> None:
        db = _db()
        try:
            referral = create_referral(db, canonical_facility_id="canonical-i")
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

    def test_second_placement_splits_welcome_package_and_reduces_net_income(self) -> None:
        db = _db()
        try:
            first = create_referral(db, canonical_facility_id="canonical-j")
            confirm_entry(db, first.referral_code, entry_date=datetime.now(timezone.utc) - timedelta(days=100))

            second = create_referral(db, canonical_facility_id="canonical-j")
            entry2 = datetime.now(timezone.utc) - timedelta(days=61)
            confirm_entry(db, second.referral_code, entry_date=entry2)
            loaded_first = get_referral_by_code(db, first.referral_code)
            loaded_second = get_referral_by_code(db, second.referral_code)

            self.assertEqual(placement_number(db, loaded_first), 1)
            self.assertEqual(placement_number(db, loaded_second), 2)

            # First placement: facility funds the whole $500 alone.
            self.assertEqual(oomnik_welcome_contribution_cents(db, loaded_first), 0)
            self.assertEqual(facility_welcome_contribution_cents(db, loaded_first), WELCOME_PACKAGE_CENTS)

            # Second placement: $250/$250 split, net income is fee minus OPTIME's $250.
            self.assertEqual(oomnik_welcome_contribution_cents(db, loaded_second), OOMNIK_WELCOME_CONTRIBUTION_CENTS)
            self.assertEqual(facility_welcome_contribution_cents(db, loaded_second), 25000)
            self.assertEqual(commission_due_cents(db, loaded_second), FULL_FEE_CENTS)
            self.assertEqual(net_income_cents(db, loaded_second), FULL_FEE_CENTS - OOMNIK_WELCOME_CONTRIBUTION_CENTS)
            self.assertEqual(net_income_cents(db, loaded_second), 174900)  # $1,749
        finally:
            db.close()

    def test_second_placement_death_nets_749_dollars_50(self) -> None:
        db = _db()
        try:
            first = create_referral(db, canonical_facility_id="canonical-k")
            confirm_entry(db, first.referral_code, entry_date=datetime.now(timezone.utc) - timedelta(days=100))

            second = create_referral(db, canonical_facility_id="canonical-k")
            entry2 = datetime.now(timezone.utc) - timedelta(days=20)
            confirm_entry(db, second.referral_code, entry_date=entry2)
            report_departure(db, second.referral_code, departure_date=entry2 + timedelta(days=10), reason="DECEASED")
            loaded = get_referral_by_code(db, second.referral_code)

            self.assertEqual(commission_due_cents(db, loaded, now=entry2 + timedelta(days=11)), DEATH_PARTIAL_FEE_CENTS)
            self.assertEqual(net_income_cents(db, loaded, now=entry2 + timedelta(days=11)), DEATH_PARTIAL_FEE_CENTS - OOMNIK_WELCOME_CONTRIBUTION_CENTS)
            self.assertEqual(net_income_cents(db, loaded, now=entry2 + timedelta(days=11)), 74950)  # $749.50
        finally:
            db.close()

    def test_no_launch_date_configured_means_no_facility_is_founding(self) -> None:
        db = _db()
        try:
            mark_onboarding_complete(db, "canonical-l", completed_at=datetime.now(timezone.utc))
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("OPTIME_LAUNCH_DATE", None)
                self.assertFalse(is_founding_facility(db, "canonical-l"))
        finally:
            db.close()

    def test_facility_onboarding_within_90_days_of_launch_is_founding(self) -> None:
        db = _db()
        try:
            mark_onboarding_complete(db, "canonical-m", completed_at=datetime.fromisoformat(_LAUNCH_AT) + timedelta(days=89))
            with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": _LAUNCH_AT}, clear=False):
                self.assertTrue(is_founding_facility(db, "canonical-m"))
        finally:
            db.close()

    def test_facility_onboarding_after_90_days_of_launch_is_not_founding(self) -> None:
        db = _db()
        try:
            mark_onboarding_complete(db, "canonical-n", completed_at=datetime.fromisoformat(_LAUNCH_AT) + timedelta(days=91))
            with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": _LAUNCH_AT}, clear=False):
                self.assertFalse(is_founding_facility(db, "canonical-n"))
        finally:
            db.close()

    def test_founding_facility_first_placement_is_fee_free_regardless_of_outcome(self) -> None:
        db = _db()
        try:
            mark_onboarding_complete(db, "canonical-o", completed_at=datetime.fromisoformat(_LAUNCH_AT) + timedelta(days=1))
            with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": _LAUNCH_AT}, clear=False):
                referral = create_referral(db, canonical_facility_id="canonical-o")
                entry = datetime.now(timezone.utc) - timedelta(days=90)
                confirm_entry(db, referral.referral_code, entry_date=entry)
                loaded = get_referral_by_code(db, referral.referral_code)
                self.assertEqual(billable_status(db, loaded), "WAIVED_FOUNDING_FIRST_PLACEMENT")
                self.assertEqual(commission_due_cents(db, loaded), 0)
                self.assertEqual(oomnik_welcome_contribution_cents(db, loaded), 0)
                self.assertEqual(facility_welcome_contribution_cents(db, loaded), WELCOME_PACKAGE_CENTS)
        finally:
            db.close()

    def test_founding_facility_second_placement_pays_the_normal_fee_schedule(self) -> None:
        db = _db()
        try:
            mark_onboarding_complete(db, "canonical-p", completed_at=datetime.fromisoformat(_LAUNCH_AT) + timedelta(days=1))
            with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": _LAUNCH_AT}, clear=False):
                first = create_referral(db, canonical_facility_id="canonical-p")
                confirm_entry(db, first.referral_code, entry_date=datetime.now(timezone.utc) - timedelta(days=100))

                second = create_referral(db, canonical_facility_id="canonical-p")
                entry2 = datetime.now(timezone.utc) - timedelta(days=61)
                confirm_entry(db, second.referral_code, entry_date=entry2)
                loaded = get_referral_by_code(db, second.referral_code)
                self.assertEqual(billable_status(db, loaded), "DUE")
                self.assertEqual(commission_due_cents(db, loaded), FULL_FEE_CENTS)
        finally:
            db.close()

    def test_non_founding_facility_first_placement_pays_full_fee_not_free(self) -> None:
        """A facility that onboards after the 90-day founding window gets no
        free first placement at all -- the offer is a time-boxed launch
        incentive, not a standing rule for every facility that ever joins."""
        db = _db()
        try:
            mark_onboarding_complete(db, "canonical-q", completed_at=datetime.fromisoformat(_LAUNCH_AT) + timedelta(days=200))
            with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": _LAUNCH_AT}, clear=False):
                referral = create_referral(db, canonical_facility_id="canonical-q")
                entry = datetime.now(timezone.utc) - timedelta(days=90)
                confirm_entry(db, referral.referral_code, entry_date=entry)
                loaded = get_referral_by_code(db, referral.referral_code)
                self.assertEqual(billable_status(db, loaded), "DUE")
                self.assertEqual(commission_due_cents(db, loaded), FULL_FEE_CENTS)
                # No Oomnik Welcome Package contribution either -- that only starts at placement #2.
                self.assertEqual(oomnik_welcome_contribution_cents(db, loaded), 0)
        finally:
            db.close()

    def test_facility_with_no_agreement_record_is_never_founding(self) -> None:
        db = _db()
        try:
            with patch.dict(os.environ, {"OPTIME_LAUNCH_DATE": _LAUNCH_AT}, clear=False):
                self.assertFalse(is_founding_facility(db, "canonical-never-onboarded"))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
