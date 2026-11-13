from __future__ import annotations

import os
import re
import unittest
from unittest import mock

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import Facility, FacilityDomainAllowlist, FacilityUser, ProviderIdentityChallenge
from app.services.provider_identity import complete_email_verification, start_email_verification

CMS = "SEC-OTP-1"


class VerificationCodeDeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self._clean()
        self.facility = Facility(cms_id=CMS, name="Sunrise", address="1 Main", city="Las Vegas", state="NV", zip_code="89101")
        self.db.add(self.facility)
        self.db.commit()
        self.db.add(FacilityDomainAllowlist(facility_id=self.facility.id, domain="sunrise.org", is_parent_org=False))
        self.db.commit()

    def tearDown(self) -> None:
        self._clean()
        self.db.close()

    def _clean(self) -> None:
        ids = [f.id for f in self.db.query(Facility).filter(Facility.cms_id == CMS)]
        if ids:
            for model in (ProviderIdentityChallenge, FacilityDomainAllowlist, FacilityUser):
                self.db.query(model).filter(model.facility_id.in_(ids)).delete(synchronize_session=False)
            self.db.query(Facility).filter(Facility.id.in_(ids)).delete(synchronize_session=False)
        self.db.commit()

    def test_code_is_emailed_and_never_returned(self) -> None:
        sent = {}

        def fake_send(**kwargs):
            sent.update(kwargs)
            return mock.Mock(ok=True)

        with mock.patch.dict(os.environ, {"OPTIME_PROVIDER_DEBUG_CODES": ""}), mock.patch(
            "app.services.email_service.send_email_detailed", side_effect=fake_send
        ):
            result = start_email_verification(self.db, self.facility.id, "ops@sunrise.org", "Ops", "OWNER", None)
        self.assertNotIn("debug_verification_code", result)
        self.assertEqual(sent["recipients"], ["ops@sunrise.org"])
        code = re.search(r"\b(\d{6})\b", sent["body_text"]).group(1)
        verified = complete_email_verification(self.db, self.facility.id, "ops@sunrise.org", code)
        self.assertTrue(verified)

    def test_failed_delivery_is_an_error(self) -> None:
        with mock.patch("app.services.email_service.send_email_detailed", return_value=mock.Mock(ok=False)):
            with self.assertRaises(ValueError):
                start_email_verification(self.db, self.facility.id, "ops@sunrise.org", "Ops", "OWNER", None)
