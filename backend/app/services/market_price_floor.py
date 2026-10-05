from __future__ import annotations
from typing import Any
from copy import deepcopy
from app.database import SessionLocal
from app.models.facility_room_offering import FacilityRoomType

def minimum_market_monthly_price(*, canonical_ids:list[str]|None=None)->dict[str,Any]:
    """Lowest currently published room base price in the requested candidate geography.
    This sets the intake slider floor only; it is not proof of total affordability."""
    db=SessionLocal()
    try:
        q=db.query(FacilityRoomType).filter(FacilityRoomType.monthly_price_cents.isnot(None))
        if canonical_ids is not None:
            q=q.filter(FacilityRoomType.canonical_facility_id.in_(canonical_ids))
        rows=q.all()
        if not rows: return {"minimum_monthly_price":None,"basis":"NO_PUBLISHED_ROOM_PRICE"}
        room=min(rows,key=lambda r:r.monthly_price_cents)
        return {"minimum_monthly_price":room.monthly_price_cents/100,"canonical_facility_id":room.canonical_facility_id,"room_type_name":room.room_type_name,"pricing_qualifier":room.pricing_qualifier or "UNKNOWN","basis":"LOWEST_CURRENT_PUBLISHED_ROOM_BASE_PRICE"}
    finally:
        db.close()

def minimum_price_for_questionnaire(questionnaire:dict[str,Any])->dict[str,Any]:
    """Preview the SAME care-qualified floor used by recommendations, before budget.

    The intake has button answers only at this stage. No interpreter, provider
    research or ranking AI is called. Budget and funding cannot shape their own
    comparison floor. Unknown prices/geography never become a fabricated minimum.
    """
    from app.services.patient_decision_engine_runtime import build_patient_needs_profile
    from app.services import decision_engine_evidence
    from app.services.client_intent_runtime import attach_client_intent_fit
    from app.services.provider_housing_runtime import attach_provider_housing_evidence
    from app.services.affordability_floor import compute_affordability_floor
    from app.services.canonical_intake_state import without_insurance
    state=without_insurance(deepcopy(questionnaire))
    state["budget"]=0
    profile=build_patient_needs_profile(state, structured_only=True)
    state=profile["canonical_decision_questionnaire"]
    core=decision_engine_evidence.run_patient_decision_engine(
        state, "", limit=10000, patient_needs_profile=profile)
    rows=list(core.get("results") or [])
    attach_provider_housing_evidence(rows)
    intent=profile["client_intent"]
    attach_client_intent_fit(rows, intent)
    from app.services.decision_pipeline import _attach_room_pricing_truth
    _attach_room_pricing_truth(rows)
    floor=compute_affordability_floor(rows, intent, profile)
    private_care_floor=deepcopy(floor)
    couple=str(questionnaire.get("relationship") or "").strip().lower()=="couple"
    if couple:
        from app.services.semantic_facility_requirements import _apply_pilot_monthly_cost
        for row in rows:
            _apply_pilot_monthly_cost(row)
            if row.get("monthly_price_basis") != "TWO_RESIDENT_TOTAL":
                row["starting_monthly_price"]=None  # a single-resident price cannot prove a household floor
        floor=compute_affordability_floor(rows, intent, profile)
    scope=core.get("location_scope") or {}
    unresolved=scope.get("reason")=="REFERENCE_POINT_NOT_GEOCODED"
    price=None if unresolved else floor["floor_monthly_price"]
    pursuing=False  # insurance is outside the search (owner 2026-10-05)
    return {
        "minimum_monthly_price":price,
        "canonical_facility_id":floor["floor_canonical_facility_id"] if price is not None else None,
        "basis":floor["basis"],
        "location_scope":scope,
        "affordability_floor":floor,
        "private_care_floor":private_care_floor,
        "monthly_price_basis":"TWO_RESIDENT_TOTAL" if couple else "SINGLE_RESIDENT",
        "status":"LOCATION_UNRESOLVED" if unresolved else "KNOWN" if price is not None else "PRICE_EVIDENCE_PENDING",
        "funding_pathway":"MEDICAID_COST_REQUIRES_VERIFICATION" if pursuing else "PRIVATE_PAY",
        "minimum_budget_is_binding":price is not None and not pursuing,
        "synthetic_pilot":any(row.get("synthetic_pilot") is True for row in rows),
        "rule":"Known starting monthly price for the selected area and care answers so far; final care, fees and coverage are confirmed with the facility.",
    }
