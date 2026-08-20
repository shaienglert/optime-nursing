from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

UNKNOWN = "UNKNOWN"
REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "facility_service_delivery_primary_evidence.json"


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _norm_addr(value: Any) -> str:
    text = f" {_norm(value)} "
    for source, target in {
        " street ": " st ", " road ": " rd ", " avenue ": " ave ", " boulevard ": " blvd ",
        " drive ": " dr ", " lane ": " ln ", " court ": " ct ", " place ": " pl ",
        " highway ": " hwy ", " parkway ": " pkwy ", " north ": " n ", " south ": " s ",
        " east ": " e ", " west ": " w ",
    }.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def _records() -> list[Dict[str, Any]]:
    if not EVIDENCE_PATH.is_file():
        return []
    return list(json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")).get("records") or [])


def _match(row: Dict[str, Any], record: Dict[str, Any]) -> bool:
    cid = str(row.get("canonical_facility_id") or row.get("canonical_id") or "")
    ids = {str(v) for v in record.get("canonical_facility_ids") or []}
    if cid and cid in ids:
        return True

    row_state, rec_state = _norm(row.get("state")), _norm(record.get("state"))
    if row_state and rec_state and row_state != rec_state:
        return False
    row_city, rec_city = _norm(row.get("city")), _norm(record.get("city"))
    if row_city and rec_city and row_city != rec_city:
        return False

    row_addr = _norm_addr(row.get("address") or row.get("facility_address"))
    rec_addr = _norm_addr(record.get("address"))
    if row_addr and rec_addr and row_addr == rec_addr:
        return True

    row_name = _norm(row.get("facility_name") or row.get("name"))
    aliases = {_norm(record.get("community_name"))}
    aliases.update(_norm(v) for v in record.get("aliases") or [])
    return bool(row_name and row_name in aliases and row_city == rec_city)


def get_facility_service_delivery_evidence(row: Dict[str, Any]) -> Dict[str, Any]:
    for record in _records():
        if not _match(row, record):
            continue
        return {
            "matched": True,
            "record_key": record.get("record_key") or UNKNOWN,
            "community_name": record.get("community_name") or UNKNOWN,
            "primary_source_url": record.get("primary_source_url") or UNKNOWN,
            "meal_delivery": dict(record.get("meal_delivery") or {}),
            "personal_care_delivery": dict(record.get("personal_care_delivery") or {}),
            "support_services": dict(record.get("support_services") or {}),
            "evidence_summary": record.get("evidence_summary") or UNKNOWN,
        }
    return {
        "matched": False,
        "record_key": None,
        "community_name": row.get("facility_name") or row.get("name") or UNKNOWN,
        "primary_source_url": UNKNOWN,
        "meal_delivery": {
            "dining_available": UNKNOWN,
            "meals_per_day": UNKNOWN,
            "meal_plan_model": UNKNOWN,
            "meal_plan_included": UNKNOWN,
            "meal_delivery_to_apartment": UNKNOWN,
            "between_meal_food_available": UNKNOWN,
            "evidence_status": UNKNOWN,
        },
        "personal_care_delivery": {
            "care_delivery_model": UNKNOWN,
            "personal_care_in_house": UNKNOWN,
            "outside_care_allowed": UNKNOWN,
            "partner_agency_name": UNKNOWN,
            "partner_agency_license_id": UNKNOWN,
            "agency_relationship_type": UNKNOWN,
            "evidence_status": UNKNOWN,
        },
        "support_services": {},
        "evidence_summary": UNKNOWN,
    }


__all__ = ["get_facility_service_delivery_evidence"]
