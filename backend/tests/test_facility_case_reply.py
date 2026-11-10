from base64 import b64encode
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main
from app.database import Base, SessionLocal, engine
from app.models.facility_outreach import FacilityOutreachRequest
from app.services.facility_case_reply import CaseReplyIn, can_view, validated_reply


def test_facility_letter_and_private_response_round_trip(monkeypatch):
    Base.metadata.create_all(engine)
    monkeypatch.setenv("OPTIME_ADMIN_TOKEN", "test-admin")
    facility = {"test-case-reply": {"facility_name": "Test Community"}}
    admin = {"X-Admin-Token": "test-admin"}
    client = TestClient(main.app)
    create = lambda: client.post("/api/client-cases", json={"questionnaire_state": {}, "terms_accepted": True}).json()["case_token"]
    case, other_case = create(), create()
    path = f"/api/client-cases/{case}"
    draft = {"facility_id": "test-case-reply", "summary": "A family needs help getting dressed.",
             "items": [{"label": "Help getting dressed", "priority": "MUST"}], "intent": "visit"}

    with patch.object(main, "get_canonical_facility_index", return_value=facility), \
         patch.object(main.facility_outreach_service, "get_canonical_facility_index", return_value=facility), \
         patch.object(main.facility_outreach_service, "discover_contact", return_value=SimpleNamespace(email="intake@example.com")), \
         patch.object(main.facility_outreach_service.email_service, "send_email_detailed", return_value=SimpleNamespace(ok=True)) as send:
        assert client.post(f"{path}/facility-outreach", json=draft).status_code == 422
        draft["consent"] = True
        assert client.post(f"{path}/facility-outreach", json=draft).json()["status"] == "AWAITING_APPROVAL"
        send.assert_not_called()
        with SessionLocal() as db:
            row = db.query(FacilityOutreachRequest).filter_by(canonical_facility_id=draft["facility_id"]).order_by(FacilityOutreachRequest.id.desc()).first()
            outreach_id, token = row.id, row.response_token
        reply_url = f"/facility-outreach/{token}"
        approve_url = f"/facility-outreach-requests/{outreach_id}/approve-send"
        assert client.get(reply_url).status_code == 404
        assert client.post(approve_url).status_code in {401, 403}
        assert client.post(approve_url, headers=admin).json()["status"] == "SENT"
        send.assert_called_once()
        assert draft["summary"] not in send.call_args.kwargs["body_text"]
        assert client.get(reply_url).json()["case_letter"]["items"] == draft["items"]
        assert client.post(f"{reply_url}/submit", json={"room_types": []}).status_code == 404
        assert client.post(f"{reply_url}/case-reply", json={"answers": {"5": "yes"}}).status_code == 422
        attachment = b"%PDF-test"
        reply = {"answers": {"0": "depends"}, "notes": "Assessment required.", "monthly_price_cents": 650000,
                 "files": [{"name": "rates.pdf", "content": b64encode(attachment).decode()}]}
        assert client.post(f"{reply_url}/case-reply", json=reply).json()["status"] == "RESPONDED"
        assert client.post(f"{reply_url}/case-reply", json={"answers": {"0": "yes"}}).json()["status"] == "RESPONDED"
        assert client.get(reply_url).json()["case_letter"] is None
        [saved] = client.get(f"{path}/facility-replies").json()
        assert saved["reply"]["care_status"] == "NEEDS_FOLLOW_UP"
        assert saved["reply"]["answers"] == {"0": "depends"}
        assert saved["reply"]["evidence_status"] == "FACILITY_REPORTED"
        assert saved["files"] == ["rates.pdf"]
        assert client.get(f"/api/client-cases/{other_case}/facility-replies").json() == []
        assert client.get(f"/api/client-cases/{other_case}/facility-replies/{outreach_id}/files/0").status_code == 404
        assert client.get(f"{path}/facility-replies/{outreach_id}/files/0").content == attachment


def test_expired_letter_and_required_no():
    now = datetime.now(timezone.utc)
    assert not can_view(SimpleNamespace(status="SENT", sent_at=now - timedelta(days=14)), now)
    snapshot = {"items": [{"label": "Care", "priority": "MUST"}]}
    assert validated_reply(CaseReplyIn(answers={0: "no"}), snapshot)["care_status"] == "DOES_NOT_MEET_REQUIRED_NEED"
