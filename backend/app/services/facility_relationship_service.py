from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.facility_relationship import FacilityRelationshipDocument, FacilityRelationshipEvent
from app.models.facility_outreach import FacilityOutreachRequest, FacilitySalesCopilotInteraction
from app.services.facility_parameter_service import get_canonical_facility_index


EVENT_TYPES = {"CALL", "EMAIL", "WEBSITE", "MEETING", "NOTE", "STATUS_CHANGE", "SALES_COPILOT"}
CHANNELS = {"PHONE", "EMAIL", "WEBSITE", "VIDEO", "IN_PERSON", "INTERNAL", "OTHER"}
DIRECTIONS = {"INBOUND", "OUTBOUND", "INTERNAL", "AUTOMATED"}
DOCUMENT_TYPES = {"CONTRACT", "ADDENDUM", "LICENSE", "CORRESPONDENCE", "PRICING", "INSURANCE", "OTHER"}


def _facility(canonical_facility_id: str) -> dict[str, Any]:
    facility = get_canonical_facility_index().get(canonical_facility_id)
    if not facility:
        raise ValueError("Canonical facility not found")
    return facility


def search_facilities(query: str, limit: int = 20) -> list[dict[str, Any]]:
    needle = query.strip().lower()
    rows = []
    for canonical_id, facility in get_canonical_facility_index().items():
        haystack = " ".join(str(facility.get(key) or "") for key in ("name", "city", "address", "zip"))
        if needle and needle not in haystack.lower():
            continue
        rows.append({
            "canonical_facility_id": canonical_id,
            "facility_name": facility.get("name") or canonical_id,
            "city": facility.get("city"), "state": facility.get("state"),
            "address": facility.get("address"), "phone": facility.get("phone"),
            "canonical_type": facility.get("canonical_type"),
        })
    rows.sort(key=lambda row: (str(row["facility_name"]).lower(), row["canonical_facility_id"]))
    return rows[: max(1, min(limit, 100))]


def _iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value else None


def facility_record(db: Session, canonical_facility_id: str) -> dict[str, Any]:
    facility = _facility(canonical_facility_id)
    events = db.query(FacilityRelationshipEvent).filter(
        FacilityRelationshipEvent.canonical_facility_id == canonical_facility_id
    ).order_by(FacilityRelationshipEvent.occurred_at.desc(), FacilityRelationshipEvent.id.desc()).all()
    documents = db.query(FacilityRelationshipDocument).filter(
        FacilityRelationshipDocument.canonical_facility_id == canonical_facility_id
    ).order_by(FacilityRelationshipDocument.created_at.desc(), FacilityRelationshipDocument.id.desc()).all()
    timeline = [{
        "id": f"event-{row.id}", "event_type": row.event_type, "channel": row.channel,
        "direction": row.direction, "subject": row.subject, "summary": row.summary,
        "representative_name": row.representative_name, "contact_name": row.contact_name,
        "source": row.source, "occurred_at": _iso(row.occurred_at), "created_at": _iso(row.created_at),
    } for row in events]
    seen_copilot_questions = {row.subject for row in events if row.event_type == "SALES_COPILOT" and row.subject}
    facility_name = str(facility.get("name") or "")
    if facility_name:
        interactions = db.query(FacilitySalesCopilotInteraction).filter(
            FacilitySalesCopilotInteraction.facility_name == facility_name
        ).order_by(FacilitySalesCopilotInteraction.created_at.desc()).all()
        for row in interactions:
            if row.question[:255] in seen_copilot_questions:
                continue
            timeline.append({
                "id": f"copilot-{row.id}", "event_type": "SALES_COPILOT", "channel": "INTERNAL",
                "direction": "AUTOMATED", "subject": row.question[:255],
                "summary": f"Question asked during {row.call_stage or 'facility conversation'}; confidence {row.confidence}.",
                "representative_name": None, "contact_name": None, "source": "SALES_COPILOT_HISTORY",
                "occurred_at": _iso(row.created_at), "created_at": _iso(row.created_at),
            })
    outreach_rows = db.query(FacilityOutreachRequest).filter(
        FacilityOutreachRequest.canonical_facility_id == canonical_facility_id
    ).order_by(FacilityOutreachRequest.requested_at.desc()).all()
    for row in outreach_rows:
        timeline.append({
            "id": f"outreach-{row.id}", "event_type": "EMAIL", "channel": "EMAIL",
            "direction": "OUTBOUND", "subject": "Facility profile outreach",
            "summary": f"Outreach status: {row.status}." + (f" Failure: {row.failure_reason}" if row.failure_reason else ""),
            "representative_name": None, "contact_name": row.contact_email, "source": "OUTREACH_WORKFLOW",
            "occurred_at": _iso(row.responded_at or row.sent_at or row.requested_at), "created_at": _iso(row.requested_at),
        })
    timeline.sort(key=lambda item: (item.get("occurred_at") or "", str(item["id"])), reverse=True)
    return {
        "canonical_facility_id": canonical_facility_id,
        "facility": {
            "name": facility.get("name") or canonical_facility_id, "address": facility.get("address"),
            "city": facility.get("city"), "state": facility.get("state"), "zip": facility.get("zip"),
            "phone": facility.get("phone"), "website": facility.get("website"),
            "canonical_type": facility.get("canonical_type"), "match_status": facility.get("match_status"),
        },
        "documents": [{
            "id": row.id, "title": row.title, "document_type": row.document_type,
            "document_url": row.document_url, "status": row.status,
            "effective_date": _iso(row.effective_date), "expiration_date": _iso(row.expiration_date),
            "notes": row.notes, "added_by": row.added_by, "created_at": _iso(row.created_at),
        } for row in documents],
        "timeline": timeline,
        "counts": {"documents": len(documents), "timeline_events": len(timeline)},
    }


def add_event(db: Session, canonical_facility_id: str, payload: dict[str, Any]) -> FacilityRelationshipEvent:
    _facility(canonical_facility_id)
    event_type = str(payload.get("event_type") or "NOTE").upper()
    channel = str(payload.get("channel") or "OTHER").upper()
    direction = str(payload.get("direction") or "INTERNAL").upper()
    if event_type not in EVENT_TYPES or channel not in CHANNELS or direction not in DIRECTIONS:
        raise ValueError("Unsupported event type, channel, or direction")
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        raise ValueError("Event summary is required")
    row = FacilityRelationshipEvent(
        canonical_facility_id=canonical_facility_id, event_type=event_type, channel=channel,
        direction=direction, subject=(str(payload.get("subject") or "").strip() or None),
        summary=summary, representative_name=(str(payload.get("representative_name") or "").strip() or None),
        contact_name=(str(payload.get("contact_name") or "").strip() or None),
        source=str(payload.get("source") or "MANUAL").upper(),
        occurred_at=payload.get("occurred_at") or datetime.now(timezone.utc),
    )
    db.add(row); db.commit(); db.refresh(row)
    return row


def add_document(db: Session, canonical_facility_id: str, payload: dict[str, Any]) -> FacilityRelationshipDocument:
    _facility(canonical_facility_id)
    document_type = str(payload.get("document_type") or "OTHER").upper()
    if document_type not in DOCUMENT_TYPES:
        raise ValueError("Unsupported document type")
    document_url = str(payload.get("document_url") or "").strip()
    parsed = urlparse(document_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Document URL must be a valid HTTPS or HTTP link")
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("Document title is required")
    row = FacilityRelationshipDocument(
        canonical_facility_id=canonical_facility_id, title=title, document_type=document_type,
        document_url=document_url, status=str(payload.get("status") or "ACTIVE").upper(),
        effective_date=payload.get("effective_date"), expiration_date=payload.get("expiration_date"),
        notes=(str(payload.get("notes") or "").strip() or None),
        added_by=(str(payload.get("added_by") or "").strip() or None),
    )
    db.add(row); db.commit(); db.refresh(row)
    return row
