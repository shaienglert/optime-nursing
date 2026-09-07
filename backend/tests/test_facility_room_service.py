from __future__ import annotations

import pytest

from app.database import Base, SessionLocal, engine
import app.models.facility_room_offering  # noqa: F401 -- registers tables on Base
from app.services.facility_room_service import list_room_types, upsert_room_type

Base.metadata.create_all(bind=engine)


def _db():
    return SessionLocal()


def test_facility_with_no_rooms_returns_empty_list():
    db = _db()
    try:
        assert list_room_types(db, "canonical-does-not-exist") == []
    finally:
        db.close()


def test_upsert_creates_room_with_photos():
    db = _db()
    try:
        room = upsert_room_type(
            db,
            canonical_facility_id="canonical-test-1",
            room_type_name="Private Suite",
            description="A private room with an attached bathroom.",
            monthly_price_cents=650000,
            availability_status="AVAILABLE",
            source="OUTREACH",
            photo_urls=["https://example.com/a.jpg", "https://example.com/b.jpg"],
        )
        assert room.id is not None

        rooms = list_room_types(db, "canonical-test-1")
        assert len(rooms) == 1
        assert rooms[0].room_type_name == "Private Suite"
        assert rooms[0].monthly_price_cents == 650000
        assert {p.url for p in rooms[0].photos} == {"https://example.com/a.jpg", "https://example.com/b.jpg"}
    finally:
        db.close()


def test_upsert_same_room_type_name_updates_in_place():
    db = _db()
    try:
        upsert_room_type(
            db,
            canonical_facility_id="canonical-test-2",
            room_type_name="Shared Room",
            monthly_price_cents=400000,
            availability_status="WAITLIST",
        )
        upsert_room_type(
            db,
            canonical_facility_id="canonical-test-2",
            room_type_name="Shared Room",
            monthly_price_cents=420000,
            availability_status="AVAILABLE",
        )
        rooms = list_room_types(db, "canonical-test-2")
        assert len(rooms) == 1  # updated, not duplicated
        assert rooms[0].monthly_price_cents == 420000
        assert rooms[0].availability_status == "AVAILABLE"
    finally:
        db.close()


def test_upsert_rejects_invalid_availability_status():
    db = _db()
    try:
        with pytest.raises(ValueError):
            upsert_room_type(
                db,
                canonical_facility_id="canonical-test-3",
                room_type_name="Studio",
                availability_status="MAYBE",
            )
    finally:
        db.close()
