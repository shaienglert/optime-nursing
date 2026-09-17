from __future__ import annotations

import base64
import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_REGISTRY_PATH = REPO_ROOT / "database" / "facility_media_registry.json"
PILOT_REGISTRY_PATH = REPO_ROOT / "database" / "synthetic_pilot" / "facility_media_registry.json.gz.b64"
_REGISTRY_CACHE: Dict[str, Any] = {"mtime": None, "payload": {"records": []}}


def _load_registry_payload() -> Dict[str, Any]:
    registry_path = _registry_path()
    if not registry_path.exists():
        return {"records": []}
    if registry_path.name.endswith(".gz.b64"):
        payload = json.loads(gzip.decompress(base64.b64decode(registry_path.read_text(encoding="ascii"))).decode("utf-8"))
    else:
        with registry_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    if not isinstance(payload, dict):
        return {"records": []}
    return payload


def get_facility_media_registry() -> Dict[str, Dict[str, Any]]:
    registry_path = _registry_path()
    current_mtime = registry_path.stat().st_mtime if registry_path.exists() else None
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

    synthetic_pilot = bool(record.get("synthetic_pilot")) and _pilot_mode()
    if not bool(record.get("verified_facility_specific")) and not synthetic_pilot:
        return None
    if str(record.get("image_status") or "").upper() not in {"VERIFIED", "SYNTHETIC_PILOT"}:
        return None
    if str(record.get("display_rights_status") or "").upper() not in {
        "OFFICIAL_DISPLAY_ALLOWED",
        "OWNER_AUTHORIZED",
        "LICENSED_EXTERNAL",
        "OOMNIK_OWNED_SYNTHETIC",
    }:
        return None

    image_url = str(record.get("primary_image_url") or "").strip()
    if not image_url:
        return None

    source_url = str(record.get("image_source_url") or record.get("official_facility_page_url") or record.get("source_url") or "").strip()
    source_type = str(record.get("image_source_type") or record.get("source_type") or "OFFICIAL_SITE")
    verification_method = str(record.get("verification_method") or "official identity + official page image verification")
    last_verified = str(record.get("verified_at") or record.get("last_verified") or "")

    source_note = "Synthetic pilot illustration — not a real facility" if synthetic_pilot else "Official Site"
    if source_type and not synthetic_pilot:
        source_note = f"Official Site ({source_type})"

    return {
        "hero": {
            "category": str(record.get("primary_image_category") or "exterior"),
            "url": image_url,
            "source": "Synthetic Pilot" if synthetic_pilot else "Official Site",
            "collected_at": last_verified,
            "source_url": source_url,
            "verification_method": verification_method,
            "source_note": source_note,
        },
        "gallery": [
            {
                "category": str(item.get("category") or "gallery"),
                "url": str(item.get("url") or ""),
                "source": "Synthetic Pilot" if synthetic_pilot else "Official Site",
                "collected_at": last_verified,
                "source_url": source_url,
                "verification_method": verification_method,
                "source_note": source_note,
            }
            for item in (record.get("gallery_images") or [{"category": "gallery", "url": image_url}])
            if str(item.get("url") or "").strip()
        ],
    }


def _pilot_mode() -> bool:
    return str(os.getenv("OPTIME_CANONICAL_MARKET") or "").strip().lower() in {"pilot", "synthetic", "synthetic-pilot"}


def _registry_path() -> Path:
    return PILOT_REGISTRY_PATH if _pilot_mode() else PRODUCTION_REGISTRY_PATH
