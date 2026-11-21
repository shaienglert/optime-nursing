"""Project the Israeli canonical facility universe into the public facility table."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable

from sqlalchemy.orm import Session

from app.models.facility import Facility
from app.services.canonical_universe import resolve_canonical_universe_path
from app.services.canonical_universe import configured_canonical_market
from app.services.market_scope import ISRAEL_MARKET, ISRAEL_STATE_CODE, ISRAEL_SYNTHETIC_MARKET

SYNTHETIC_PREFIX = "IL-SYN-"

SOURCE_NAME = "Israel canonical facility universe"


def load_israel_records(market: str | None = None) -> tuple[list[Dict[str, Any]], str | None]:
    market = market or configured_canonical_market()
    if market not in {ISRAEL_MARKET, ISRAEL_SYNTHETIC_MARKET}:
        market = ISRAEL_MARKET
    path = resolve_canonical_universe_path(market)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = list(payload.get("records") or [])
    if any(str(row.get("state") or "").upper() != ISRAEL_STATE_CODE for row in records):
        raise ValueError("Israel canonical universe contains out-of-scope records")
    # Synthetic test facilities and real ones must never share a deployment.
    synthetic = [str(row.get("canonical_id") or "").startswith(SYNTHETIC_PREFIX) for row in records]
    if market == ISRAEL_SYNTHETIC_MARKET and not all(synthetic):
        raise ValueError("The synthetic Israeli universe contains a non-synthetic record")
    if market == ISRAEL_MARKET and any(synthetic):
        raise ValueError("The real Israeli universe contains a synthetic record")
    return records, str(payload.get("generated_at_utc") or "") or None


def import_israel_facilities(
    db: Session, *, records: Iterable[Dict[str, Any]] | None = None, source_date: str | None = None
) -> Dict[str, int]:
    """Upsert one row per canonical record; unknown fields stay marked unknown."""
    if records is None:
        rows, loaded_source_date = load_israel_records()
        source_date = source_date or loaded_source_date
    else:
        rows = list(records)

    created = 0
    updated = 0
    for row in rows:
        if str(row.get("state") or "").upper() != ISRAEL_STATE_CODE:
            raise ValueError("Attempted to import a facility outside Israel")
        key = str(row.get("canonical_id") or "").strip()
        if not key or len(key) > 20:
            raise ValueError(f"Israeli canonical record has an unusable identity: {key!r}")
        facility = db.query(Facility).filter(Facility.cms_id == key).one_or_none()
        if facility is None:
            facility = Facility(
                cms_id=key,
                name=str(row.get("facility_name") or "Unknown facility"),
                address=str(row.get("address") or "Unknown"),
                city=str(row.get("city") or "Unknown"),
                state=ISRAEL_STATE_CODE,
                zip_code="UNKNOWN",
            )
            db.add(facility)
            created += 1
        else:
            updated += 1

        facility.name = str(row.get("facility_name") or facility.name)
        facility.address = str(row.get("address") or facility.address)
        facility.city = str(row.get("city") or facility.city)
        facility.state = ISRAEL_STATE_CODE
        facility.phone = (str(row.get("phone") or "").strip() or None)
        facility.latitude = row.get("latitude")
        facility.longitude = row.get("longitude")
        # Israel has no CMS-style star ratings; leave them empty rather than invent them.
        facility.overall_rating = None
        facility.staffing_rating = None
        facility.quality_rating = None
        facility.inspection_rating = None
        facility.source_name = SOURCE_NAME
        facility.source_date = source_date
        facility.confidence_level = "SOURCE_LIST"

    db.commit()
    return {"facilities_imported": len(rows), "facilities_created": created, "facilities_updated": updated}


def seed_synthetic_registrations(db: Session) -> int:
    """Load the synthetic facilities' own questionnaire answers (test deployment only).

    Existing registrations are left alone, so answers edited through the portal during
    a test run survive a restart.
    """
    from app.models.facility import FacilityMarketRegistration
    from app.services.canonical_universe import resolve_canonical_universe_path

    if configured_canonical_market() != ISRAEL_SYNTHETIC_MARKET:
        raise RuntimeError("Synthetic registrations may be seeded only in the israel-synthetic market")
    path = resolve_canonical_universe_path(ISRAEL_SYNTHETIC_MARKET).with_name("registrations.json")
    registrations = json.loads(path.read_text(encoding="utf-8"))["registrations"]
    ids = {f.cms_id: f.id for f in db.query(Facility).filter(Facility.cms_id.like(SYNTHETIC_PREFIX + "%"))}
    existing = {
        row.facility_id
        for row in db.query(FacilityMarketRegistration.facility_id).filter(FacilityMarketRegistration.market == ISRAEL_MARKET)
    }
    created = 0
    for canonical_id, payload in registrations.items():
        facility_id = ids.get(canonical_id)
        if facility_id is None or facility_id in existing:
            continue
        db.add(
            FacilityMarketRegistration(
                facility_id=facility_id,
                market=ISRAEL_MARKET,
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            )
        )
        created += 1
    # Synthetic visiting hours so the visit calendar can be exercised (left alone once set).
    from app.models.facility import FacilityVisitSchedule
    from app.services.israel_visits import synthetic_schedule

    scheduled = {row.facility_id for row in db.query(FacilityVisitSchedule.facility_id)}
    for canonical_id, payload in registrations.items():
        facility_id = ids.get(canonical_id)
        if facility_id is None or facility_id in scheduled:
            continue
        religious = (payload.get("questionnaire") or {}).get("religious_character")
        db.add(FacilityVisitSchedule(facility_id=facility_id, schedule_json=json.dumps(synthetic_schedule(canonical_id, religious), ensure_ascii=False)))
    db.commit()
    return created
