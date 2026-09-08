from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.database import Base, SessionLocal, engine
import app.models.facility_outreach  # noqa: F401 -- registers tables on Base
import app.models.facility_room_offering  # noqa: F401
from app.services import facility_outreach_service as svc
from app.services.facility_contact_discovery_service import FacilityContact
from app.services.facility_room_service import list_room_types

Base.metadata.create_all(bind=engine)

_FAKE_CANONICAL_INDEX = {"canonical-x": {"facility_name": "Testville Manor", "city": "Las Vegas"}}


class FacilityOutreachServiceTests(unittest.TestCase):
    def _db(self):
        return SessionLocal()

    def test_request_outreach_with_no_discoverable_contact_fails_honestly(self) -> None:
        db = self._db()
        try:
            with patch("app.services.facility_outreach_service.discover_contact", return_value=None):
                outreach = svc.request_outreach(db, "canonical-x")
            self.assertEqual(outreach.status, "FAILED_NO_CONTACT")
            self.assertIsNone(outreach.contact_email)
            self.assertTrue(outreach.failure_reason)
        finally:
            db.close()

    def test_request_outreach_with_contact_awaits_approval_and_sends_nothing(self) -> None:
        db = self._db()
        try:
            fake_contact = FacilityContact(canonical_facility_id="canonical-x", email="marketing@testville.com", contact_role="MARKETING_SALES", source_url="https://testville.com")
            with patch("app.services.facility_outreach_service.discover_contact", return_value=fake_contact), patch(
                "app.services.facility_outreach_service.get_canonical_facility_index", return_value=_FAKE_CANONICAL_INDEX
            ), patch("app.services.facility_outreach_service.email_service.send_email_detailed") as mock_send:
                outreach = svc.request_outreach(db, "canonical-x")
            mock_send.assert_not_called()
            self.assertEqual(outreach.status, "AWAITING_APPROVAL")
            self.assertEqual(outreach.contact_email, "marketing@testville.com")
        finally:
            db.close()

    def test_draft_email_is_pure_and_mentions_facility_and_response_link(self) -> None:
        db = self._db()
        try:
            with patch("app.services.facility_outreach_service.get_canonical_facility_index", return_value=_FAKE_CANONICAL_INDEX):
                outreach = app.models.facility_outreach.FacilityOutreachRequest(
                    canonical_facility_id="canonical-x", status="AWAITING_APPROVAL", contact_email="marketing@testville.com"
                )
                db.add(outreach)
                db.commit()
                db.refresh(outreach)
                draft = svc.draft_email(outreach)
            self.assertEqual(draft["to"], "marketing@testville.com")
            self.assertIn("Testville Manor", draft["subject"])
            self.assertIn(outreach.response_token, draft["body_text"])
            self.assertIn(outreach.response_token, draft["body_html"])
        finally:
            db.close()

    def test_approve_and_send_requires_awaiting_approval_status(self) -> None:
        db = self._db()
        try:
            outreach = app.models.facility_outreach.FacilityOutreachRequest(canonical_facility_id="canonical-x", status="FAILED_NO_CONTACT")
            db.add(outreach)
            db.commit()
            db.refresh(outreach)
            with self.assertRaises(ValueError):
                svc.approve_and_send_outreach(db, outreach.id)
        finally:
            db.close()

    def test_approve_and_send_success_updates_status_and_calls_email_service_once(self) -> None:
        db = self._db()
        try:
            outreach = app.models.facility_outreach.FacilityOutreachRequest(
                canonical_facility_id="canonical-x", status="AWAITING_APPROVAL", contact_email="marketing@testville.com"
            )
            db.add(outreach)
            db.commit()
            db.refresh(outreach)

            ok_result = MagicMock(ok=True, message="sent")
            with patch("app.services.facility_outreach_service.get_canonical_facility_index", return_value=_FAKE_CANONICAL_INDEX), patch(
                "app.services.facility_outreach_service.email_service.send_email_detailed", return_value=ok_result
            ) as mock_send:
                result = svc.approve_and_send_outreach(db, outreach.id)
            mock_send.assert_called_once()
            self.assertEqual(mock_send.call_args.kwargs["recipients"], ["marketing@testville.com"])
            self.assertEqual(result.status, "SENT")
            self.assertIsNotNone(result.sent_at)
        finally:
            db.close()

    def test_approve_and_send_failure_records_failure_reason(self) -> None:
        db = self._db()
        try:
            outreach = app.models.facility_outreach.FacilityOutreachRequest(
                canonical_facility_id="canonical-x", status="AWAITING_APPROVAL", contact_email="marketing@testville.com"
            )
            db.add(outreach)
            db.commit()
            db.refresh(outreach)

            bad_result = MagicMock(ok=False, message="SMTP host is not configured")
            with patch("app.services.facility_outreach_service.get_canonical_facility_index", return_value=_FAKE_CANONICAL_INDEX), patch(
                "app.services.facility_outreach_service.email_service.send_email_detailed", return_value=bad_result
            ):
                result = svc.approve_and_send_outreach(db, outreach.id)
            self.assertEqual(result.status, "FAILED_SEND")
            self.assertEqual(result.failure_reason, "SMTP host is not configured")
        finally:
            db.close()

    def test_submit_outreach_response_writes_rooms_and_marks_responded(self) -> None:
        db = self._db()
        try:
            outreach = app.models.facility_outreach.FacilityOutreachRequest(canonical_facility_id="canonical-submit", status="SENT")
            db.add(outreach)
            db.commit()
            db.refresh(outreach)

            result = svc.submit_outreach_response(
                db,
                outreach.response_token,
                [
                    {
                        "room_type_name": "Private Suite",
                        "description": "A private room",
                        "monthly_price_cents": 500000,
                        "availability_status": "AVAILABLE",
                        "photo_urls": ["https://example.com/a.jpg"],
                    }
                ],
            )
            self.assertEqual(result.status, "RESPONDED")
            self.assertIsNotNone(result.responded_at)

            rooms = list_room_types(db, "canonical-submit")
            self.assertEqual(len(rooms), 1)
            self.assertEqual(rooms[0].source, "OUTREACH")
            self.assertEqual(rooms[0].monthly_price_cents, 500000)
        finally:
            db.close()

    def test_submit_outreach_response_unknown_token_raises(self) -> None:
        db = self._db()
        try:
            with self.assertRaises(ValueError):
                svc.submit_outreach_response(db, "not-a-real-token", [])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
