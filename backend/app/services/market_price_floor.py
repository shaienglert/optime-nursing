from __future__ import annotations
from typing import Any
from app.database import SessionLocal
from app.models.facility_room_offering import FacilityRoomType

def minimum_market_monthly_price(*, canonical_ids:list[str]|None=None)->dict[str,Any]:
    """Lowest currently published room base price in the requested candidate geography.
    This sets the intake slider floor only; it is not proof of total affordability."""
    db=SessionLocal()
    try:
        q=db.query(FacilityRoomType).filter(FacilityRoomType.monthly_price_cents.isnot(None))
        if canonical_ids:
            q=q.filter(FacilityRoomType.canonical_facility_id.in_(canonical_ids))
        rows=q.all()
        if not rows: return {"minimum_monthly_price":None,"basis":"NO_PUBLISHED_ROOM_PRICE"}
        room=min(rows,key=lambda r:r.monthly_price_cents)
        return {"minimum_monthly_price":room.monthly_price_cents/100,"canonical_facility_id":room.canonical_facility_id,"room_type_name":room.room_type_name,"pricing_qualifier":room.pricing_qualifier or "UNKNOWN","basis":"LOWEST_CURRENT_PUBLISHED_ROOM_BASE_PRICE"}
    finally:
        db.close()