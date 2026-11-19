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
    FacilityNotification,
    FacilityPortalInvite,
    FacilityPortalSession,
    FacilityUser,
    FacilityVisit,
    FacilityVisitSchedule,
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
        self.env = mock.patch.dict(os.environ, {"OPTIME_ADMIN_TOKEN": "adm", "OPTIME_PROVIDER_SESSION_REQUIRED": "1", "OOMNIK_RATE_LIMIT_DISABLED": "1"})
        self.env.start()
        from app.services import israel_rate_limit

        israel_rate_limit.reset()
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
            for model in (FacilityNotification, FacilityVisitSchedule, FacilityVisit, FacilityFeedback, FacilityInquiry, FacilityPortalSession, FacilityPortalInvite, FacilityAuditLog, FacilityUser):
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


class VisitTests(InquiryTests):
    """Owner flow 2026-11-17: results -> facility page -> visit."""

    @staticmethod
    def _day(offset):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        return (datetime.now(ZoneInfo("Asia/Jerusalem")).date() + timedelta(days=offset)).isoformat()

    def _inquiry(self) -> str:
        return self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST).json()["token"]

    def _ask(self, token, slots, **extra):
        return self.client.post(f"/api/il/inquiries/{token}/visit", json={"slots": slots, **extra})

    def test_family_proposal_is_validated(self):
        token = self._inquiry()
        bad = [
            [],
            [{"date": self._day(0), "part": "MORNING"}],  # today is too late
            [{"date": self._day(90), "part": "MORNING"}],  # beyond the horizon
            [{"date": self._day(2), "part": "MIDNIGHT"}],
            [{"date": self._day(d), "part": "MORNING"} for d in (2, 3, 4, 5)],  # more than three
        ]
        for slots in bad:
            self.assertEqual(self._ask(token, slots).status_code, 400, slots)
        self.assertEqual(self._ask(token, [{"date": self._day(2), "part": "MORNING"}], visitors=12).status_code, 400)

    def test_confirm_one_of_the_family_dates_and_download_calendar(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        token = self._inquiry()
        asked = self._ask(token, [{"date": self._day(3), "part": "MORNING"}, {"date": self._day(5), "part": "AFTERNOON"}], visitors=2).json()
        self.assertEqual(asked["status"], "REQUESTED")
        self.assertEqual(len(asked["slots"]), 2)
        inquiry_id = self.client.get(f"/api/il/inquiries/{token}").json()["inquiry_id"]
        url = f"/provider/facilities/{self.a.id}/inquiries/{inquiry_id}/visit"
        self.assertEqual(self.client.post(url, json={"action": "CONFIRM", "slot_index": 1, "time": "16:30"}).status_code, 401)
        headers = self._session(self.a)
        self.assertEqual(self.client.post(url, json={"action": "CONFIRM", "slot_index": 7, "time": "16:30"}, headers=headers).status_code, 400)
        self.assertEqual(self.client.post(url, json={"action": "CONFIRM", "slot_index": 1, "time": "25:00"}, headers=headers).status_code, 400)
        done = self.client.post(url, json={"action": "CONFIRM", "slot_index": 1, "time": "16:30"}, headers=headers).json()
        self.assertEqual(done["status"], "CONFIRMED")
        self.assertEqual(done["confirmed"]["date"], self._day(5))
        family = self.client.get(f"/api/il/inquiries/{token}").json()
        self.assertEqual(family["visit"]["status"], "CONFIRMED")
        self.assertNotIn("contact_phone", family["request"])
        ics = self.client.get(f"/api/il/inquiries/{token}/visit.ics")
        self.assertEqual(ics.status_code, 200)
        start = datetime.fromisoformat(f"{self._day(5)}T16:30:00").replace(tzinfo=ZoneInfo("Asia/Jerusalem"))
        self.assertIn("DTSTART:" + start.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ"), ics.text)
        # A confirmed visit is changed only after cancelling it.
        self.assertEqual(self._ask(token, [{"date": self._day(6), "part": "NOON"}]).status_code, 400)

    def test_facility_proposal_needs_the_familys_approval(self):
        token = self._inquiry()
        self._ask(token, [{"date": self._day(2), "part": "MORNING"}])
        inquiry_id = self.client.get(f"/api/il/inquiries/{token}").json()["inquiry_id"]
        headers = self._session(self.a)
        url = f"/provider/facilities/{self.a.id}/inquiries/{inquiry_id}/visit"
        proposed = self.client.post(url, json={"action": "PROPOSE", "date": self._day(4), "time": "11:00", "note": "נוח לנו יותר"}, headers=headers).json()
        self.assertEqual(proposed["status"], "FACILITY_PROPOSED")
        self.assertEqual(self.client.get(f"/api/il/inquiries/{token}/visit.ics").status_code, 404)  # not agreed yet
        accepted = self.client.post(f"/api/il/inquiries/{token}/visit/answer", json={"action": "ACCEPT"}).json()
        self.assertEqual(accepted["status"], "CONFIRMED")
        cancelled = self.client.post(f"/api/il/inquiries/{token}/visit/answer", json={"action": "CANCEL"}).json()
        self.assertEqual(cancelled["status"], "CANCELLED")
        again = self._ask(token, [{"date": self._day(7), "part": "NOON"}]).json()
        self.assertEqual(again["status"], "REQUESTED")
        self.assertEqual([h["action"] for h in again["history"]], ["REQUESTED", "PROPOSE", "ACCEPTED", "CANCELLED", "REQUESTED"])

    def test_another_facility_cannot_touch_the_visit(self):
        token = self._inquiry()
        self._ask(token, [{"date": self._day(2), "part": "MORNING"}])
        inquiry_id = self.client.get(f"/api/il/inquiries/{token}").json()["inquiry_id"]
        other = self._session(self.b)
        response = self.client.post(
            f"/provider/facilities/{self.b.id}/inquiries/{inquiry_id}/visit",
            json={"action": "CONFIRM", "slot_index": 0, "time": "10:00"},
            headers=other,
        )
        self.assertEqual(response.status_code, 404)


class VisitCalendarTests(VisitTests):
    """The facility publishes visiting hours; families book an open slot directly."""

    SCHEDULE = {
        "weekly": {d: [["10:00", "12:00"]] for d in ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")},
        "slot_minutes": 60,
        "capacity": 1,
        "lead_hours": 0,
        "modes": ["IN_PERSON"],
    }

    def _publish(self, **overrides):
        return self.client.put(f"/provider/facilities/{self.a.id}/visit-schedule", json={**self.SCHEDULE, **overrides}, headers=self._session(self.a))

    def test_schedule_is_validated_and_needs_a_session(self):
        self.assertEqual(self.client.put(f"/provider/facilities/{self.a.id}/visit-schedule", json=self.SCHEDULE).status_code, 401)
        self.assertEqual(self._publish(weekly={"SUN": [["12:00", "10:00"]]}).status_code, 400)
        self.assertEqual(self._publish(weekly={"SUN": [["10:00", "12:00"], ["11:00", "13:00"]]}).status_code, 400)
        self.assertEqual(self._publish(slot_minutes=7).status_code, 400)
        self.assertEqual(self._publish().status_code, 200)

    def test_calendar_respects_hours_closed_dates_and_lead_time(self):
        token = self._inquiry()
        self.assertFalse(self.client.get(f"/api/il/inquiries/{token}/visit/slots").json()["configured"])
        self._publish(blocked_dates=[self._day(3)], lead_hours=48)
        calendar = self.client.get(f"/api/il/inquiries/{token}/visit/slots").json()
        by_day = {d["date"]: [s["time"] for s in d["slots"]] for d in calendar["days"]}
        self.assertEqual(by_day[self._day(3)], [])  # closed date
        self.assertEqual(by_day[self._day(5)], ["10:00", "11:00"])  # two one-hour slots
        self.assertEqual(by_day[self._day(0)], [])  # inside the 48h lead time
        self.assertEqual(len(calendar["days"]), 31)

    def test_booking_confirms_at_once_and_fills_the_slot(self):
        self._publish()
        first, second = self._inquiry(), self._inquiry()
        booked = self.client.post(f"/api/il/inquiries/{first}/visit/book", json={"date": self._day(4), "time": "10:00", "visitors": 2})
        self.assertEqual(booked.status_code, 200, booked.text)
        self.assertEqual(booked.json()["status"], "CONFIRMED")
        self.assertEqual(booked.json()["confirmed"]["time"], "10:00")
        # The slot held one family; it is gone for the next one.
        times = {d["date"]: [s["time"] for s in d["slots"]] for d in self.client.get(f"/api/il/inquiries/{second}/visit/slots").json()["days"]}
        self.assertEqual(times[self._day(4)], ["11:00"])
        taken = self.client.post(f"/api/il/inquiries/{second}/visit/book", json={"date": self._day(4), "time": "10:00"})
        self.assertEqual(taken.status_code, 409)
        self.assertEqual(self.client.post(f"/api/il/inquiries/{second}/visit/book", json={"date": self._day(4), "time": "10:30"}).status_code, 409)  # not a slot
        self.assertEqual(self.client.post(f"/api/il/inquiries/{second}/visit/book", json={"date": self._day(4), "time": "11:00", "mode": "VIDEO"}).status_code, 400)
        # Cancelling frees the slot again.
        self.client.post(f"/api/il/inquiries/{first}/visit/answer", json={"action": "CANCEL"})
        self.assertEqual(self.client.post(f"/api/il/inquiries/{second}/visit/book", json={"date": self._day(4), "time": "10:00"}).status_code, 200)


class NotificationTests(VisitTests):
    """Owner 2026-11-18: facility and family hear about inquiries and visits by email."""

    def setUp(self):
        super().setUp()
        from app.services import israel_notifications

        self.sent = []
        israel_notifications.set_sender(lambda **m: (self.sent.append(m), (True, "OK"))[1])
        self.notify_env = mock.patch.dict(os.environ, {"OOMNIK_NOTIFY_SYNC": "1", "OOMNIK_PUBLIC_URL": "https://example.test"})
        self.notify_env.start()

    def tearDown(self):
        from app.services import israel_notifications

        israel_notifications.set_sender(None)
        self.notify_env.stop()
        super().tearDown()

    def _facility_email(self):
        headers = self._session(self.a)
        self.db.query(FacilityPortalInvite).filter(FacilityPortalInvite.facility_id == self.a.id).update({"contact_email": "office@facility-a.co.il"})
        self.db.commit()
        return headers

    def _rows(self):
        self.db.expire_all()
        return [(r.audience, r.event, r.status) for r in self.db.query(FacilityNotification).order_by(FacilityNotification.id)]

    def test_inquiry_notifies_facility_and_gives_family_its_link(self):
        self._facility_email()
        created = self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json={**REQUEST, "contact_email": "ronit@example.com"}).json()
        token = created["token"]
        self.assertTrue(created["email_sent_to_family"])
        self.assertEqual(self._rows(), [("FACILITY", "NEW_INQUIRY", "SENT"), ("FAMILY", "INQUIRY_SENT", "SENT")])
        facility_mail, family_mail = self.sent
        self.assertEqual(facility_mail["recipients"], ["office@facility-a.co.il"])
        self.assertIn(f"https://example.test/provider/{self.a.id}/israel", facility_mail["body_text"])
        self.assertNotIn("050-1234567", facility_mail["body_text"])  # contact details stay in the portal
        self.assertNotIn(token, facility_mail["body_text"])
        self.assertEqual(family_mail["recipients"], ["ronit@example.com"])
        self.assertIn(f"https://example.test/he/inquiry/{token}", family_mail["body_text"])

    def test_no_family_email_is_recorded_not_sent_and_bad_email_rejected(self):
        self._facility_email()
        self.assertEqual(self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json={**REQUEST, "contact_email": "not-an-email"}).status_code, 400)
        self._inquiry()
        self.assertEqual(self._rows(), [("FACILITY", "NEW_INQUIRY", "SENT"), ("FAMILY", "INQUIRY_SENT", "SKIPPED_NO_ADDRESS")])

    def test_facility_without_address_and_synthetic_facility_are_never_emailed(self):
        self._inquiry()
        self.assertEqual(self._rows()[0], ("FACILITY", "NEW_INQUIRY", "SKIPPED_NO_ADDRESS"))
        self.a.cms_id = "IL-SYN-TEST-INQ"
        self.db.commit()
        try:
            self._facility_email()
            self._inquiry()
            self.assertEqual(self._rows()[-2], ("FACILITY", "NEW_INQUIRY", "SKIPPED_SYNTHETIC"))
            with mock.patch.dict(os.environ, {"OOMNIK_NOTIFY_SYNTHETIC_TO": "tester@oomnik.co.il"}):
                self._inquiry()
            self.assertEqual(self._rows()[-2], ("FACILITY", "NEW_INQUIRY", "SENT"))
            self.assertEqual(self.sent[-1]["recipients"], ["tester@oomnik.co.il"])
        finally:
            self.a.cms_id = PREFIX + "A"
            self.db.commit()

    def test_visit_events_reach_the_other_side(self):
        headers = self._facility_email()
        token = self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json={**REQUEST, "contact_email": "ronit@example.com"}).json()["token"]
        self.sent.clear()
        self.assertEqual(self._ask(token, [{"date": self._day(3), "part": "MORNING"}]).status_code, 200)
        iid = self.db.query(FacilityInquiry).filter(FacilityInquiry.facility_id == self.a.id).one().id
        r = self.client.post(f"/provider/facilities/{self.a.id}/inquiries/{iid}/visit", json={"action": "CONFIRM", "slot_index": 0, "time": "10:30"}, headers=headers)
        self.assertEqual(r.status_code, 200, r.text)
        self.client.post(f"/api/il/inquiries/{token}/visit/answer", json={"action": "CANCEL"})
        events = [(r[0], r[1]) for r in self._rows()[2:]]
        self.assertEqual(events, [("FACILITY", "VISIT_REQUESTED"), ("FAMILY", "VISIT_CONFIRMED"), ("FACILITY", "VISIT_CANCELLED")])
        confirmed = self.sent[1]
        self.assertIn("10:30", confirmed["body_text"])
        self.assertIn("הקישור האישי מהמייל הראשון", confirmed["body_text"])  # facility-side events never carry the token

    def test_smtp_failure_never_breaks_the_inquiry(self):
        from app.services import israel_notifications

        def boom(**_):
            raise RuntimeError("smtp down")

        israel_notifications.set_sender(boom)
        self._facility_email()
        created = self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(self._rows()[0][2], "NOT_SENT")


class InquiryRateLimitTests(InquiryTests):
    def setUp(self):
        super().setUp()
        from app.services import israel_rate_limit

        israel_rate_limit.reset()
        self.limit_env = mock.patch.dict(os.environ, {"OOMNIK_RATE_LIMIT_DISABLED": "0"})
        self.limit_env.start()

    def tearDown(self):
        self.limit_env.stop()
        super().tearDown()

    def test_fourth_inquiry_to_one_facility_from_one_address_is_refused(self):
        headers = {"x-oomnik-client-ip": "203.0.113.7"}
        codes = [self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST, headers=headers).status_code for _ in range(4)]
        self.assertEqual(codes, [200, 200, 200, 429])
        # Form mistakes never count: a family fixing its form is not locked out.
        from app.services import israel_rate_limit

        israel_rate_limit.reset()
        for _ in range(5):
            self.assertEqual(self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json={**REQUEST, "contact_phone": "abc"}, headers=headers).status_code, 400)
        self.assertEqual(self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST, headers=headers).status_code, 200)
        other = self.client.post(f"/api/il/facilities/{self.a.cms_id}/inquiries", json=REQUEST, headers={"x-oomnik-client-ip": "203.0.113.8"})
        self.assertEqual(other.status_code, 200)
