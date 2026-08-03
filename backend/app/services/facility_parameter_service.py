from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"

REGISTRY_PATH = DATABASE_DIR / "optime_parameter_registry.json"
EVIDENCE_PATH = DATABASE_DIR / "florida_facility_parameter_evidence.json"
CANONICAL_PATH = DATABASE_DIR / "florida_facility_universe_canonical.json"

PROFILE_TAGS = {
    "stroke": ["stroke", "neurological", "rehab", "transfer", "medication", "nursing", "mobility"],
    "memory": ["memory", "dementia", "specialized_care"],
    "high_acuity": ["high_acuity", "medical", "nursing"],
}

logger = logging.getLogger("optime.runtime_cache")

_CACHE_LOCK = threading.RLock()
_CACHE: Dict[str, Any] = {
    "signature": None,
    "payload": None,
    "loaded_at": None,
    "swap_count": 0,
    "last_swap_reason": None,
}


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _signature() -> tuple[float, float, float]:
    return (
        REGISTRY_PATH.stat().st_mtime,
        EVIDENCE_PATH.stat().st_mtime,
        CANONICAL_PATH.stat().st_mtime,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _scope_rank(scope: str) -> int:
    return {"FACILITY": 4, "PROGRAM": 3, "UNIT": 2, "SERVICE": 1}.get(scope, 0)


def _best_evidence_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return sorted(
        rows,
        key=lambda item: (
            _scope_rank(str(item.get("scope") or "")),
            1 if str(item.get("confidence") or "") == "HIGH" else 0,
            str(item.get("last_verified") or ""),
        ),
        reverse=True,
    )[0]


def _base_priority(parameter: Dict[str, Any]) -> float:
    score = 100.0
    if parameter.get("hard_filter_eligibility"):
        score += 50.0
    if parameter.get("ranking_eligibility"):
        score += 20.0
    score += {
        "CARE_NURSING": 14.0,
        "REHABILITATION": 13.0,
        "SPECIALIZED_CARE": 12.0,
        "QUALITY_SAFETY": 8.0,
        "FINANCIAL_ACCESS": 6.0,
        "PERSONAL_FIT": 5.0,
        "DYNAMIC": 1.0,
    }.get(str(parameter.get("family")), 0.0)
    return score


def _build_runtime_payload(active_signature: tuple[float, float, float]) -> Dict[str, Any]:
    registry_payload = _read_json(REGISTRY_PATH)
    evidence_payload = _read_json(EVIDENCE_PATH)
    canonical_payload = _read_json(CANONICAL_PATH)

    registry = registry_payload.get("records") or []
    canonical = canonical_payload.get("records") or []
    evidence = evidence_payload.get("records") or []

    canonical_by_id = {row["canonical_id"]: row for row in canonical}
    evidence_lookup: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    evidence_best_lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in evidence:
        facility_rows = evidence_lookup.setdefault(row["canonical_facility_id"], {})
        facility_rows.setdefault(row["parameter_id"], []).append(row)

    for canonical_facility_id, facility_rows in evidence_lookup.items():
        best_for_facility: Dict[str, Dict[str, Any]] = {}
        for parameter_id, rows in facility_rows.items():
            best_for_facility[parameter_id] = _best_evidence_row(rows)
        evidence_best_lookup[canonical_facility_id] = best_for_facility

    # Full evidence rows are large and only needed for detailed comparison/profile views.
    # Keep just best/count lookups in steady-state and build full row lookup lazily.
    evidence_lookup = {}

    payload = {
        "registry_payload": registry_payload,
        "registry": registry,
        "canonical_by_id": canonical_by_id,
        "evidence_lookup": evidence_lookup,
        "evidence_best_lookup": evidence_best_lookup,
        "evidence_lookup_loaded": False,
        "runtime_meta": {
            "runtime_version": hashlib.sha256(
                json.dumps(
                    {
                        "registry_generated_at": registry_payload.get("generated_at_utc"),
                        "evidence_generated_at": evidence_payload.get("generated_at_utc"),
                        "canonical_generated_at": canonical_payload.get("generated_at_utc"),
                        "registry_count": int(registry_payload.get("record_count") or 0),
                        "evidence_count": int(evidence_payload.get("record_count") or 0),
                        "canonical_count": int(canonical_payload.get("record_count") or 0),
                        "mtime_signature": active_signature,
                    },
                    sort_keys=True,
                    default=str,
                ).encode("utf-8")
            ).hexdigest()[:16],
            "runtime_timestamp": registry_payload.get("generated_at_utc")
            or evidence_payload.get("generated_at_utc")
            or canonical_payload.get("generated_at_utc"),
            "artifact_signature": active_signature,
        },
    }
    return payload


def _atomic_swap_runtime_payload(payload: Dict[str, Any], active_signature: tuple[float, float, float], reason: str) -> None:
    with _CACHE_LOCK:
        _CACHE["payload"] = payload
        _CACHE["signature"] = active_signature
        _CACHE["loaded_at"] = _utc_now_iso()
        _CACHE["swap_count"] = int(_CACHE.get("swap_count") or 0) + 1
        _CACHE["last_swap_reason"] = reason


def _load_runtime() -> Dict[str, Any]:
    active_signature = _signature()
    with _CACHE_LOCK:
        cached_payload = _CACHE.get("payload")
        cached_signature = _CACHE.get("signature")
        if cached_payload is not None and cached_signature == active_signature:
            return cached_payload

        # Serialize rebuild to avoid N parallel JSON loads/swaps during high concurrency.
        payload = _build_runtime_payload(active_signature)
        _CACHE["payload"] = payload
        _CACHE["signature"] = active_signature
        _CACHE["loaded_at"] = _utc_now_iso()
        _CACHE["swap_count"] = int(_CACHE.get("swap_count") or 0) + 1
        _CACHE["last_swap_reason"] = "load_or_refresh"
        logger.info("runtime_cache_swapped reason=load_or_refresh runtime_version=%s", payload.get("runtime_meta", {}).get("runtime_version"))
        return payload


def _ensure_full_evidence_lookup(runtime: Dict[str, Any]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    with _CACHE_LOCK:
        if runtime.get("evidence_lookup_loaded") and isinstance(runtime.get("evidence_lookup"), dict):
            return runtime["evidence_lookup"]

    evidence_payload = _read_json(EVIDENCE_PATH)
    evidence_rows = evidence_payload.get("records") or []
    lookup: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for row in evidence_rows:
        facility_rows = lookup.setdefault(row["canonical_facility_id"], {})
        facility_rows.setdefault(row["parameter_id"], []).append(row)

    with _CACHE_LOCK:
        runtime["evidence_lookup"] = lookup
        runtime["evidence_lookup_loaded"] = True
    return lookup


def get_parameter_registry_payload() -> Dict[str, Any]:
    return _load_runtime()["registry_payload"]


def get_runtime_metadata() -> Dict[str, Optional[str]]:
    runtime = _load_runtime()
    meta = runtime.get("runtime_meta") or {}
    return {
        "runtime_version": str(meta.get("runtime_version") or ""),
        "runtime_timestamp": meta.get("runtime_timestamp"),
    }


def refresh_runtime_cache(reason: str = "manual") -> Dict[str, Optional[str]]:
    # Controlled invalidation + reload guarantees an atomic runtime snapshot swap.
    with _CACHE_LOCK:
        _CACHE["payload"] = None
        _CACHE["signature"] = None
    runtime = _load_runtime()
    meta = runtime.get("runtime_meta") or {}
    return {
        "reason": reason,
        "runtime_version": str(meta.get("runtime_version") or ""),
        "runtime_timestamp": meta.get("runtime_timestamp"),
    }


def get_runtime_cache_status() -> Dict[str, Any]:
    with _CACHE_LOCK:
        payload = _CACHE.get("payload")
        runtime_meta = (payload or {}).get("runtime_meta") if isinstance(payload, dict) else {}
        return {
            "cache_loaded": payload is not None,
            "loaded_at": _CACHE.get("loaded_at"),
            "swap_count": int(_CACHE.get("swap_count") or 0),
            "last_swap_reason": _CACHE.get("last_swap_reason"),
            "signature": _CACHE.get("signature"),
            "runtime_version": (runtime_meta or {}).get("runtime_version"),
            "runtime_timestamp": (runtime_meta or {}).get("runtime_timestamp"),
        }


def get_all_canonical_facility_ids() -> List[str]:
    runtime = _load_runtime()
    return list(runtime["canonical_by_id"].keys())


def get_canonical_facility_index() -> Dict[str, Dict[str, Any]]:
    runtime = _load_runtime()
    return runtime["canonical_by_id"]


def _ordered_registry(
    registry: List[Dict[str, Any]],
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    effective_tags = {_normalize_text(tag) for tag in (need_tags or [])}
    if profile_key:
        effective_tags.update(PROFILE_TAGS.get(profile_key, []))
    priority_set = {str(item) for item in (priority_parameter_ids or [])}

    ordered = []
    for parameter in registry:
        tag_bonus = float(len(effective_tags.intersection({_normalize_text(tag) for tag in (parameter.get("personalization_tags") or [])})) * 20)
        explicit_bonus = 100.0 if parameter["parameter_id"] in priority_set else 0.0
        ordered.append({**parameter, "sort_score": _base_priority(parameter) + tag_bonus + explicit_bonus})
    ordered.sort(key=lambda item: (-item["sort_score"], item["family"], item["display_name"]))
    return ordered


def get_personalized_parameter_order(
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
) -> Dict[str, Any]:
    runtime = _load_runtime()
    ordered = _ordered_registry(runtime["registry"], need_tags=need_tags, priority_parameter_ids=priority_parameter_ids, profile_key=profile_key)
    return {
        "generated_at_utc": runtime["registry_payload"].get("generated_at_utc"),
        "profile_key": profile_key,
        "need_tags": need_tags or [],
        "priority_parameter_ids": priority_parameter_ids or [],
        "ordered_parameters": [
            {
                "parameter_id": item["parameter_id"],
                "family": item["family"],
                "display_name": item["display_name"],
                "applicable_scope": item["applicable_scope"],
                "sort_score": round(item["sort_score"], 2),
            }
            for item in ordered
        ],
    }


def _resolve_rows_for_facility(
    canonical_facility_id: str,
    ordered_registry: List[Dict[str, Any]],
    evidence_lookup: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]],
    evidence_best_lookup: Dict[str, Dict[str, Dict[str, Any]]],
    include_evidence_records: bool,
) -> List[Dict[str, Any]]:
    facility_rows = (evidence_lookup or {}).get(canonical_facility_id, {})
    facility_best_rows = evidence_best_lookup.get(canonical_facility_id, {})
    resolved = []

    for parameter in ordered_registry:
        rows = facility_rows.get(parameter["parameter_id"], [])
        best = facility_best_rows.get(parameter["parameter_id"])
        if best is not None:
            raw_value = best.get("value")
            display_value = raw_value
            if raw_value == "UNKNOWN":
                display_value = "Not verified"
            source = str(best.get("source") or "Not verified")
            last_verified = best.get("last_verified")
            detail_scope = str(best.get("scope") or parameter["applicable_scope"])
            scope_name = best.get("scope_name")
            source_record_id = best.get("source_record_id")
            evidence_confidence = best.get("confidence")
            evidence_strength = best.get("evidence_strength")
            provenance = best.get("provenance") or {}
            evidence_count = len(rows) if include_evidence_records else 0
            if include_evidence_records:
                evidence_records = [
                    {
                        "source_record_id": entry.get("source_record_id"),
                        "evidence_text": entry.get("evidence_text"),
                        "evidence_value": entry.get("evidence_value"),
                        "evidence_date": entry.get("evidence_date"),
                        "last_verified": entry.get("last_verified"),
                        "scope": entry.get("scope"),
                        "scope_name": entry.get("scope_name"),
                        "source": entry.get("source"),
                        "confidence": entry.get("confidence"),
                        "evidence_strength": entry.get("evidence_strength"),
                        "conflict_status": entry.get("conflict_status"),
                        "provenance": entry.get("provenance") or {},
                    }
                    for entry in rows
                ]
            else:
                evidence_records = []
        else:
            raw_value = "UNKNOWN"
            display_value = "Not verified"
            source = "Not verified"
            last_verified = None
            detail_scope = parameter["applicable_scope"]
            scope_name = None
            source_record_id = None
            evidence_confidence = None
            evidence_strength = None
            provenance = {}
            evidence_count = 0
            evidence_records = []

        if parameter["parameter_id"] == "current_availability":
            raw_value = "UNKNOWN"
            display_value = "Confirm directly with facility"
            source = "Direct facility confirmation required"

        resolved.append(
            {
                "parameter_id": parameter["parameter_id"],
                "category": parameter["family"],
                "parameter": parameter["display_name"],
                "status_value": display_value,
                "raw_value": raw_value,
                "detail_scope": detail_scope,
                "scope_name": scope_name,
                "source": source,
                "last_verified": last_verified,
                "source_record_id": source_record_id,
                "evidence_confidence": evidence_confidence,
                "evidence_strength": evidence_strength,
                "provenance": provenance,
                "evidence_count": evidence_count,
                "evidence_records": evidence_records,
            }
        )
    return resolved


def get_facility_parameter_table(
    canonical_facility_id: str,
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
    ordered_registry: Optional[List[Dict[str, Any]]] = None,
    include_evidence_records: bool = True,
) -> Dict[str, Any]:
    runtime = _load_runtime()
    facility = runtime["canonical_by_id"].get(canonical_facility_id)
    if not facility:
        raise KeyError(canonical_facility_id)

    ordered = ordered_registry or _ordered_registry(runtime["registry"], need_tags=need_tags, priority_parameter_ids=priority_parameter_ids, profile_key=profile_key)
    evidence_lookup = _ensure_full_evidence_lookup(runtime) if include_evidence_records else None
    rows = _resolve_rows_for_facility(
        canonical_facility_id,
        ordered,
        evidence_lookup,
        runtime["evidence_best_lookup"],
        include_evidence_records,
    )
    return {
        "canonical_facility_id": canonical_facility_id,
        "facility_name": facility.get("facility_name"),
        "city": facility.get("city"),
        "state": facility.get("state"),
        "county": facility.get("county"),
        "zip": facility.get("zip"),
        "canonical_type": facility.get("canonical_type"),
        "role_classification": facility.get("role_classification"),
        "match_status": (facility.get("match") or {}).get("status"),
        "need_tags": need_tags or [],
        "priority_parameter_ids": priority_parameter_ids or [],
        "profile_key": profile_key,
        "rows": rows,
    }


def compare_facility_parameter_tables(
    canonical_facility_ids: List[str],
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
) -> Dict[str, Any]:
    runtime = _load_runtime()
    ordered = _ordered_registry(runtime["registry"], need_tags=need_tags, priority_parameter_ids=priority_parameter_ids, profile_key=profile_key)
    ordered_ids = [item["parameter_id"] for item in ordered]

    facilities = [
        get_facility_parameter_table(
            canonical_facility_id=item,
            need_tags=need_tags,
            priority_parameter_ids=priority_parameter_ids,
            profile_key=profile_key,
            ordered_registry=ordered,
        )
        for item in canonical_facility_ids
    ]
    return {
        "parameter_ids": ordered_ids,
        "need_tags": need_tags or [],
        "priority_parameter_ids": priority_parameter_ids or [],
        "profile_key": profile_key,
        "facilities": facilities,
    }