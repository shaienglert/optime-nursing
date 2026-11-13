"""One uniform public home page per Israeli facility.

Every facility in the Israeli registry gets the same structure. What the list
says is shown as list information; what the facility filled in at registration
is shown as the facility's own information; anything unknown is shown as not yet
provided, never guessed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.facility import Facility, FacilityPhoto
from app.services.activity_intelligence import get_public_activity_categories
from app.services.israel_facility_import import load_israel_records
from app.services.israel_facility_registration import load_israel_registration

LEVEL_LABELS = {"INDEPENDENT": "עצמאיים", "FRAIL": "תשושים", "NURSING": "סיעודיים", "COGNITIVE_FRAIL": "תשושי נפש"}
AUTHORITY_LABELS = {"MINISTRY_OF_HEALTH": "משרד הבריאות", "MINISTRY_OF_WELFARE": "משרד הרווחה"}


@lru_cache(maxsize=1)
def _records_by_id() -> Dict[str, Dict[str, Any]]:
    records, _ = load_israel_records()
    return {r["canonical_id"]: r for r in records}


def _value(fact: Any) -> Any:
    return fact.get("value") if isinstance(fact, dict) and fact.get("status") == "STATED" else None


def list_israel_facilities(city: Optional[str] = None, setting: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = []
    for record in _records_by_id().values():
        if city and city.strip() not in str(record.get("city") or ""):
            continue
        if setting and record.get("canonical_setting") != setting:
            continue
        rows.append({
            "canonical_id": record["canonical_id"],
            "name": record.get("facility_name"),
            "facility_type": record.get("facility_type"),
            "city": record.get("city"),
        })
    return sorted(rows, key=lambda r: (str(r["city"] or ""), str(r["name"] or "")))


def build_israel_facility_page(db: Session, canonical_id: str) -> Optional[Dict[str, Any]]:
    record = _records_by_id().get(canonical_id)
    if record is None:
        return None
    registration = load_israel_registration(db, canonical_id)
    facility = db.query(Facility).filter(Facility.cms_id == canonical_id).one_or_none()

    photos: List[Dict[str, Any]] = []
    activities: List[Dict[str, Any]] = []
    if facility is not None:
        photos = [
            {"url": p.url, "caption": p.caption, "category": p.category}
            for p in db.query(FacilityPhoto)
            .filter(FacilityPhoto.facility_id == facility.id, FacilityPhoto.is_active.is_(True))
            .order_by(FacilityPhoto.uploaded_at)
        ]
        activities = get_public_activity_categories(db, facility.id)

    from_list = {
        "facility_type": record.get("facility_type"),
        "city": record.get("city"),
        "district": record.get("district"),
        "operator_name": record.get("operator_name"),
        "ownership_type": record.get("ownership_type"),
        "phone": record.get("phone"),
        "website": record.get("website"),
        "license_id": _value(record["licensing"].get("license_id")),
        "moh_code_agreement": _value(record["licensing"].get("moh_code_agreement")),
        "departments": _value(record["care_capabilities"].get("departments")) or [],
        "religion_attitude": _value(record["lifestyle"].get("religion_attitude")) or [],
        "source_name": next(iter(record["source_evidence"].values()))["source_name"],
    }

    from_facility = None
    if registration:
        from_facility = {
            "functional_levels_served": [LEVEL_LABELS[level] for level in registration["functional_levels_served"]],
            "moh_code_agreement": registration["moh_code_agreement"],
            "license_authority": AUTHORITY_LABELS.get(registration["license_authority"], registration["license_authority"]),
            "license_id": registration["license_id"],
            "license_expiration_date": registration["license_expiration_date"],
            "monthly_price_ils": registration.get("monthly_price_ils"),
            "deposit_ils": registration.get("deposit_ils"),
        }

    return {
        "canonical_id": canonical_id,
        "name": record.get("facility_name"),
        "registration_status": "REGISTERED" if registration else "NOT_REGISTERED",
        "from_list": from_list,
        "from_facility": from_facility,
        "photos": photos,
        "activities": activities,
        "data_quality_flags": record.get("data_quality_flags") or [],
    }
