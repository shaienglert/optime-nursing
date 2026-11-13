"""Israeli facility registration: the facts a facility fills in about itself.

Owner decisions (2026-11-13): the source lists are only an outreach catalog,
and data the facility fills in itself counts as verified. These facts are the
only Israeli matching data; they reach the shared engine as FACILITY_SUPPLIED
facts on the candidate row.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityAuditLog, FacilityMarketRegistration
from app.services.israel_must_gates import FUNCTIONAL_LEVELS
from app.services.market_scope import ISRAEL_MARKET, ISRAEL_STATE_CODE
from app.services.provider_identity import CATEGORY_MEDICAL, role_can_edit_category

FACILITY_SUPPLIED_SOURCE = "facility_registration"
LICENSE_AUTHORITIES = {"MINISTRY_OF_HEALTH", "MINISTRY_OF_WELFARE"}
YES_NO = {"YES", "NO"}


def _clean_int(value: Any, field: str) -> Optional[int]:
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field} must be a non-negative number of shekels.")
    return int(value)


def validate_registration(payload: Dict[str, Any]) -> Dict[str, Any]:
    levels = payload.get("functional_levels_served")
    if not isinstance(levels, list) or not levels:
        raise ValueError("functional_levels_served must list at least one level.")
    levels = sorted({str(level).upper() for level in levels})
    unknown = [level for level in levels if level not in FUNCTIONAL_LEVELS]
    if unknown:
        raise ValueError(f"Unknown functional level(s): {', '.join(unknown)}.")

    agreement = str(payload.get("moh_code_agreement") or "").upper()
    if agreement not in YES_NO:
        raise ValueError("moh_code_agreement must be YES or NO.")

    license_id = str(payload.get("license_id") or "").strip()
    if not license_id:
        raise ValueError("license_id is required.")
    authority = str(payload.get("license_authority") or "").upper()
    if authority not in LICENSE_AUTHORITIES:
        raise ValueError("license_authority must be MINISTRY_OF_HEALTH or MINISTRY_OF_WELFARE.")
    try:
        expires = date.fromisoformat(str(payload.get("license_expiration_date") or ""))
    except ValueError as error:
        raise ValueError("license_expiration_date must be an ISO date (YYYY-MM-DD).") from error

    from app.services.israel_facility_questionnaire import validate_questionnaire

    questionnaire = validate_questionnaire(payload.get("questionnaire"))
    tracks = set(questionnaire.get("payment_tracks", []))
    if agreement == "YES" and "MOH_CODE" not in tracks:
        raise ValueError("סימנתם שיש הסכם קוד עם משרד הבריאות: יש לסמן גם את מסלול המימון \"קוד משרד הבריאות\".")
    if agreement == "NO" and "MOH_CODE" in tracks:
        raise ValueError("סימנתם מסלול \"קוד משרד הבריאות\" אבל אין הסכם קוד. יש לתקן אחת מהתשובות.")

    return {
        "questionnaire": questionnaire,
        "functional_levels_served": levels,
        "moh_code_agreement": agreement,
        "license_id": license_id,
        "license_authority": authority,
        "license_expiration_date": expires.isoformat(),
        "monthly_price_ils": _clean_int(payload.get("monthly_price_ils"), "monthly_price_ils"),
        "deposit_ils": _clean_int(payload.get("deposit_ils"), "deposit_ils"),
    }


def save_israel_registration(
    db: Session, facility_id: int, user_id: int, payload: Dict[str, Any], ip_address: Optional[str] = None
) -> Dict[str, Any]:
    from app.services.facility_profile_portal import _get_facility, _get_user

    facility = _get_facility(db, facility_id)
    if str(facility.state or "").upper() != ISRAEL_STATE_CODE:
        raise ValueError("Israeli registration is only for Israeli facilities.")
    user = _get_user(db, facility_id, user_id)
    if not role_can_edit_category(user.role, CATEGORY_MEDICAL):
        raise PermissionError(f"Role {user.role} may not submit the Israeli registration.")

    data = validate_registration(payload)
    row = (
        db.query(FacilityMarketRegistration)
        .filter(FacilityMarketRegistration.facility_id == facility_id, FacilityMarketRegistration.market == ISRAEL_MARKET)
        .one_or_none()
    )
    previous = row.payload_json if row else None
    new_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if row is None:
        row = FacilityMarketRegistration(facility_id=facility_id, market=ISRAEL_MARKET, payload_json=new_json)
        db.add(row)
    row.payload_json = new_json
    row.submitted_by_user_id = user.id
    # An unchanged resubmission is the facility confirming its details are still right;
    # it is logged so "last confirmed" can be shown and reviewed.
    db.add(
        FacilityAuditLog(
            facility_id=facility_id,
            user_id=user.id,
            field_name="israel_registration" if previous != new_json else "israel_registration:confirmed",
            old_value=previous if previous != new_json else None,
            new_value=new_json,
            ip_address=ip_address,
            user_role=user.role,
        )
    )
    db.commit()
    return {"facility_id": facility_id, "registration": data, "changed": previous != new_json}


def load_israel_registration(db: Session, canonical_id: str) -> Optional[Dict[str, Any]]:
    row = (
        db.query(FacilityMarketRegistration)
        .join(Facility, Facility.id == FacilityMarketRegistration.facility_id)
        .filter(Facility.cms_id == canonical_id, FacilityMarketRegistration.market == ISRAEL_MARKET)
        .one_or_none()
    )
    return json.loads(row.payload_json) if row else None


def _supplied(value: Any) -> Dict[str, Any]:
    return {"value": value, "status": "STATED", "source": FACILITY_SUPPLIED_SOURCE, "basis": "FACILITY_SUPPLIED"}


def apply_registration(row: Dict[str, Any], registration: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a copy of the candidate row carrying the facility's own facts."""
    if not registration:
        return row
    out = copy.deepcopy(row)
    out.setdefault("care_capabilities", {})["functional_levels_served"] = _supplied(registration["functional_levels_served"])
    licensing = out.setdefault("licensing", {})
    licensing["moh_code_agreement"] = _supplied(registration["moh_code_agreement"])
    licensing["license_id"] = _supplied(registration["license_id"])
    licensing["authority"] = _supplied(registration["license_authority"])
    pricing = out.setdefault("pricing", {"currency": "ILS"})
    if registration.get("monthly_price_ils") is not None:
        pricing["monthly_price"] = _supplied(registration["monthly_price_ils"])
    if registration.get("deposit_ils") is not None:
        pricing["deposit"] = _supplied(registration["deposit_ils"])
    # Read by the shared LICENSE_CURRENTLY_VALID gate (license_standing).
    out["license_status"] = "ACTIVE"
    out["expiration_date"] = registration["license_expiration_date"]
    out.pop("license_standing", None)
    out["registration_status"] = "REGISTERED"
    out["matching_eligibility"] = "REGISTERED"
    return out


def with_facility_supplied_facts(row: Dict[str, Any]) -> Dict[str, Any]:
    canonical_id = str(row.get("canonical_id") or "").strip()
    if not canonical_id.startswith("IL-"):
        return row
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        return apply_registration(row, load_israel_registration(db, canonical_id))
    finally:
        db.close()
