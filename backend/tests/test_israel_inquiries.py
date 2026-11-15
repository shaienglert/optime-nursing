from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
import app.models.agent_execution  # noqa: F401
import app.models.clinical_evidence  # noqa: F401
import app.models.external_discovery  # noqa: F401
from app.models.facility import (
    Facility,
    FacilityAuditLog,
    FacilityFeedback,
    FacilityInquiry,
    FacilityPortalInvite,
    FacilityPortalSession,
    FacilityUser,
)

PREFIX = "TEST-INQ-"
REQUEST = {
    "room_type": "SHARED_2",
    "level": "NURSING",
    "move_in": "WITHIN_MONTH",
    "monthly_cap_ils": 15000,
    "contact_name": "רונית",
    "contact_phone": "050-1234567",
}


class InquiryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = mock.patch.dict(os.environ, {"OPTIME_ADMIN_TOKEN": "adm", "OPTIME_PROVIDER_SESSION_REQUIRED": "1"})
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
            for model in (FacilityFeedback, FacilityInquiry, FacilityPortalSession, FacilityPortalInvite, FacilityAuditLog, FacilityUser):
                self.db.query(model).filter(model.facility_id.in_(ids)).delete(synchronize_session=False)
            self.db.query(Facility).filter(Facility.id.in_(ids)).delete(synchronize_session=False)
        self.db.commit()

    def _session(self, facility) -> dict:
        invite = self.client.post("/admin/portal/invites", json={"facility_id": facility.id}, headers={"x-admin-token": "adm"}).json()
        token = self.client.post("/provider/portal/redeem", json={"token": invite["token"]}).json()["session_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_full_thread(self) -> None:
        created = self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST)
        self.assertEqual(created.status_code, 200, created.text)
        token = created.json()["token"]
        self.assertEqual(created.json()["link_path"], f"/he/inquiry/{token}")

        family = self.client.get(f"/api/il/inquiries/{token}").json()
        self.assertEqual(family["status"], "SENT")
        self.assertNotIn("contact_phone", family["request"])  # the family link never echoes contact details

        headers = self._session(self.a)
        listed = self.client.get(f"/provider/facilities/{self.a.id}/inquiries", headers=headers).json()["inquiries"]
        self.assertEqual(listed[0]["request"]["contact_phone"], "050-1234567")
        inquiry_id = listed[0]["inquiry_id"]

        asked = self.client.post(
            f"/provider/facilities/{self.a.id}/inquiries/{inquiry_id}/respond",
            json={"kind": "NEED_INFO", "text": "האם יש צורך בהזנה מיוחדת?"},
            headers=headers,
        )
        self.assertEqual(asked.json()["status"], "NEED_INFO")
        replied = self.client.post(f"/api/il/inquiries/{token}/reply", json={"text": "לא"}).json()
        self.assertEqual(replied["status"], "SENT")
        offered = self.client.post(
            f"/provider/facilities/{self.a.id}/inquiries/{inquiry_id}/respond",
            json={"kind": "ALTERNATIVE", "text": "חדר ליחיד", "monthly_ils": 17500},
            headers=headers,
        ).json()
        self.assertEqual(offered["status"], "ALTERNATIVE")
        thread = self.client.get(f"/api/il/inquiries/{token}").json()["messages"]
        self.assertEqual([m["kind"] for m in thread], ["REQUEST", "NEED_INFO", "REPLY", "ALTERNATIVE"])
        self.assertEqual(thread[-1]["monthly_ils"], 17500)

    def test_other_facility_cannot_read_or_answer(self) -> None:
        self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST)
        headers_b = self._session(self.b)
        self.assertEqual(self.client.get(f"/provider/facilities/{self.a.id}/inquiries", headers=headers_b).status_code, 403)
        inquiry = self.db.query(FacilityInquiry).filter(FacilityInquiry.facility_id == self.a.id).one()
        answered = self.client.post(
            f"/provider/facilities/{self.b.id}/inquiries/{inquiry.id}/respond", json={"kind": "ACCEPT"}, headers=headers_b
        )
        self.assertEqual(answered.status_code, 404)
        self.assertEqual(self.client.get(f"/provider/facilities/{self.a.id}/inquiries").status_code, 401)

    def test_validation(self) -> None:
        for bad in ({"move_in": ""}, {"contact_phone": "abc"}, {"room_type": "PALACE"}, {"monthly_cap_ils": -5}):
            response = self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json={**REQUEST, **bad})
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(self.client.post("/api/il/facilities/NOPE/inquiries", json=REQUEST).status_code, 404)
        self.assertEqual(self.client.get("/api/il/inquiries/not-a-token").status_code, 404)


if __name__ == "__main__":
    unittest.main()


class FeedbackTests(InquiryTests):
    RATING = {"relation": "VISITED", "ratings": {"staff": 5, "care": 4, "food": ""}, "recommend": "YES"}

    def _inquiry(self, cid: str) -> str:
        return self.client.post(f"/api/il/facilities/{cid}/inquiries", json=REQUEST).json()["token"]

    def test_only_a_family_with_a_request_link_can_rate(self):
        assert self.client.post("/api/il/inquiries/not-a-token/feedback", json=self.RATING).status_code == 404

    def test_validation(self):
        token = self._inquiry(PREFIX + "A")
        bad = [
            {**self.RATING, "relation": "HEARD_ABOUT_IT"},
            {**self.RATING, "ratings": {}},
            {**self.RATING, "ratings": {"staff": 6}},
            {**self.RATING, "recommend": ""},
        ]
        for payload in bad:
            assert self.client.post(f"/api/il/inquiries/{token}/feedback", json=payload).status_code == 400, payload

    def test_one_answer_per_request_and_hidden_until_enough_families(self):
        from app.services.israel_feedback import MIN_TO_SHOW, feedback_summary

        token = self._inquiry(PREFIX + "A")
        assert self.client.post(f"/api/il/inquiries/{token}/feedback", json=self.RATING).status_code == 200
        again = self.client.post(f"/api/il/inquiries/{token}/feedback", json={**self.RATING, "recommend": "NO"}).json()
        assert again["mine"]["recommend"] == "NO"
        assert again["mine"]["ratings"] == {"staff": 5, "care": 4}  # "not relevant" is not stored as a score
        summary = feedback_summary(self.db, self.a.id)
        assert summary == {"count": 1, "min_to_show": MIN_TO_SHOW, "shown": False}

        for _ in range(MIN_TO_SHOW - 1):
            t = self._inquiry(PREFIX + "A")
            self.client.post(f"/api/il/inquiries/{t}/feedback", json={**self.RATING, "relation": "MOVED_IN"})
        summary = feedback_summary(self.db, self.a.id)
        assert summary["shown"] and summary["count"] == MIN_TO_SHOW
        staff = next(a for a in summary["aspects"] if a["key"] == "staff")
        food = next(a for a in summary["aspects"] if a["key"] == "food")
        assert staff["average"] == 5 and food["average"] is None and food["answers"] == 0
        assert summary["recommend_pct"] == round(100 * (MIN_TO_SHOW - 1) / MIN_TO_SHOW)
        # Feedback belongs to the facility the request was sent to, not another.
        assert feedback_summary(self.db, self.b.id)["count"] == 0
        # Comments are never part of the public summary.
        assert "comment" not in str(summary)
