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

def minimum_price_for_questionnaire(questionnaire:dict[str,Any])->dict[str,Any]:
    from app.services.facility_parameter_service import get_canonical_facility_index
    from app.services.location_radius import annotate_distances, plan_radius_scope, resolve_reference_point
    index=get_canonical_facility_index()
    rows=[{**row,"canonical_facility_id":str(cid)} for cid,row in index.items() if row.get("synthetic_pilot") is not True]
    reference=resolve_reference_point(questionnaire,rows,location_city=str(questionnaire.get("locationCity") or "") or None)
    annotate_distances(rows,reference,index)
    scoped=plan_radius_scope(rows,questionnaire,reference)
    ids=[str(row.get("canonical_facility_id")) for row in scoped["rows"] if row.get("canonical_facility_id")]
    result=minimum_market_monthly_price(canonical_ids=ids)
    result["location_scope"]=scoped["scope"]
    return result
