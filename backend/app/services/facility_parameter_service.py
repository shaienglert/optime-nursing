from __future__ import annotations

import json
from pathlib import Path
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

_CACHE: Dict[str, Any] = {"signature": None, "payload": None}


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _signature() -> tuple[float, float, float]:
    return (
        REGISTRY_PATH.stat().st_mtime,
        EVIDENCE_PATH.stat().st_mtime,
        CANONICAL_PATH.stat().st_mtime,
    )


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _scope_rank(scope: str) -> int:
    return {"FACILITY": 4, "PROGRAM": 3, "UNIT": 2, "SERVICE": 1}.get(scope, 0)


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


def _load_runtime() -> Dict[str, Any]:
    signature = _signature()
    if _CACHE["signature"] == signature and _CACHE["payload"] is not None:
        return _CACHE["payload"]

    registry_payload = _read_json(REGISTRY_PATH)
    evidence_payload = _read_json(EVIDENCE_PATH)
    canonical_payload = _read_json(CANONICAL_PATH)

    registry = registry_payload.get("records") or []
    canonical = canonical_payload.get("records") or []
    evidence = evidence_payload.get("records") or []

    canonical_by_id = {row["canonical_id"]: row for row in canonical}
    evidence_lookup: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for row in evidence:
        facility_rows = evidence_lookup.setdefault(row["canonical_facility_id"], {})
        facility_rows.setdefault(row["parameter_id"], []).append(row)

    payload = {
        "registry_payload": registry_payload,
        "registry": registry,
        "canonical_by_id": canonical_by_id,
        "evidence_lookup": evidence_lookup,
    }
    _CACHE["signature"] = signature
    _CACHE["payload"] = payload
    return payload


def get_parameter_registry_payload() -> Dict[str, Any]:
    return _load_runtime()["registry_payload"]


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
    evidence_lookup: Dict[str, Dict[str, List[Dict[str, Any]]]],
) -> List[Dict[str, Any]]:
    facility_rows = evidence_lookup.get(canonical_facility_id, {})
    resolved = []

    for parameter in ordered_registry:
        rows = facility_rows.get(parameter["parameter_id"], [])
        if rows:
            best = sorted(
                rows,
                key=lambda item: (
                    _scope_rank(str(item.get("scope") or "")),
                    1 if str(item.get("confidence") or "") == "HIGH" else 0,
                    str(item.get("last_verified") or ""),
                ),
                reverse=True,
            )[0]
            raw_value = best.get("value")
            display_value = raw_value
            if raw_value == "UNKNOWN":
                display_value = "Not verified"
            source = str(best.get("source") or "Not verified")
            last_verified = best.get("last_verified")
            detail_scope = str(best.get("scope") or parameter["applicable_scope"])
            scope_name = best.get("scope_name")
            evidence_count = len(rows)
        else:
            raw_value = "UNKNOWN"
            display_value = "Not verified"
            source = "Not verified"
            last_verified = None
            detail_scope = parameter["applicable_scope"]
            scope_name = None
            evidence_count = 0

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
                "evidence_count": evidence_count,
            }
        )
    return resolved


def get_facility_parameter_table(
    canonical_facility_id: str,
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
) -> Dict[str, Any]:
    runtime = _load_runtime()
    facility = runtime["canonical_by_id"].get(canonical_facility_id)
    if not facility:
        raise KeyError(canonical_facility_id)

    ordered = _ordered_registry(runtime["registry"], need_tags=need_tags, priority_parameter_ids=priority_parameter_ids, profile_key=profile_key)
    rows = _resolve_rows_for_facility(canonical_facility_id, ordered, runtime["evidence_lookup"])
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