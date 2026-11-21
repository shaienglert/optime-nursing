from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import (
    Facility,
    FacilityAuditLog,
    FacilityMarketRegistration,
    FacilityPhoto,
    FacilityPortalInvite,
    FacilityPortalSession,
    FacilityUser,
)

from tests.israel_registration_fixture import REQUIRED_QUESTIONNAIRE

PREFIX = "TEST-PORTAL-"
VALID = {
    "functional_levels_served": ["NURSING"],
    "moh_code_agreement": "YES",
    "license_id": "X1",
    "license_authority": "MINISTRY_OF_HEALTH",
    "license_expiration_date": "2099-12-31",
    "questionnaire": dict(REQUIRED_QUESTIONNAIRE),
}


class PortalAccessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = mock.patch.dict(
            os.environ,
            {"OPTIME_ADMIN_TOKEN": "admin-secret", "OPTIME_PROVIDER_SESSION_REQUIRED": "1"},
        )
        self.env.start()
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        self._clean()
        self.a = Facility(cms_id=PREFIX + "A", name="א", address="x", city="x", state="IL", zip_code="0")
        self.b = Facility(cms_id=PREFIX + "B", name="ב", address="x", city="x", state="IL", zip_code="0")
        self.db.add_all([self.a, self.b])
        self.db.commit()
        from app.main import app

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self._clean()
        self.db.close()
        self.env.stop()

    def _clean(self) -> None:
        ids = [f.id for f in self.db.query(Facility).filter(Facility.cms_id.like(PREFIX + "%"))]
        if ids:
            for model in (FacilityPortalSession, FacilityPortalInvite, FacilityMarketRegistration, FacilityPhoto, FacilityAuditLog, FacilityUser):
                self.db.query(model).filter(model.facility_id.in_(ids)).delete(synchronize_session=False)
            self.db.query(Facility).filter(Facility.id.in_(ids)).delete(synchronize_session=False)
        self.db.commit()

    def _invite(self, facility: Facility) -> str:
        response = self.client.post(
            "/admin/portal/invites",
            json={"canonical_id": facility.cms_id},
            headers={"x-admin-token": "admin-secret"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["link_path"], f"/he/portal/{body['token']}")
        return body["token"]

    def _session(self, facility: Facility) -> str:
        response = self.client.post("/provider/portal/redeem", json={"token": self._invite(facility)})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["facility_id"], facility.id)
        return response.json()["session_token"]

    def _save(self, facility_id: int, headers=None, body_extra=None):
        return self.client.put(
            f"/provider/facilities/{facility_id}/israel-registration",
            json={**VALID, **(body_extra or {})},
            headers=headers or {},
        )

    def test_invite_requires_admin_token(self) -> None:
        response = self.client.post("/admin/portal/invites", json={"facility_id": self.a.id})
        self.assertEqual(response.status_code, 401)

    def test_token_is_stored_only_as_hash(self) -> None:
        token = self._invite(self.a)
        stored = self.db.query(FacilityPortalInvite).filter(FacilityPortalInvite.facility_id == self.a.id).one()
        self.assertNotEqual(stored.token_hash, token)
        self.assertNotIn(token, stored.token_hash)

    def test_link_session_can_save_and_body_user_id_is_ignored(self) -> None:
        token = self._session(self.a)
        response = self._save(self.a.id, {"Authorization": f"Bearer {token}"}, {"user_id": 999999})
        self.assertEqual(response.status_code, 200, response.text)
        me = self.client.get("/provider/portal/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me.json()["canonical_id"], self.a.cms_id)

    def test_body_user_id_alone_is_refused_when_sessions_required(self) -> None:
        owner = FacilityUser(facility_id=self.a.id, email="o@example.com", password_hash="x", role="OWNER")
        self.db.add(owner)
        self.db.commit()
        self.assertEqual(self._save(self.a.id, body_extra={"user_id": owner.id}).status_code, 401)

    def test_portal_reads_back_raw_saved_values(self) -> None:
        token = self._session(self.a)
        headers = {"Authorization": f"Bearer {token}"}
        self._save(self.a.id, headers)
        got = self.client.get(f"/provider/facilities/{self.a.id}/israel-registration", headers=headers)
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.json()["registration"]["functional_levels_served"], ["NURSING"])
        self.assertEqual(self.client.get(f"/provider/facilities/{self.a.id}/israel-registration").status_code, 401)

    def test_session_cannot_write_to_another_facility(self) -> None:
        token = self._session(self.a)
        self.assertEqual(self._save(self.b.id, {"Authorization": f"Bearer {token}"}).status_code, 403)

    def test_bad_or_expired_or_revoked_links_fail(self) -> None:
        self.assertEqual(self.client.post("/provider/portal/redeem", json={"token": "nope"}).status_code, 401)

        token = self._invite(self.a)
        invite = self.db.query(FacilityPortalInvite).filter(FacilityPortalInvite.facility_id == self.a.id).one()
        invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        self.db.commit()
        self.assertEqual(self.client.post("/provider/portal/redeem", json={"token": token}).status_code, 401)

        session = self._session(self.a)
        self.client.post(f"/admin/portal/invites/{self.a.id}/revoke", headers={"x-admin-token": "admin-secret"})
        self.assertEqual(self._save(self.a.id, {"Authorization": f"Bearer {session}"}).status_code, 401)

    def test_new_invite_replaces_old_link(self) -> None:
        first = self._invite(self.a)
        self._invite(self.a)
        self.assertEqual(self.client.post("/provider/portal/redeem", json={"token": first}).status_code, 401)

    def test_email_claim_flow_is_closed_when_invite_only(self) -> None:
        response = self.client.post(
            f"/provider/facilities/{self.a.id}/identity/register/start",
            json={"email": "x@example.com", "role": "OWNER"},
        )
        self.assertEqual(response.status_code, 403)

    def test_legacy_body_user_id_still_works_when_sessions_not_required(self) -> None:
        owner = FacilityUser(facility_id=self.a.id, email="o@example.com", password_hash="x", role="OWNER")
        self.db.add(owner)
        self.db.commit()
        with mock.patch.dict(os.environ, {"OPTIME_PROVIDER_SESSION_REQUIRED": "0"}):
            response = self.client.post(
                f"/provider/facilities/{self.a.id}/photos",
                json={"user_id": owner.id, "url": "https://example.com/a.jpg"},
            )
        self.assertEqual(response.status_code, 200, response.text)


if __name__ == "__main__":
    unittest.main()
