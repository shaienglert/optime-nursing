from __future__ import annotations

import os
import unittest
from unittest import mock

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import Facility, FacilityAuditLog, FacilityMarketRegistration, FacilityUser
from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
from app.services.israel_facility_import import load_israel_records
from app.services.israel_facility_registration import save_israel_registration, validate_registration

CANONICAL_ID = "IL-MOH-237U6"
VALID = {
    "functional_levels_served": ["NURSING", "cognitive_frail"],
    "moh_code_agreement": "YES",
    "license_id": "237U6",
    "license_authority": "MINISTRY_OF_HEALTH",
    "license_expiration_date": "2099-12-31",
    "monthly_price_ils": 18000,
}


class IsraelRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self._clean()
        self.facility = Facility(cms_id=CANONICAL_ID, name="אדמונית החורש", address="Unknown", city="עספיא", state="IL", zip_code="UNKNOWN")
        self.db.add(self.facility)
        self.db.commit()
        self.user = FacilityUser(facility_id=self.facility.id, email="a@example.com", password_hash="x", role="OWNER")
        self.marketing = FacilityUser(facility_id=self.facility.id, email="m@example.com", password_hash="x", role="MARKETING")
        self.db.add_all([self.user, self.marketing])
        self.db.commit()
        self.row = next(r for r in load_israel_records()[0] if r["canonical_id"] == CANONICAL_ID)

    def tearDown(self) -> None:
        self._clean()
        self.db.close()

    def _clean(self) -> None:
        ids = [f.id for f in self.db.query(Facility).filter(Facility.cms_id == CANONICAL_ID)]
        if ids:
            for model in (FacilityMarketRegistration, FacilityAuditLog, FacilityUser):
                self.db.query(model).filter(model.facility_id.in_(ids)).delete(synchronize_session=False)
            self.db.query(Facility).filter(Facility.id.in_(ids)).delete(synchronize_session=False)
        self.db.commit()

    def _fit(self, answers):
        with mock.patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "israel"}):
            intent = build_client_intent({"israelMarket": answers}, "", {}, {})
            return evaluate_candidate_intent(self.row, intent)

    def test_unregistered_facility_is_pending(self) -> None:
        fit = self._fit({"functionalLevel": "NURSING", "fundingPathway": "MOH_CODE"})
        self.assertEqual(fit["hard_gate"], "PENDING_VERIFICATION")

    def test_registration_decides_all_israeli_musts_including_license(self) -> None:
        save_israel_registration(self.db, self.facility.id, self.user.id, VALID)
        fit = self._fit({"functionalLevel": "NURSING", "fundingPathway": "MOH_CODE"})
        self.assertEqual(fit["hard_gate"], "PASS", fit)
        self.assertTrue({"IL_FUNCTIONAL_LEVEL", "IL_MOH_CODE_AGREEMENT", "LICENSE_CURRENTLY_VALID"} <= set(fit["must_pass"]))
        self.assertEqual(self._fit({"functionalLevel": "INDEPENDENT"})["hard_gate"], "FAIL")

    def test_expired_license_fails(self) -> None:
        save_israel_registration(self.db, self.facility.id, self.user.id, {**VALID, "license_expiration_date": "2020-01-01"})
        self.assertEqual(self._fit({"functionalLevel": "NURSING"})["hard_gate"], "FAIL")

    def test_audit_only_on_change_and_role_check(self) -> None:
        save_israel_registration(self.db, self.facility.id, self.user.id, VALID)
        again = save_israel_registration(self.db, self.facility.id, self.user.id, VALID)
        self.assertFalse(again["changed"])
        audits = self.db.query(FacilityAuditLog).filter(FacilityAuditLog.facility_id == self.facility.id).count()
        self.assertEqual(audits, 1)
        with self.assertRaises(PermissionError):
            save_israel_registration(self.db, self.facility.id, self.marketing.id, VALID)

    def test_validation(self) -> None:
        for bad in (
            {**VALID, "functional_levels_served": []},
            {**VALID, "functional_levels_served": ["SOMETHING"]},
            {**VALID, "moh_code_agreement": "MAYBE"},
            {**VALID, "license_expiration_date": "31/12/2099"},
            {**VALID, "monthly_price_ils": -5},
        ):
            with self.assertRaises(ValueError):
                validate_registration(bad)
