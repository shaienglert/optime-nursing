from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "database" / "facility_media_registry.json"
_REGISTRY_CACHE: Dict[str, Any] = {"mtime": None, "payload": {"records": []}}


def _load_registry_payload() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"records": []}
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {"records": []}
    return payload


def get_facility_media_registry() -> Dict[str, Dict[str, Any]]:
    current_mtime = REGISTRY_PATH.stat().st_mtime if REGISTRY_PATH.exists() else None
    if _REGISTRY_CACHE["mtime"] != current_mtime:
        _REGISTRY_CACHE["mtime"] = current_mtime
        _REGISTRY_CACHE["payload"] = _load_registry_payload()

    payload = _REGISTRY_CACHE["payload"]
    records = payload.get("records") or []
    result: Dict[str, Dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        canonical_id = str(item.get("canonical_facility_id") or "").strip()
        if not canonical_id:
            continue
        result[canonical_id] = item
    return result


def get_facility_media_record(canonical_facility_id: Optional[str]) -> Optional[Dict[str, Any]]:
    canonical_id = str(canonical_facility_id or "").strip()
    if not canonical_id:
        return None
    return get_facility_media_registry().get(canonical_id)


def build_visual_media_payload(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not record:
        return None

    if not bool(record.get("verified_facility_specific")):
        return None
    if str(record.get("image_status") or "").upper() != "VERIFIED":
        return None

    image_url = str(record.get("primary_image_url") or "").strip()
    if not image_url:
        return None

    source_url = str(record.get("image_source_url") or record.get("official_facility_page_url") or record.get("source_url") or "").strip()
    source_type = str(record.get("image_source_type") or record.get("source_type") or "OFFICIAL_SITE")
    verification_method = str(record.get("verification_method") or "official identity + official page image verification")
    last_verified = str(record.get("last_verified") or "")

    source_note = "Official Site"
    if source_type:
        source_note = f"Official Site ({source_type})"

    return {
        "hero": {
            "category": "exterior",
            "url": image_url,
            "source": "Official Site",
            "collected_at": last_verified,
            "source_url": source_url,
            "verification_method": verification_method,
            "source_note": source_note,
        },
        "gallery": [
            {
                "category": "gallery",
                "url": image_url,
                "source": "Official Site",
                "collected_at": last_verified,
                "source_url": source_url,
                "verification_method": verification_method,
                "source_note": source_note,
            }
        ],
    }
