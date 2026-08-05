from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from app.services.source_policy_engine import (
    LIFECYCLE_APPROVED,
    LIFECYCLE_BLOCKED_TEMPORARILY,
    LIFECYCLE_DISCOVERED,
    LIFECYCLE_INTEGRATED,
    LIFECYCLE_INTEGRATION_IN_PROGRESS,
    LIFECYCLE_OWNER_DECISION_REQUIRED,
    LIFECYCLE_REJECTED,
    LIFECYCLE_UNDER_REVIEW,
    LIFECYCLE_VALIDATED,
    POLICY_VERSION,
    evaluate_source_policy,
    migrate as migrate_source_record,
    validate as validate_source_record,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
    SUPPORTED_VERSIONS as SOURCE_SUPPORTED_VERSIONS,
    utc_now_iso,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "database" / "source_lifecycle_registry.json"
STATUS_REPORT_PATH = REPO_ROOT / "reports" / "SOURCE_LIFECYCLE_STATUS.md"

REGISTRY_VERSION = "source-lifecycle-v2.0.0"
SCHEMA_VERSION = SOURCE_SCHEMA_VERSION
SUPPORTED_VERSIONS = list(SOURCE_SUPPORTED_VERSIONS)

LIFECYCLE_STATES = [
    LIFECYCLE_DISCOVERED,
    LIFECYCLE_UNDER_REVIEW,
    LIFECYCLE_VALIDATED,
    LIFECYCLE_APPROVED,
    LIFECYCLE_INTEGRATION_IN_PROGRESS,
    LIFECYCLE_INTEGRATED,
    LIFECYCLE_BLOCKED_TEMPORARILY,
    LIFECYCLE_REJECTED,
    LIFECYCLE_OWNER_DECISION_REQUIRED,
]

TERMINAL_STATES = {
    LIFECYCLE_INTEGRATED,
    LIFECYCLE_BLOCKED_TEMPORARILY,
    LIFECYCLE_REJECTED,
    LIFECYCLE_OWNER_DECISION_REQUIRED,
}

ALLOWED_TRANSITIONS = {
    LIFECYCLE_DISCOVERED: {LIFECYCLE_DISCOVERED, LIFECYCLE_UNDER_REVIEW, LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_REJECTED, LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_INTEGRATED},
    LIFECYCLE_UNDER_REVIEW: {LIFECYCLE_UNDER_REVIEW, LIFECYCLE_VALIDATED, LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_REJECTED, LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_INTEGRATED},
    LIFECYCLE_VALIDATED: {LIFECYCLE_VALIDATED, LIFECYCLE_APPROVED, LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_REJECTED, LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_INTEGRATED},
    LIFECYCLE_APPROVED: {LIFECYCLE_APPROVED, LIFECYCLE_INTEGRATION_IN_PROGRESS, LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_REJECTED, LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_INTEGRATED},
    LIFECYCLE_INTEGRATION_IN_PROGRESS: {LIFECYCLE_INTEGRATION_IN_PROGRESS, LIFECYCLE_INTEGRATED, LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_REJECTED, LIFECYCLE_OWNER_DECISION_REQUIRED},
    LIFECYCLE_INTEGRATED: {LIFECYCLE_INTEGRATED, LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_BLOCKED_TEMPORARILY},
    LIFECYCLE_BLOCKED_TEMPORARILY: {LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_UNDER_REVIEW, LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_REJECTED},
    LIFECYCLE_REJECTED: {LIFECYCLE_REJECTED},
    LIFECYCLE_OWNER_DECISION_REQUIRED: {LIFECYCLE_OWNER_DECISION_REQUIRED, LIFECYCLE_UNDER_REVIEW, LIFECYCLE_REJECTED, LIFECYCLE_APPROVED, LIFECYCLE_BLOCKED_TEMPORARILY},
}


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_source_id(record: Mapping[str, Any]) -> str:
    market = str(record.get("market") or "global").strip().upper()
    state = str(record.get("state") or "NA").strip().upper()
    source_name = str(record.get("source_name") or "source").strip()
    official_url = str(record.get("official_url") or record.get("download_url") or record.get("api_url") or "").strip().lower()
    seed = f"{market}|{state}|{source_name}|{official_url}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12].upper()
    return f"SRC-{market}-{digest}"


def default_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    now = utc_now_iso()
    source_id = str(record.get("source_id") or "").strip() or build_source_id(record)
    created_at = str(record.get("created_at") or record.get("discovery_date") or now)
    lifecycle_status = str(record.get("lifecycle_status") or LIFECYCLE_DISCOVERED)
    shaped = {
        **dict(record),
        "source_id": source_id,
        "source_name": str(record.get("source_name") or "").strip(),
        "market": str(record.get("market") or "").strip(),
        "state": str(record.get("state") or "").strip(),
        "authority_level": str(record.get("authority_level") or "UNKNOWN").strip(),
        "source_type": str(record.get("source_type") or "UNKNOWN").strip(),
        "schema_version": str(record.get("schema_version") or SCHEMA_VERSION).strip(),
        "supported_versions": list(record.get("supported_versions") or SUPPORTED_VERSIONS),
        "official_url": record.get("official_url"),
        "api_url": record.get("api_url") or record.get("api"),
        "download_url": record.get("download_url") or record.get("csv") or record.get("xml"),
        "authentication_requirement": record.get("authentication_requirement") or record.get("authentication") or "UNKNOWN",
        "discovery_agent": str(record.get("discovery_agent") or "Provider Intelligence Agent").strip(),
        "discovery_date": str(record.get("discovery_date") or now),
        "last_validation": record.get("last_validation") or None,
        "lifecycle_status": lifecycle_status,
        "policy_status": record.get("policy_status") or "UNSET",
        "policy_version": record.get("policy_version") or POLICY_VERSION,
        "policy_reason_codes": list(record.get("policy_reason_codes") or []),
        "policy_confidence": record.get("policy_confidence") or "UNKNOWN",
        "policy_owner_review_required": bool(record.get("policy_owner_review_required")) if record.get("policy_owner_review_required") is not None else lifecycle_status == LIFECYCLE_OWNER_DECISION_REQUIRED,
        "policy_missing_evidence": list(record.get("policy_missing_evidence") or []),
        "owner": str(record.get("owner") or "Data Quality & Trust Agent").strip(),
        "priority": str(record.get("priority") or "P1").strip(),
        "facility_types_covered": list(record.get("facility_types_covered") or []),
        "markets_affected": list(record.get("markets_affected") or ([str(record.get("market") or "").strip()] if str(record.get("market") or "").strip() else [])),
        "estimated_facility_coverage": record.get("estimated_facility_coverage"),
        "access_status": record.get("access_status") or "UNKNOWN",
        "format_status": record.get("format_status") or "UNKNOWN",
        "authority_status": record.get("authority_status") or "UNKNOWN",
        "relevance_status": record.get("relevance_status") or "UNKNOWN",
        "legal_status": record.get("legal_status") or "UNKNOWN",
        "data_quality_status": record.get("data_quality_status") or "UNKNOWN",
        "blocking_issue": record.get("blocking_issue"),
        "failure_category": record.get("failure_category"),
        "next_action": record.get("next_action") or "",
        "next_review_date": record.get("next_review_date"),
        "last_successful_import": record.get("last_successful_import"),
        "last_failed_import": record.get("last_failed_import"),
        "retry_count": int(record.get("retry_count") or 0),
        "dependencies": list(record.get("dependencies") or []),
        "evidence": list(record.get("evidence") or []),
        "owner_decision": record.get("owner_decision"),
        "owner_decision_date": record.get("owner_decision_date"),
        "created_at": created_at,
        "updated_at": str(record.get("updated_at") or now),
        "registry_version": record.get("registry_version") or REGISTRY_VERSION,
    }
    return shaped


def _normalize_supported_versions(values: Any) -> List[str]:
    versions: List[str] = []
    for value in values or []:
        version = str(value or "").strip()
        if not version or version in versions:
            continue
        versions.append(version)
    return versions


def migrate(payload: Mapping[str, Any]) -> Dict[str, Any]:
    records = [migrate_source_record(default_record(record)) for record in (payload.get("records") or [])]
    return {
        "generated_at_utc": str(payload.get("generated_at_utc") or utc_now_iso()),
        "schema_version": SCHEMA_VERSION,
        "supported_versions": list(SUPPORTED_VERSIONS),
        "registry_version": REGISTRY_VERSION,
        "lifecycle_states": list(LIFECYCLE_STATES),
        "governance_rule": "Every discovered source must be represented with exactly one lifecycle_status.",
        "record_count": len(records),
        "records": records,
    }


def validate(payload: Mapping[str, Any]) -> Dict[str, Any]:
    shaped = migrate(payload)
    errors: List[str] = []

    schema_version = str(shaped.get("schema_version") or "").strip()
    supported_versions = _normalize_supported_versions(shaped.get("supported_versions"))
    if schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not supported_versions:
        errors.append("supported_versions is required")
    elif schema_version not in supported_versions:
        errors.append("schema_version must be included in supported_versions")

    for record in shaped["records"]:
        record_errors = validate_source_record(record)
        errors.extend(f"{record.get('source_id')}: {message}" for message in record_errors)

    snapshot = generate_status_snapshot(shaped)
    if snapshot["record_count"] != shaped["record_count"]:
        errors.append("record_count does not match generated status snapshot")

    return {
        "valid": not errors,
        "errors": errors,
        "snapshot": snapshot,
        "payload": shaped,
    }


def ensure_registry_shape(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return migrate(payload)


def load_registry(path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    return migrate(_read_json(path))


def save_registry(payload: Mapping[str, Any], path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    shaped = migrate(payload)
    shaped["generated_at_utc"] = utc_now_iso()
    shaped["record_count"] = len(shaped["records"])
    _write_json(path, shaped)
    return shaped


def _find_record(payload: Dict[str, Any], source_id: str) -> Dict[str, Any]:
    for record in payload["records"]:
        if record["source_id"] == source_id:
            return record
    raise KeyError(f"Unknown source_id: {source_id}")


def _merge_unique_list(existing: Iterable[Any], incoming: Iterable[Any]) -> List[Any]:
    merged: List[Any] = []
    seen = set()
    for value in list(existing) + list(incoming):
        marker = json.dumps(value, sort_keys=True, default=str) if isinstance(value, (dict, list)) else str(value)
        if marker in seen:
            continue
        seen.add(marker)
        merged.append(value)
    return merged


def register_source_candidate(payload: Dict[str, Any], candidate: Mapping[str, Any], actor: str = "Provider Intelligence Agent") -> Dict[str, Any]:
    shaped = default_record({**dict(candidate), "discovery_agent": actor, "lifecycle_status": candidate.get("lifecycle_status") or LIFECYCLE_DISCOVERED})
    for record in payload["records"]:
        same_source = record["source_id"] == shaped["source_id"]
        same_identity = (
            record["market"] == shaped["market"]
            and record["state"] == shaped["state"]
            and record["source_name"] == shaped["source_name"]
            and str(record.get("official_url") or "") == str(shaped.get("official_url") or "")
        )
        if not (same_source or same_identity):
            continue
        record["evidence"] = _merge_unique_list(record.get("evidence") or [], shaped.get("evidence") or [])
        record["dependencies"] = _merge_unique_list(record.get("dependencies") or [], shaped.get("dependencies") or [])
        record["markets_affected"] = _merge_unique_list(record.get("markets_affected") or [], shaped.get("markets_affected") or [])
        record["facility_types_covered"] = _merge_unique_list(record.get("facility_types_covered") or [], shaped.get("facility_types_covered") or [])
        for key in ("official_url", "api_url", "download_url", "authentication_requirement", "authority_level", "source_type", "priority", "next_action", "blocking_issue", "failure_category"):
            if not record.get(key) and shaped.get(key):
                record[key] = shaped.get(key)
        record["updated_at"] = utc_now_iso()
        return record
    payload["records"].append(shaped)
    payload["record_count"] = len(payload["records"])
    return shaped


def update_source_evidence(payload: Dict[str, Any], source_id: str, evidence_item: Any) -> Dict[str, Any]:
    record = _find_record(payload, source_id)
    record["evidence"] = _merge_unique_list(record.get("evidence") or [], [evidence_item])
    record["updated_at"] = utc_now_iso()
    return record


def transition_source_status(
    record: Dict[str, Any],
    new_status: str,
    *,
    reason_codes: List[str],
    next_review_date: Optional[str] = None,
    last_successful_import: Optional[str] = None,
    owner_decision: Optional[str] = None,
    owner_decision_date: Optional[str] = None,
    allow_owner_override: bool = False,
) -> Dict[str, Any]:
    current = str(record.get("lifecycle_status") or LIFECYCLE_DISCOVERED)
    if not reason_codes:
        raise ValueError("Lifecycle transition requires reason codes")
    if new_status not in LIFECYCLE_STATES:
        raise ValueError(f"Unsupported lifecycle status: {new_status}")
    if new_status not in ALLOWED_TRANSITIONS.get(current, {current}):
        raise ValueError(f"Invalid lifecycle transition: {current} -> {new_status}")
    if current == LIFECYCLE_INTEGRATED and new_status != LIFECYCLE_INTEGRATED and not reason_codes:
        raise ValueError("Integrated source cannot lose status without evidence")
    if record.get("owner_decision") and new_status != current and not allow_owner_override:
        raise ValueError("Owner decision is preserved until explicitly reopened")
    if new_status == LIFECYCLE_DISCOVERED:
        raise ValueError("Transitions back to DISCOVERED are not allowed")
    if current == LIFECYCLE_DISCOVERED and new_status == LIFECYCLE_INTEGRATED and not last_successful_import:
        raise ValueError("DISCOVERED -> INTEGRATED requires successful import evidence")
    if new_status == LIFECYCLE_BLOCKED_TEMPORARILY and not next_review_date:
        raise ValueError("BLOCKED_TEMPORARILY requires next review date")
    if new_status == LIFECYCLE_INTEGRATED and not (last_successful_import or record.get("last_successful_import")):
        raise ValueError("INTEGRATED requires last successful import evidence")
    if current == LIFECYCLE_REJECTED and new_status == LIFECYCLE_INTEGRATED:
        raise ValueError("REJECTED -> INTEGRATED requires formal reopening")

    record["lifecycle_status"] = new_status
    record["policy_reason_codes"] = list(reason_codes)
    if next_review_date:
        record["next_review_date"] = next_review_date
    if last_successful_import:
        record["last_successful_import"] = last_successful_import
    if owner_decision is not None:
        record["owner_decision"] = owner_decision
    if owner_decision_date is not None:
        record["owner_decision_date"] = owner_decision_date
    record["updated_at"] = utc_now_iso()
    return record


def evaluate_source_policy_for_record(record: Dict[str, Any]) -> Dict[str, Any]:
    outcome = evaluate_source_policy(record)
    record["policy_status"] = outcome["policy_status"]
    record["policy_version"] = outcome["policy_version"]
    record["policy_reason_codes"] = outcome["policy_reason_codes"]
    record["policy_confidence"] = outcome["policy_confidence"]
    record["policy_owner_review_required"] = outcome["owner_review_required"]
    record["policy_missing_evidence"] = outcome["missing_evidence"]
    record["next_action"] = outcome["next_action"]
    if outcome.get("next_review_date"):
        record["next_review_date"] = outcome["next_review_date"]
    for key, value in outcome["status_dimensions"].items():
        record[key] = value
    return outcome


def record_import_success(payload: Dict[str, Any], source_id: str, *, imported_at: Optional[str] = None) -> Dict[str, Any]:
    record = _find_record(payload, source_id)
    imported = imported_at or utc_now_iso()
    record["last_successful_import"] = imported
    record["retry_count"] = 0
    return transition_source_status(record, LIFECYCLE_INTEGRATED, reason_codes=list(record.get("policy_reason_codes") or []), last_successful_import=imported, allow_owner_override=True)


def record_import_failure(payload: Dict[str, Any], source_id: str, *, failed_at: Optional[str] = None, failure_category: str = "UNKNOWN", blocking_issue: str = "") -> Dict[str, Any]:
    record = _find_record(payload, source_id)
    record["last_failed_import"] = failed_at or utc_now_iso()
    record["retry_count"] = int(record.get("retry_count") or 0) + 1
    record["failure_category"] = failure_category
    record["blocking_issue"] = blocking_issue
    next_review_date = record.get("next_review_date") or utc_now_iso()
    return transition_source_status(record, LIFECYCLE_BLOCKED_TEMPORARILY, reason_codes=list(record.get("policy_reason_codes") or ["ACCESS_TEMPORARILY_FAILED"]), next_review_date=next_review_date, allow_owner_override=True)


def request_owner_decision(payload: Dict[str, Any], source_id: str, *, decision_context: str) -> Dict[str, Any]:
    record = _find_record(payload, source_id)
    transition_source_status(record, LIFECYCLE_OWNER_DECISION_REQUIRED, reason_codes=list(record.get("policy_reason_codes") or ["POLICY_CONFLICT"]), allow_owner_override=True)
    record["owner_decision"] = decision_context
    record["owner_decision_date"] = utc_now_iso()
    record["policy_owner_review_required"] = True
    record["updated_at"] = utc_now_iso()
    return record


def _has_integrated_alternative(record: Mapping[str, Any], records: List[Mapping[str, Any]]) -> bool:
    alt = str(record.get("alternative_source") or "").strip()
    if not alt:
        return False
    target_types = set(record.get("facility_types_covered") or [])
    for candidate in records:
        if str(candidate.get("source_name") or "") != alt:
            continue
        if str(candidate.get("lifecycle_status") or "") != LIFECYCLE_INTEGRATED:
            continue
        overlap = target_types.intersection(set(candidate.get("facility_types_covered") or []))
        if overlap:
            return True
    return False


def list_launch_blockers(payload: Dict[str, Any], market: Optional[str] = None) -> List[Dict[str, Any]]:
    records = payload["records"]
    blockers: List[Dict[str, Any]] = []
    for record in records:
        if market and record.get("market") != market:
            continue
        if str(record.get("priority") or "") != "P0":
            continue
        status = str(record.get("lifecycle_status") or "")
        if status == LIFECYCLE_REJECTED and _has_integrated_alternative(record, records):
            continue
        if status == LIFECYCLE_BLOCKED_TEMPORARILY and _has_integrated_alternative(record, records):
            continue
        if status in {LIFECYCLE_UNDER_REVIEW, LIFECYCLE_VALIDATED, LIFECYCLE_APPROVED, LIFECYCLE_INTEGRATION_IN_PROGRESS, LIFECYCLE_BLOCKED_TEMPORARILY, LIFECYCLE_OWNER_DECISION_REQUIRED}:
            blockers.append(record)
    return blockers


def list_sources_due_for_review(payload: Dict[str, Any], reference_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    now = reference_time or datetime.now(timezone.utc)
    due: List[Dict[str, Any]] = []
    for record in payload["records"]:
        next_review = str(record.get("next_review_date") or "").strip()
        if not next_review:
            if str(record.get("lifecycle_status") or "") in {LIFECYCLE_UNDER_REVIEW, LIFECYCLE_VALIDATED, LIFECYCLE_APPROVED, LIFECYCLE_BLOCKED_TEMPORARILY}:
                due.append(record)
            continue
        try:
            review_dt = datetime.fromisoformat(next_review.replace("Z", "+00:00"))
        except ValueError:
            due.append(record)
            continue
        if review_dt <= now:
            due.append(record)
    return due


def generate_status_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    records = payload["records"]
    by_status: Dict[str, int] = {}
    by_market: Dict[str, int] = {}
    by_state: Dict[str, int] = {}
    by_authority: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    policy_versions: Dict[str, int] = {}
    for record in records:
        by_status[record["lifecycle_status"]] = by_status.get(record["lifecycle_status"], 0) + 1
        by_market[record["market"]] = by_market.get(record["market"], 0) + 1
        by_state[record["state"]] = by_state.get(record["state"], 0) + 1
        by_authority[record["authority_level"]] = by_authority.get(record["authority_level"], 0) + 1
        policy_versions[record["policy_version"]] = policy_versions.get(record["policy_version"], 0) + 1
        for facility_type in record.get("facility_types_covered") or []:
            by_type[facility_type] = by_type.get(facility_type, 0) + 1

    owner_decision_count = sum(1 for record in records if record.get("policy_owner_review_required") or record.get("lifecycle_status") == LIFECYCLE_OWNER_DECISION_REQUIRED)
    owner_decision_percentage = round((owner_decision_count * 100.0) / max(1, len(records)), 2)

    market_readiness: Dict[str, Dict[str, Any]] = {}
    for market in sorted({str(record.get("market") or "") for record in records}):
        market_records = [record for record in records if record.get("market") == market]
        terminal_complete = all(record.get("lifecycle_status") in TERMINAL_STATES for record in market_records)
        blockers = list_launch_blockers(payload, market=market)
        estimated_completeness = max((record.get("estimated_facility_coverage") or 0) for record in market_records) if market_records else 0
        market_readiness[market] = {
            "terminal_state_complete": terminal_complete,
            "launch_ready": terminal_complete and len(blockers) == 0 and estimated_completeness is not None,
            "launch_blocker_count": len(blockers),
            "estimated_canonical_universe_completeness": estimated_completeness,
        }

    due_for_retry = [record for record in records if record.get("lifecycle_status") == LIFECYCLE_BLOCKED_TEMPORARILY]
    due_for_validation = [record for record in records if record.get("lifecycle_status") in {LIFECYCLE_UNDER_REVIEW, LIFECYCLE_VALIDATED, LIFECYCLE_APPROVED, LIFECYCLE_INTEGRATION_IN_PROGRESS}]

    return {
        "generated_at_utc": utc_now_iso(),
        "record_count": len(records),
        "status_distribution": by_status,
        "coverage_by_market": by_market,
        "coverage_by_state": by_state,
        "coverage_by_authority": by_authority,
        "coverage_by_facility_type": by_type,
        "owner_decision_count": owner_decision_count,
        "owner_decision_percentage": owner_decision_percentage,
        "launch_blockers": list_launch_blockers(payload),
        "sources_due_for_retry": due_for_retry,
        "sources_due_for_validation": due_for_validation,
        "policy_version_distribution": policy_versions,
        "market_readiness": market_readiness,
    }


def render_status_report(payload: Dict[str, Any]) -> str:
    snapshot = generate_status_snapshot(payload)
    lines: List[str] = []
    lines.append("# Source Lifecycle Status")
    lines.append("")
    lines.append(f"Generated: `{snapshot['generated_at_utc']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total discovered authoritative sources in registry: **{snapshot['record_count']}**")
    for status, count in sorted(snapshot["status_distribution"].items()):
        lines.append(f"- {status}: **{count}**")
    lines.append(f"- Owner review required: **{snapshot['owner_decision_count']}** ({snapshot['owner_decision_percentage']}%)")
    lines.append("")
    lines.append("## Lifecycle Coverage By Status")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("| --- | ---: |")
    for status, count in sorted(snapshot["status_distribution"].items()):
        lines.append(f"| {status} | {count} |")
    lines.append("")
    lines.append("## Coverage By Market")
    lines.append("")
    lines.append("| Market | Sources | Terminal-state complete | Launch ready | Launch blockers |")
    lines.append("| --- | ---: | --- | --- | ---: |")
    for market, count in sorted(snapshot["coverage_by_market"].items()):
        readiness = snapshot["market_readiness"].get(market, {})
        lines.append(f"| {market} | {count} | {'YES' if readiness.get('terminal_state_complete') else 'NO'} | {'YES' if readiness.get('launch_ready') else 'NO'} | {readiness.get('launch_blocker_count', 0)} |")
    lines.append("")
    lines.append("## Coverage By State")
    lines.append("")
    lines.append("| State | Sources |")
    lines.append("| --- | ---: |")
    for state, count in sorted(snapshot["coverage_by_state"].items()):
        lines.append(f"| {state} | {count} |")
    lines.append("")
    lines.append("## Coverage By Authority")
    lines.append("")
    lines.append("| Authority | Sources |")
    lines.append("| --- | ---: |")
    for authority, count in sorted(snapshot["coverage_by_authority"].items()):
        lines.append(f"| {authority} | {count} |")
    lines.append("")
    lines.append("## Coverage By Facility Type")
    lines.append("")
    lines.append("| Facility Type | Sources |")
    lines.append("| --- | ---: |")
    for facility_type, count in sorted(snapshot["coverage_by_facility_type"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {facility_type} | {count} |")
    lines.append("")
    lines.append("## Top Missing Sources")
    lines.append("")
    lines.append("| Source ID | Source Name | Market | Lifecycle | Policy | Next Action |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    missing = [record for record in payload["records"] if record.get("lifecycle_status") != LIFECYCLE_INTEGRATED]
    missing.sort(key=lambda item: (str(item.get("priority") or ""), str(item.get("market") or ""), str(item.get("source_id") or "")))
    for record in missing[:10]:
        lines.append(f"| {record['source_id']} | {record['source_name']} | {record['market']} | {record['lifecycle_status']} | {record.get('policy_status') or ''} | {record.get('next_action') or ''} |")
    lines.append("")
    lines.append("## Launch Blockers")
    lines.append("")
    if snapshot["launch_blockers"]:
        lines.append("| Source ID | Source Name | Market | Lifecycle | Policy | Failure Category | Blocking Issue |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for record in snapshot["launch_blockers"]:
            lines.append(f"| {record['source_id']} | {record['source_name']} | {record['market']} | {record['lifecycle_status']} | {record.get('policy_status') or ''} | {record.get('failure_category') or ''} | {record.get('blocking_issue') or ''} |")
    else:
        lines.append("No current launch blockers.")
    return "\n".join(lines) + "\n"