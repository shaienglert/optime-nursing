from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.facility_outreach import FacilityOutreachRequest
from app.services import facility_relationship_service as service


FACILITY_ID = "NV-TEST-001"
FACILITY = {"name": "Test Community", "city": "Las Vegas", "state": "NV", "address": "1 Main St"}


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_facility_record_combines_manual_activity_documents_and_outreach() -> None:
    db = _db()
    with patch.object(service, "get_canonical_facility_index", return_value={FACILITY_ID: FACILITY}):
        service.add_event(db, FACILITY_ID, {"event_type": "CALL", "channel": "PHONE", "direction": "OUTBOUND", "summary": "Spoke with admissions."})
        service.add_document(db, FACILITY_ID, {"title": "Facility agreement", "document_type": "CONTRACT", "document_url": "https://example.com/contract.pdf"})
        db.add(FacilityOutreachRequest(canonical_facility_id=FACILITY_ID, status="SENT", contact_email="admissions@example.com"))
        db.commit()
        record = service.facility_record(db, FACILITY_ID)

    assert record["facility"]["name"] == "Test Community"
    assert record["counts"] == {"documents": 1, "timeline_events": 2}
    assert {item["source"] for item in record["timeline"]} == {"MANUAL", "OUTREACH_WORKFLOW"}


def test_document_rejects_non_web_location() -> None:
    db = _db()
    with patch.object(service, "get_canonical_facility_index", return_value={FACILITY_ID: FACILITY}):
        try:
            service.add_document(db, FACILITY_ID, {"title": "Unsafe", "document_url": "file:///tmp/private.pdf"})
        except ValueError as exc:
            assert "valid HTTPS or HTTP" in str(exc)
        else:
            raise AssertionError("Expected invalid document location to be rejected")
