from __future__ import annotations

"""Orchestrates outreach to a facility: find its contact (via
facility_contact_discovery_service), prepare a draft request for a person at OPTIME to
review, and -- only once a person explicitly approves it -- send it and record what
happened. No email is ever sent automatically; discovering a contact and requesting
outreach only produces a draft awaiting human approval (approve_and_send_outreach).
Populating the room-listing tables (facility_room_offering.py) from the facility's
reply is done by submit_outreach_response, called from the public form's endpoint.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.facility_outreach import FacilityOutreachRequest
from app.services import email_service
from app.services.facility_contact_discovery_service import discover_contact
from app.services.facility_parameter_service import get_canonical_facility_index
from app.services.facility_room_service import upsert_room_type

DEFAULT_FRONTEND_BASE_URL = "https://optime-nursing.vercel.app"


def frontend_base_url() -> str:
    return os.getenv("OPTIME_FRONTEND_BASE_URL", DEFAULT_FRONTEND_BASE_URL).rstrip("/")


def get_request_by_id(db: Session, request_id: int) -> Optional[FacilityOutreachRequest]:
    return db.query(FacilityOutreachRequest).filter(FacilityOutreachRequest.id == request_id).first()


def get_request_by_token(db: Session, response_token: str) -> Optional[FacilityOutreachRequest]:
    return db.query(FacilityOutreachRequest).filter(FacilityOutreachRequest.response_token == response_token).first()


def list_awaiting_approval(db: Session) -> list[FacilityOutreachRequest]:
    return (
        db.query(FacilityOutreachRequest)
        .filter(FacilityOutreachRequest.status == "AWAITING_APPROVAL")
        .order_by(FacilityOutreachRequest.requested_at)
        .all()
    )


def facility_name_for(canonical_facility_id: str) -> str:
    facility = get_canonical_facility_index().get(canonical_facility_id) or {}
    return str(facility.get("facility_name") or facility.get("name") or canonical_facility_id)


def response_url_for(outreach: FacilityOutreachRequest) -> str:
    return f"{frontend_base_url()}/facility-outreach/{outreach.response_token}"


def draft_email(outreach: FacilityOutreachRequest) -> dict:
    """Composes the outreach email content for review. Pure/deterministic -- never
    called with side effects, and never itself sends anything."""
    facility_name = facility_name_for(outreach.canonical_facility_id)
    response_url = response_url_for(outreach)
    subject = f"Room availability & pricing request -- {facility_name}"
    text = (
        f"Hello,\n\n"
        f"A family is currently considering {facility_name} through OPTIME, a senior-living "
        f"matching service, and asked us to check on your current room types, pricing, and "
        f"availability on their behalf.\n\n"
        f"Could you let us know:\n"
        f"- What room types you currently offer, with a short description of each\n"
        f"- Current monthly pricing per room type\n"
        f"- Current availability (open now / waitlist / not available)\n"
        f"- Any photos you'd like us to include\n\n"
        f"You can submit this directly here, no account needed:\n{response_url}\n\n"
        f"Thank you,\nOPTIME\n"
    )
    html = (
        f"<p>Hello,</p>"
        f"<p>A family is currently considering <strong>{facility_name}</strong> through OPTIME, "
        f"a senior-living matching service, and asked us to check on your current room types, "
        f"pricing, and availability on their behalf.</p>"
        f"<p>Could you let us know:</p>"
        f"<ul>"
        f"<li>What room types you currently offer, with a short description of each</li>"
        f"<li>Current monthly pricing per room type</li>"
        f"<li>Current availability (open now / waitlist / not available)</li>"
        f"<li>Any photos you'd like us to include</li>"
        f"</ul>"
        f'<p>You can submit this directly here, no account needed: <a href="{response_url}">{response_url}</a></p>'
        f"<p>Thank you,<br>OPTIME</p>"
    )
    return {"to": outreach.contact_email, "subject": subject, "body_text": text, "body_html": html}


def request_outreach(db: Session, canonical_facility_id: str) -> FacilityOutreachRequest:
    """Creates the outreach record and, if a public contact email can be found on the
    facility's own website, prepares it for review. Sends nothing -- see
    approve_and_send_outreach for the explicit, human-approved send step."""
    outreach = FacilityOutreachRequest(canonical_facility_id=canonical_facility_id, status="PENDING")
    db.add(outreach)
    db.commit()
    db.refresh(outreach)

    contact = discover_contact(db, canonical_facility_id)
    if contact is None:
        outreach.status = "FAILED_NO_CONTACT"
        outreach.failure_reason = "No public contact email could be found for this facility's own website."
    else:
        outreach.contact_email = contact.email
        outreach.status = "AWAITING_APPROVAL"
    db.commit()
    db.refresh(outreach)
    return outreach


def approve_and_send_outreach(db: Session, request_id: int) -> FacilityOutreachRequest:
    """The only function in this module that actually sends an email. Must only be
    called from an explicit, human-triggered admin action (never automatically) --
    the endpoint calling this is the human approval gate, this function does not
    re-check approval itself beyond requiring AWAITING_APPROVAL status."""
    outreach = get_request_by_id(db, request_id)
    if outreach is None:
        raise ValueError("unknown_outreach_request")
    if outreach.status != "AWAITING_APPROVAL":
        raise ValueError(f"outreach request is not awaiting approval (status={outreach.status})")

    draft = draft_email(outreach)
    result = email_service.send_email_detailed(
        subject=draft["subject"],
        body_text=draft["body_text"],
        body_html=draft["body_html"],
        recipients=[draft["to"]],
    )
    if result.ok:
        outreach.status = "SENT"
        outreach.sent_at = datetime.now(timezone.utc)
    else:
        outreach.status = "FAILED_SEND"
        outreach.failure_reason = result.message
    db.commit()
    db.refresh(outreach)
    return outreach


def submit_outreach_response(db: Session, response_token: str, room_types: list[dict]) -> FacilityOutreachRequest:
    outreach = get_request_by_token(db, response_token)
    if outreach is None:
        raise ValueError("unknown_response_token")

    for room in room_types:
        upsert_room_type(
            db,
            canonical_facility_id=outreach.canonical_facility_id,
            room_type_name=str(room["room_type_name"]),
            description=str(room.get("description") or ""),
            monthly_price_cents=room.get("monthly_price_cents"),
            availability_status=str(room.get("availability_status") or "UNKNOWN"),
            source="OUTREACH",
            photo_urls=room.get("photo_urls"),
        )

    outreach.status = "RESPONDED"
    outreach.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(outreach)
    return outreach
