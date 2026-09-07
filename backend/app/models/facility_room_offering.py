from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class FacilityRoomType(Base):
    """One bookable room type at a facility -- the Booking.com-style listing unit.

    Keyed by canonical_facility_id (the identity used across the decision engine and
    the personal report), not the SQL facilities.id, because most recommended
    facilities (assisted living, memory care, group homes) never get a CMS-sourced
    facilities row -- canonical_facility_id is the only id that covers all of them.

    Rows only exist once a facility has actually responded to an outreach query (or
    been entered manually from a known price sheet) -- there is no fabricated/default
    pricing. A facility with zero rows here simply hasn't been reached yet, and the
    facility page must render that as "not yet available", not as zero rooms.
    """

    __tablename__ = "facility_room_types"

    id = Column(Integer, primary_key=True, index=True)
    canonical_facility_id = Column(String(64), nullable=False, index=True)
    room_type_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False, default="")
    monthly_price_cents = Column(Integer, nullable=True)
    availability_status = Column(String(32), nullable=False, default="UNKNOWN")
    source = Column(String(32), nullable=False, default="OUTREACH")
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    photos = relationship("FacilityRoomPhoto", cascade="all, delete-orphan", passive_deletes=False)


class FacilityRoomPhoto(Base):
    """A photo attached to one room type. Deliberately not attached to the facility
    directly -- a photo of a shared studio isn't evidence about a private suite."""

    __tablename__ = "facility_room_photos"

    id = Column(Integer, primary_key=True, index=True)
    room_type_id = Column(Integer, ForeignKey("facility_room_types.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    caption = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
