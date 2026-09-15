from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class FacilityRelationshipEvent(Base):
    """One durable item in a facility's commercial relationship timeline."""

    __tablename__ = "facility_relationship_events"

    id = Column(Integer, primary_key=True, index=True)
    canonical_facility_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    channel = Column(String(32), nullable=False, default="OTHER")
    direction = Column(String(16), nullable=False, default="INTERNAL")
    subject = Column(String(255), nullable=True)
    summary = Column(Text, nullable=False)
    representative_name = Column(String(160), nullable=True)
    contact_name = Column(String(160), nullable=True)
    source = Column(String(40), nullable=False, default="MANUAL")
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FacilityRelationshipDocument(Base):
    """Metadata and secure location for a document associated with a facility."""

    __tablename__ = "facility_relationship_documents"

    id = Column(Integer, primary_key=True, index=True)
    canonical_facility_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    document_type = Column(String(40), nullable=False, default="OTHER", index=True)
    document_url = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="ACTIVE")
    effective_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    added_by = Column(String(160), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
