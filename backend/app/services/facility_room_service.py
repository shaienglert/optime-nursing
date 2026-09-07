from __future__ import annotations

"""Room-type listings for a facility -- the data behind the Booking.com-style facility
page (room types, descriptions, photos, price), keyed by canonical_facility_id.

Kept separate from the decision-engine/report code: this module never computes a
match or a recommendation, it only stores and serves what a facility has told OPTIME
about its own rooms. Populating it is future work (an automated outreach query to the
facility); this module is the storage/read side that a facility page can already rely
on, whether a given row got there by outreach or by manual entry.
"""

from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.facility_room_offering import FacilityRoomPhoto, FacilityRoomType

VALID_AVAILABILITY_STATUSES = {"AVAILABLE", "WAITLIST", "UNAVAILABLE", "UNKNOWN"}
VALID_SOURCES = {"OUTREACH", "MANUAL", "EXISTING_DATABASE"}


def list_room_types(db: Session, canonical_facility_id: str) -> List[FacilityRoomType]:
    return (
        db.query(FacilityRoomType)
        .options(joinedload(FacilityRoomType.photos))
        .filter(FacilityRoomType.canonical_facility_id == canonical_facility_id)
        .order_by(FacilityRoomType.id)
        .all()
    )


def upsert_room_type(
    db: Session,
    *,
    canonical_facility_id: str,
    room_type_name: str,
    description: str = "",
    monthly_price_cents: Optional[int] = None,
    availability_status: str = "UNKNOWN",
    source: str = "MANUAL",
    photo_urls: Optional[List[str]] = None,
) -> FacilityRoomType:
    if availability_status not in VALID_AVAILABILITY_STATUSES:
        raise ValueError(f"invalid availability_status: {availability_status}")
    if source not in VALID_SOURCES:
        raise ValueError(f"invalid source: {source}")

    room = (
        db.query(FacilityRoomType)
        .filter(
            FacilityRoomType.canonical_facility_id == canonical_facility_id,
            FacilityRoomType.room_type_name == room_type_name,
        )
        .first()
    )
    if room is None:
        room = FacilityRoomType(canonical_facility_id=canonical_facility_id, room_type_name=room_type_name)
        db.add(room)

    room.description = description
    room.monthly_price_cents = monthly_price_cents
    room.availability_status = availability_status
    room.source = source
    db.flush()

    if photo_urls is not None:
        db.query(FacilityRoomPhoto).filter(FacilityRoomPhoto.room_type_id == room.id).delete()
        for url in photo_urls:
            db.add(FacilityRoomPhoto(room_type_id=room.id, url=url))

    db.commit()
    db.refresh(room)
    return room
