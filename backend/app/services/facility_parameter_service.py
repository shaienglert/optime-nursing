from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional

from app.services.canonical_universe import configured_canonical_market, resolve_canonical_universe_path


REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"
REGISTRY_PATH = DATABASE_DIR / "optime_parameter_registry.json"
FLORIDA_EVIDENCE_PATH = DATABASE_DIR / "florida_facility_parameter_evidence.json"
# Backward-compatible public constant used by older runtime-sync code/tests.
EVIDENCE_PATH = FLORIDA_EVIDENCE_PATH

PROFILE_TAGS = {
    "stroke": ["stroke", "neurological", "rehab", "transfer", "medication", "nursing", "mobility"],
    "memory": ["memory", "dementia", "specialized_care"],
    "high_acuity": ["high_acuity", "medical", "nursing"],
}

logger = logging.getLogger("optime.runtime_cache")
_CACHE_LOCK = threading.RLock()
_CACHE: Dict[str, Any] = {}


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _effective_market() -> str:
    market = configured_canonical_market()
    return "las-vegas" if market in {"las-vegas", "nevada"} else market


def _canonical_records_for_market(payload: Dict[str, Any], market: str) -> List[Dict[str, Any]]:
    rows = list(payload.get("records") or [])
    if market == "las-vegas":
        # The Nevada canonical artifact is statewide. Production Las Vegas search must
        # never silently rank Reno/other Nevada facilities merely because they exist.
        rows = [row for row in rows if row.get("is_las_vegas_valley") is True]
    return rows


def _signature(market: str) -> tuple[Any, ...]:
    canonical_path = resolve_canonical_universe_path(market)
    evidence_mtime = FLORIDA_EVIDENCE_PATH.stat().st_mtime if market == "florida" and FLORIDA_EVIDENCE_PATH.exists() else 0.0
    return (
        market,
        REGISTRY_PATH.stat().st_mtime,
        evidence_mtime,
        canonical_path.stat().st_mtime,
        str(canonical_path),
    )


def _evidence_row(
    canonical_id: str,
    parameter_id: str,
    value: Any,
    *,
    source: str,
    source_record_id: str,
    scope: str = "FACILITY",
    confidence: str = "HIGH",
    evidence_strength: str = "REGULATORY_VERIFIED",
    evidence_text: Optional[str] = None,
    evidence_date: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "canonical_facility_id": canonical_id,
        "parameter_id": parameter_id,
        "value": value,
        "source": source,
        "scope": scope,
        "scope_name": None,
        "last_verified": evidence_date,
        "source_record_id": source_record_id,
        "evidence_text": evidence_text or parameter_id.replace("_", " "),
        "evidence_value": value,
        "evidence_date": evidence_date,
        "confidence": confidence,
        "evidence_strength": evidence_strength,
        "conflict_status": "NONE",
        "provenance": provenance or {},
    }


def _source_record_id(facility: Dict[str, Any]) -> str:
    return str(
        facility.get("nevada_license_id")
        or facility.get("business_license_id")
        or facility.get("cms_ccn")
        or facility.get("canonical_id")
        or "UNKNOWN"
    )


def _synthesize_nevada_evidence(canonical_rows: List[Dict[str, Any]], generated_at: Optional[str]) -> List[Dict[str, Any]]:
    """Create governed runtime evidence only from facts already present in Nevada canonical data.

    Facility-type implications such as ADL support for an RFG are deliberately labeled
    taxonomy inference. UNKNOWN is never converted to NO and service-level capabilities
    such as transfer help/medication management remain UNKNOWN unless directly supported.
    """
    rows: List[Dict[str, Any]] = []
    for facility in canonical_rows:
        canonical_id = str(facility.get("canonical_id") or "").strip()
        if not canonical_id:
            continue
        canonical_type = str(facility.get("canonical_type") or "UNKNOWN").strip().upper()
        record_id = _source_record_id(facility)
        detail_url = facility.get("detail_url")
        base_provenance = {
            "source_family": "Nevada HCQC / ALiS",
            "source_url": detail_url if isinstance(detail_url, str) and detail_url not in {"", "UNKNOWN"} else None,
            "canonical_field_origin": True,
        }

        license_status = facility.get("license_status")
        if license_status not in (None, "", "UNKNOWN"):
            rows.append(_evidence_row(
                canonical_id, "license_status", license_status,
                source="Nevada HCQC / ALiS",
                source_record_id=record_id,
                evidence_date=generated_at,
                evidence_text="Nevada license status",
                provenance=base_provenance,
            ))

        capacity = facility.get("licensed_capacity")
        if capacity not in (None, "", "UNKNOWN"):
            rows.append(_evidence_row(
                canonical_id, "licensed_beds_capacity", capacity,
                source="Nevada HCQC / ALiS",
                source_record_id=record_id,
                evidence_date=generated_at,
                evidence_text="Licensed capacity",
                provenance=base_provenance,
            ))

        if canonical_type == "ASSISTED_LIVING_RFG":
            # RFG licensure is strong evidence of the care taxonomy, but not proof of a
            # particular resident-level service package. Keep it taxonomy inferred.
            rows.append(_evidence_row(
                canonical_id, "adl_support", "YES",
                source="Nevada HCQC / ALiS taxonomy",
                source_record_id=record_id,
                scope="SERVICE",
                evidence_date=generated_at,
                evidence_strength="TAXONOMY_INFERRED",
                evidence_text="Residential Facility for Groups taxonomy supports ADL assistance; exact service level requires direct verification",
                provenance=base_provenance,
            ))

        if canonical_type == "SKILLED_NURSING":
            cms_ccn = facility.get("cms_ccn")
            snf_source = "CMS / Nevada skilled nursing regulatory evidence" if cms_ccn not in (None, "", "UNKNOWN") else "Nevada HCQC / ALiS taxonomy"
            snf_provenance = {
                "source_family": "CMS / Nevada HCQC",
                "source_url": "https://data.cms.gov/provider-data/dataset/4pq5-n9py" if cms_ccn not in (None, "", "UNKNOWN") else base_provenance.get("source_url"),
                "canonical_field_origin": True,
            }
            for parameter_id, text in [
                ("skilled_nursing_capabilities", "Licensed skilled nursing facility"),
                ("nursing_24_7", "Skilled nursing regulatory taxonomy"),
                ("adl_support", "Skilled nursing taxonomy supports ADL assistance"),
            ]:
                rows.append(_evidence_row(
                    canonical_id, parameter_id, "YES",
                    source=snf_source,
                    source_record_id=str(cms_ccn or record_id),
                    scope="FACILITY" if parameter_id != "adl_support" else "SERVICE",
                    evidence_date=generated_at,
                    evidence_strength="REGULATORY_VERIFIED" if cms_ccn not in (None, "", "UNKNOWN") else "TAXONOMY_INFERRED",
                    evidence_text=text,
                    provenance=snf_provenance,
                ))
            if cms_ccn not in (None, "", "UNKNOWN"):
                rows.append(_evidence_row(
                    canonical_id, "medicare_attributes", "YES",
                    source="CMS Care Compare Provider Information",
                    source_record_id=str(cms_ccn),
                    evidence_date=generated_at,
                    evidence_text="CMS-certified nursing facility",
                    provenance=snf_provenance,
                ))

        if facility.get("memory_care_classification") == "CONFIRMED":
            memory_provenance = dict(base_provenance)
            memory_provenance["official_memory_care_evidence"] = facility.get("memory_care_evidence")
            for parameter_id in ("memory_care", "dementia_alz_programs"):
                rows.append(_evidence_row(
                    canonical_id, parameter_id, "YES",
                    source="Nevada HCQC / ALiS official detail",
                    source_record_id=record_id,
                    scope="PROGRAM",
                    evidence_date=generated_at,
                    evidence_text="Official Nevada Alzheimer/dementia endorsement or Category-II Alzheimer beds",
                    provenance=memory_provenance,
                ))

        cms_ccn = facility.get("cms_ccn")
        if cms_ccn not in (None, "", "UNKNOWN"):
            cms_provenance = {
                "source_family": "CMS",
                "source_url": "https://data.cms.gov/provider-data/dataset/4pq5-n9py",
                "canonical_field_origin": True,
            }
            inspection_rating = facility.get("cms_health_inspection_rating")
            if inspection_rating not in (None, "", "UNKNOWN"):
                rows.append(_evidence_row(
                    canonical_id, "inspection_rating", inspection_rating,
                    source="CMS Care Compare Provider Information",
                    source_record_id=str(cms_ccn),
                    evidence_date=str(facility.get("cms_processing_date") or generated_at or "") or None,
                    evidence_text="CMS health inspection rating",
                    provenance=cms_provenance,
                ))

        # Independent Living is intentionally not converted into ADL/medication care.
        # A confirmed IL property remains a housing classification unless care evidence exists.

    return rows


def _build_runtime_payload(market: str, active_signature: tuple[Any, ...]) -> Dict[str, Any]:
    registry_payload = _read_json(REGISTRY_PATH)
    canonical_path = resolve_canonical_universe_path(market)
    canonical_payload = _read_json(canonical_path)
    canonical = _canonical_records_for_market(canonical_payload, market)

    if market == "florida":
        evidence_payload = _read_json(FLORIDA_EVIDENCE_PATH)
        evidence = list(evidence_payload.get("records") or [])
        evidence_generated_at = evidence_payload.get("generated_at_utc")
    else:
        evidence_generated_at = canonical_payload.get("generated_at_utc")
        evidence = _synthesize_nevada_evidence(canonical, evidence_generated_at)
        evidence_payload = {
            "generated_at_utc": evidence_generated_at,
            "record_count": len(evidence),
            "records": evidence,
            "source": "synthesized_from_nevada_canonical_verified_fields",
        }

    registry = registry_payload.get("records") or []
    canonical_by_id = {
        str(row.get("canonical_id")): row
        for row in canonical
        if str(row.get("canonical_id") or "").strip()
    }
    evidence_lookup: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    evidence_best_lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in evidence:
        canonical_id = str(row.get("canonical_facility_id") or "").strip()
        parameter_id = str(row.get("parameter_id") or "").strip()
        if not canonical_id or not parameter_id or canonical_id not in canonical_by_id:
            continue
        facility_rows = evidence_lookup.setdefault(canonical_id, {})
        facility_rows.setdefault(parameter_id, []).append(row)

    for canonical_facility_id, facility_rows in evidence_lookup.items():
        evidence_best_lookup[canonical_facility_id] = {
            parameter_id: _best_evidence_row(rows)
            for parameter_id, rows in facility_rows.items()
        }

    runtime_version = hashlib.sha256(
        json.dumps(
            {
                "market": market,
                "registry_generated_at": registry_payload.get("generated_at_utc"),
                "evidence_generated_at": evidence_generated_at,
                "canonical_generated_at": canonical_payload.get("generated_at_utc"),
                "registry_count": len(registry),
                "evidence_count": len(evidence),
                "canonical_count": len(canonical_by_id),
                "signature": active_signature,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()[:16]

    return {
        "market": market,
        "registry_payload": registry_payload,
        "registry": registry,
        "canonical_by_id": canonical_by_id,
        "evidence_lookup": evidence_lookup,
        "evidence_best_lookup": evidence_best_lookup,
        "runtime_meta": {
            "runtime_version": runtime_version,
            "runtime_timestamp": registry_payload.get("generated_at_utc") or evidence_generated_at or canonical_payload.get("generated_at_utc"),
            "artifact_signature": active_signature,
            "market": market,
            "canonical_count": len(canonical_by_id),
            "evidence_count": len(evidence),
        },
    }


def _load_runtime() -> Dict[str, Any]:
    market = _effective_market()
    active_signature = _signature(market)
    with _CACHE_LOCK:
        cached = _CACHE.get(market)
        if cached and cached.get("signature") == active_signature:
            return cached["payload"]
        payload = _build_runtime_payload(market, active_signature)
        previous_swaps = int((cached or {}).get("swap_count") or 0)
        _CACHE[market] = {
            "payload": payload,
            "signature": active_signature,
            "loaded_at": _utc_now_iso(),
            "swap_count": previous_swaps + 1,
            "last_swap_reason": "load_or_refresh",
        }
        logger.info(
            "runtime_cache_swapped market=%s canonical_count=%s evidence_count=%s runtime_version=%s",
            market,
            payload["runtime_meta"]["canonical_count"],
            payload["runtime_meta"]["evidence_count"],
            payload["runtime_meta"]["runtime_version"],
        )
        return payload


def get_parameter_registry_payload() -> Dict[str, Any]:
    return _load_runtime()["registry_payload"]


def get_runtime_metadata() -> Dict[str, Optional[str]]:
    meta = _load_runtime().get("runtime_meta") or {}
    return {
        "runtime_version": str(meta.get("runtime_version") or ""),
        "runtime_timestamp": meta.get("runtime_timestamp"),
        "market": meta.get("market"),
    }


def refresh_runtime_cache(reason: str = "manual") -> Dict[str, Optional[str]]:
    market = _effective_market()
    with _CACHE_LOCK:
        _CACHE.pop(market, None)
    meta = _load_runtime().get("runtime_meta") or {}
    return {
        "reason": reason,
        "runtime_version": str(meta.get("runtime_version") or ""),
        "runtime_timestamp": meta.get("runtime_timestamp"),
        "market": meta.get("market"),
    }


def get_runtime_cache_status() -> Dict[str, Any]:
    market = _effective_market()
    with _CACHE_LOCK:
        cached = _CACHE.get(market) or {}
        payload = cached.get("payload") or {}
        meta = payload.get("runtime_meta") or {}
        return {
            "cache_loaded": bool(payload),
            "loaded_at": cached.get("loaded_at"),
            "swap_count": int(cached.get("swap_count") or 0),
            "last_swap_reason": cached.get("last_swap_reason"),
            "signature": cached.get("signature"),
            "runtime_version": meta.get("runtime_version"),
            "runtime_timestamp": meta.get("runtime_timestamp"),
            "market": market,
            "canonical_count": meta.get("canonical_count"),
            "evidence_count": meta.get("evidence_count"),
        }


def get_all_canonical_facility_ids() -> List[str]:
    return list(_load_runtime()["canonical_by_id"].keys())


def get_canonical_facility_index() -> Dict[str, Dict[str, Any]]:
    return _load_runtime()["canonical_by_id"]


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


def _resolve_rows_for_facility_lean(
    canonical_facility_id: str,
    ordered_registry: List[Dict[str, Any]],
    evidence_best_lookup: Dict[str, Dict[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Same raw_value/source/detail_scope resolution as the full row builder, minus
    every field only used for client-facing display (category, provenance, evidence
    records, etc). Scoring only ever reads raw_value/source/detail_scope per
    parameter_id -- this exists so the per-candidate scoring pass over the full
    market doesn't pay for building ~15 unused fields x ~59 parameters x N facilities.
    """
    facility_best_rows = evidence_best_lookup.get(canonical_facility_id, {})
    resolved = []
    for parameter in ordered_registry:
        best = facility_best_rows.get(parameter["parameter_id"])
        if best is not None:
            raw_value = best.get("value")
            source = str(best.get("source") or "Not verified")
            detail_scope = str(best.get("scope") or parameter["applicable_scope"])
        else:
            raw_value = "UNKNOWN"
            source = "Not verified"
            detail_scope = parameter["applicable_scope"]
        if parameter["parameter_id"] == "current_availability":
            raw_value = "UNKNOWN"
        resolved.append({
            "parameter_id": parameter["parameter_id"],
            "raw_value": raw_value,
            "source": source,
            "detail_scope": detail_scope,
        })
    return resolved


def _resolve_rows_for_facility(
    canonical_facility_id: str,
    ordered_registry: List[Dict[str, Any]],
    evidence_lookup: Optional[Dict[str, Dict[str, List[Dict[str, Any]]]]],
    evidence_best_lookup: Dict[str, Dict[str, Dict[str, Any]]],
    include_evidence_records: bool = True,
) -> List[Dict[str, Any]]:
    facility_rows = (evidence_lookup or {}).get(canonical_facility_id, {})
    facility_best_rows = evidence_best_lookup.get(canonical_facility_id, {})
    resolved = []
    for parameter in ordered_registry:
        rows = facility_rows.get(parameter["parameter_id"], [])
        best = facility_best_rows.get(parameter["parameter_id"])
        if best is not None:
            raw_value = best.get("value")
            display_value = "Not verified" if raw_value == "UNKNOWN" else raw_value
            source = str(best.get("source") or "Not verified")
            last_verified = best.get("last_verified")
            detail_scope = str(best.get("scope") or parameter["applicable_scope"])
            scope_name = best.get("scope_name")
            source_record_id = best.get("source_record_id")
            evidence_confidence = best.get("confidence")
            evidence_strength = best.get("evidence_strength")
            provenance = best.get("provenance") or {}
            evidence_count = len(rows) if include_evidence_records else 0
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
            ] if include_evidence_records else []
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

        resolved.append({
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
        })
    return resolved


def get_facility_parameter_table(
    canonical_facility_id: str,
    need_tags: Optional[List[str]] = None,
    priority_parameter_ids: Optional[List[str]] = None,
    profile_key: Optional[str] = None,
    ordered_registry: Optional[List[Dict[str, Any]]] = None,
    include_evidence_records: bool = True,
    lean: bool = False,
) -> Dict[str, Any]:
    runtime = _load_runtime()
    facility = runtime["canonical_by_id"].get(canonical_facility_id)
    if not facility:
        raise KeyError(canonical_facility_id)
    ordered = ordered_registry or _ordered_registry(runtime["registry"], need_tags=need_tags, priority_parameter_ids=priority_parameter_ids, profile_key=profile_key)
    if lean:
        rows = _resolve_rows_for_facility_lean(canonical_facility_id, ordered, runtime["evidence_best_lookup"])
    else:
        rows = _resolve_rows_for_facility(
            canonical_facility_id,
            ordered,
            runtime["evidence_lookup"] if include_evidence_records else None,
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
