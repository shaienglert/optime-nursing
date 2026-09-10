"""Project the governed Las Vegas facility universe into the public facility table."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable

from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.services.canonical_universe import resolve_canonical_universe_path


SOURCE_NAME = "Nevada canonical Las Vegas runtime projection"
NEVADA_STATE_CODE = "NV"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(str(value)) if str(value or "").strip().isdigit() else None
    except (TypeError, ValueError):
        return None


def _facility_key(row: Dict[str, Any]) -> str:
    ccn = str(row.get("cms_ccn") or "").strip()
    if ccn.isdigit() and len(ccn) == 6:
        return ccn
    canonical_id = str(row.get("canonical_id") or "").strip()
    if not canonical_id:
        raise ValueError("Nevada canonical record has no identity")
    return "NVRT-" + hashlib.sha1(canonical_id.encode("utf-8")).hexdigest()[:15]


def load_las_vegas_runtime_records() -> tuple[list[Dict[str, Any]], str | None]:
    path = resolve_canonical_universe_path("las-vegas")
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = list(payload.get("records") or [])
    invalid = [row for row in records if str(row.get("state") or "").upper() != NEVADA_STATE_CODE or row.get("is_las_vegas_valley") is not True]
    if invalid:
        raise ValueError("Las Vegas runtime projection contains out-of-scope records")
    return records, str(payload.get("generated_at") or payload.get("generated_at_utc") or "") or None


def import_las_vegas_runtime_facilities(
    db: Session, *, records: Iterable[Dict[str, Any]] | None = None, source_date: str | None = None
) -> Dict[str, int]:
    """Upsert only governed Nevada Valley records; never synthesize facility facts."""
    if records is None:
        rows, loaded_source_date = load_las_vegas_runtime_records()
        source_date = source_date or loaded_source_date
    else:
        rows = list(records)

    created = 0
    updated = 0
    keys: set[str] = set()
    for row in rows:
        if str(row.get("state") or "").upper() != NEVADA_STATE_CODE or row.get("is_las_vegas_valley") is not True:
            raise ValueError("Attempted to import a facility outside Las Vegas, Nevada")
        key = _facility_key(row)
        keys.add(key)
        facility = db.query(Facility).filter(Facility.cms_id == key).one_or_none()
        if facility is None:
            facility = Facility(
                cms_id=key,
                name=str(row.get("facility_name") or "Unknown facility"),
                address=str(row.get("address") or "Unknown"),
                city=str(row.get("city") or "LAS VEGAS"),
                state=NEVADA_STATE_CODE,
                zip_code=str(row.get("zip") or "UNKNOWN"),
            )
            db.add(facility)
            created += 1
        else:
            updated += 1

        facility.name = str(row.get("facility_name") or facility.name)
        facility.address = str(row.get("address") or facility.address)
        facility.city = str(row.get("city") or facility.city)
        facility.state = NEVADA_STATE_CODE
        facility.zip_code = str(row.get("zip") or facility.zip_code)
        facility.phone = str(row.get("phone") or "").strip() or None
        facility.beds = _int_or_none(row.get("certified_beds")) or _int_or_none(row.get("licensed_capacity"))
        facility.overall_rating = _int_or_none(row.get("cms_overall_rating"))
        facility.staffing_rating = _int_or_none(row.get("cms_staffing_rating"))
        facility.quality_rating = _int_or_none(row.get("cms_quality_measure_rating"))
        facility.inspection_rating = _int_or_none(row.get("cms_health_inspection_rating"))
        facility.source_name = SOURCE_NAME
        facility.source_date = source_date
        facility.confidence_level = "HIGH"

    db.commit()
    return {"facilities_imported": len(rows), "facilities_created": created, "facilities_updated": updated}
