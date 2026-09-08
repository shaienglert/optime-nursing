import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


def _new_response_token() -> str:
    # A public, URL-safe, unguessable token -- this is what lets a facility's own
    # marketing/sales contact submit room data through a link in an email, with no
    # OPTIME login. Same shape and rationale as personal_report_case.case_token.
    return uuid.uuid4().hex


class FacilityContact(Base):
    """The best known outreach contact for a facility, discovered from its own public
    website (never guessed/fabricated) -- or entered manually as a fallback.

    Kept separate from FacilityOutreachRequest: a contact, once found, is reusable
    across multiple outreach requests to the same facility over time.
    """

    __tablename__ = "facility_contacts"

    id = Column(Integer, primary_key=True, index=True)
    canonical_facility_id = Column(String(64), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    contact_role = Column(String(32), nullable=False, default="UNKNOWN")
    source_url = Column(Text, nullable=False)
    source = Column(String(32), nullable=False, default="WEBSITE_DISCOVERY")
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FacilityOutreachRequest(Base):
    """One outreach attempt to a facility, asking for room types, pricing, photos,
    and current availability. Created the moment a client asks OPTIME to follow up
    with a specific facility -- this is the record of that ask, not of the facility's
    reply (the reply is written directly into facility_room_offering.py's tables).
    """

    __tablename__ = "facility_outreach_requests"

    id = Column(Integer, primary_key=True, index=True)
    canonical_facility_id = Column(String(64), nullable=False, index=True)
    response_token = Column(String(32), nullable=False, unique=True, index=True, default=_new_response_token)
    status = Column(String(32), nullable=False, default="PENDING")
    contact_email = Column(String(255), nullable=True)
    failure_reason = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
