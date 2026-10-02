"""Published room-price floor for the requested real catalog area."""
from app.database import SessionLocal
from app.models.facility_room_offering import FacilityRoomType
from app.services.facility_parameter_service import get_canonical_facility_index


def minimum_price_for_questionnaire(questionnaire):
    index = get_canonical_facility_index()
    area = str(questionnaire.get("referenceAddress") or questionnaire.get("referenceLocationValue") or "").strip().casefold()
    broad = area in {"", "anywhere in the las vegas valley"}
    ids = [str(cid) for cid, row in index.items()
           if not row.get("synthetic_pilot")
           and (broad or area in str(row.get("city") or row.get("address") or "").casefold())]
    if not ids:
        return {"minimum_monthly_price": None, "basis": "NO_PRICED_FACILITIES_IN_AREA"}
    db = SessionLocal()
    try:
        room = (db.query(FacilityRoomType)
                .filter(FacilityRoomType.canonical_facility_id.in_(ids),
                        FacilityRoomType.monthly_price_cents > 0,
                        FacilityRoomType.last_verified_at.isnot(None))
                .order_by(FacilityRoomType.monthly_price_cents.asc()).first())
        if room is None:
            return {"minimum_monthly_price": None, "basis": "NO_VERIFIED_PUBLISHED_ROOM_PRICE"}
        return {"minimum_monthly_price": room.monthly_price_cents / 100,
                "basis": "LOWEST_KNOWN_PUBLISHED_ROOM_BASE_PRICE",
                "canonical_facility_id": room.canonical_facility_id,
                "last_verified_at": room.last_verified_at.isoformat(),
                "source": room.source}
    finally:
        db.close()
