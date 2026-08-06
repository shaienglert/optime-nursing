from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional


OS_LIFECYCLE_STATES = {
    "DISCOVERED",
    "UNDER_REVIEW",
    "VALIDATED",
    "APPROVED",
    "INTEGRATION_IN_PROGRESS",
    "INTEGRATED",
    "BLOCKED_TEMPORARILY",
    "OWNER_DECISION_REQUIRED",
    "REJECTED",
    "STALE",
}

NURSING_TO_OS_LIFECYCLE_STATE = {
    "DISCOVERED": "DISCOVERED",
    "UNDER_REVIEW": "UNDER_REVIEW",
    "VALIDATED": "VALIDATED",
    "APPROVED": "APPROVED",
    "INTEGRATION_IN_PROGRESS": "INTEGRATION_IN_PROGRESS",
    "INTEGRATED": "INTEGRATED",
    "BLOCKED_TEMPORARILY": "BLOCKED_TEMPORARILY",
    "OWNER_DECISION_REQUIRED": "OWNER_DECISION_REQUIRED",
    "REJECTED": "REJECTED",
}

NURSING_TO_OS_REASON_CODE = {
    "RELEVANT_FACILITY_TYPES": "RELEVANT_SOURCE",
    "SUCCESSFUL_IMPORT_EVIDENCE": "SUCCESSFUL_INTEGRATION_EVIDENCE",
}

NURSING_TO_OS_MISSING_EVIDENCE = {
    "facility_types_covered": "entity_types_covered",
}


def _to_iso_utc(raw: Any) -> Optional[str]:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dedupe(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def map_reason_codes_to_os(reason_codes: Iterable[Any]) -> List[str]:
    mapped: List[str] = []
    for raw in reason_codes:
        code = str(raw or "").strip()
        if not code:
            continue
        mapped.append(NURSING_TO_OS_REASON_CODE.get(code, code))
    return _dedupe(mapped)


def map_missing_evidence_to_os(items: Iterable[Any]) -> List[str]:
    mapped: List[str] = []
    for raw in items:
        value = str(raw or "").strip()
        if not value:
            continue
        mapped.append(NURSING_TO_OS_MISSING_EVIDENCE.get(value, value))
    return _dedupe(mapped)


def _project_stale_state(
    mapped_state: str,
    normalized_record: Mapping[str, Any],
    *,
    os_contract_requires_stale: bool,
    reference_time: Optional[datetime],
) -> str:
    if not os_contract_requires_stale:
        return mapped_state
    if mapped_state != "INTEGRATED":
        return mapped_state

    next_review = _to_iso_utc(normalized_record.get("nextReviewAt"))
    if not next_review:
        return mapped_state

    now = reference_time or datetime.now(timezone.utc)
    review_dt = datetime.fromisoformat(next_review.replace("Z", "+00:00"))
    if review_dt <= now:
        return "STALE"
    return mapped_state


def map_lifecycle_state_to_os(
    lifecycle_state: Any,
    normalized_record: Optional[Mapping[str, Any]] = None,
    *,
    os_contract_requires_stale: bool = False,
    reference_time: Optional[datetime] = None,
) -> str:
    source_state = str(lifecycle_state or "").strip().upper()
    mapped = NURSING_TO_OS_LIFECYCLE_STATE.get(source_state, source_state)
    if mapped not in OS_LIFECYCLE_STATES:
        return mapped
    if normalized_record is None:
        return mapped
    return _project_stale_state(
        mapped,
        normalized_record,
        os_contract_requires_stale=os_contract_requires_stale,
        reference_time=reference_time,
    )


def normalize_source_lifecycle_record_to_os(
    record: Mapping[str, Any],
    *,
    os_contract_requires_stale: bool = False,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {
        "sourceId": str(record.get("source_id") or "").strip(),
        "sourceName": str(record.get("source_name") or "").strip(),
        "schemaVersion": str(record.get("schema_version") or "").strip(),
        "supportedVersions": [str(v).strip() for v in (record.get("supported_versions") or []) if str(v).strip()],
        "createdAt": _to_iso_utc(record.get("created_at") or record.get("discovery_date")),
        "updatedAt": _to_iso_utc(record.get("updated_at")),
        "lastSuccessfulIntegrationAt": _to_iso_utc(record.get("last_successful_import")),
        "nextReviewAt": _to_iso_utc(record.get("next_review_date")),
        "blockedReason": str(record.get("blocking_issue") or "").strip() or None,
        "rejectionReason": str(record.get("reason") or "").strip() or None,
        "metadata": {
            "segment": str(record.get("market") or "").strip(),
            "region": str(record.get("state") or "").strip(),
            "authorityLevel": str(record.get("authority_level") or "").strip(),
            "sourceType": str(record.get("source_type") or "").strip(),
            "officialUrl": record.get("official_url"),
            "apiUrl": record.get("api_url") or record.get("api"),
            "downloadUrl": record.get("download_url") or record.get("csv") or record.get("xml"),
            "authRequirement": record.get("authentication_requirement") or record.get("authentication"),
            "policyStatus": record.get("policy_status"),
            "policyConfidence": record.get("policy_confidence"),
            "policyVersion": record.get("policy_version"),
            "policyOwnerReviewRequired": bool(record.get("policy_owner_review_required")),
            "reasonCodes": map_reason_codes_to_os(record.get("policy_reason_codes") or []),
            "missingEvidence": map_missing_evidence_to_os(record.get("policy_missing_evidence") or []),
            "nextAction": record.get("next_action"),
            "statusDimensions": {
                "accessStatus": record.get("access_status"),
                "formatStatus": record.get("format_status"),
                "authorityStatus": record.get("authority_status"),
                "relevanceStatus": record.get("relevance_status"),
                "legalStatus": record.get("legal_status"),
                "dataQualityStatus": record.get("data_quality_status"),
            },
            "entityTypesCovered": list(record.get("facility_types_covered") or []),
            "scopesAffected": list(record.get("markets_affected") or []),
            "ownerDecision": record.get("owner_decision"),
            "ownerDecisionAt": _to_iso_utc(record.get("owner_decision_date")),
            "registryVersion": record.get("registry_version"),
            "rawLifecycleState": str(record.get("lifecycle_status") or "").strip(),
        },
    }

    mapped_state = map_lifecycle_state_to_os(
        record.get("lifecycle_status"),
        normalized,
        os_contract_requires_stale=os_contract_requires_stale,
        reference_time=reference_time,
    )
    normalized["lifecycleState"] = mapped_state

    if mapped_state != "REJECTED":
        normalized["rejectionReason"] = None

    return normalized


def normalize_source_lifecycle_snapshot_to_os(
    payload: Mapping[str, Any],
    *,
    os_contract_requires_stale: bool = False,
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    records = [
        normalize_source_lifecycle_record_to_os(
            record,
            os_contract_requires_stale=os_contract_requires_stale,
            reference_time=reference_time,
        )
        for record in (payload.get("records") or [])
    ]
    return {
        "generatedAt": _to_iso_utc(payload.get("generated_at_utc")) or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "schemaVersion": str(payload.get("schema_version") or "").strip(),
        "supportedVersions": [str(v).strip() for v in (payload.get("supported_versions") or []) if str(v).strip()],
        "records": records,
        "recordCount": len(records),
    }


def validate_os_contract_record(record: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    lifecycle_state = str(record.get("lifecycleState") or "").strip().upper()
    source_id = str(record.get("sourceId") or "").strip()
    source_name = str(record.get("sourceName") or "").strip()
    schema_version = str(record.get("schemaVersion") or "").strip()
    supported_versions = [str(v).strip() for v in (record.get("supportedVersions") or []) if str(v).strip()]

    if not source_id:
        errors.append("sourceId is required")
    if not source_name:
        errors.append("sourceName is required")
    if lifecycle_state not in OS_LIFECYCLE_STATES:
        errors.append(f"Unsupported lifecycleState: {lifecycle_state}")
    if not schema_version:
        errors.append("schemaVersion is required")
    if not supported_versions:
        errors.append("supportedVersions is required")
    elif schema_version not in supported_versions:
        errors.append("schemaVersion must be included in supportedVersions")
    elif not all(value.count(".") == 2 for value in supported_versions):
        errors.append("supportedVersions must use MAJOR.MINOR.PATCH")

    if lifecycle_state == "INTEGRATED" and not _to_iso_utc(record.get("lastSuccessfulIntegrationAt")):
        errors.append("INTEGRATED requires lastSuccessfulIntegrationAt")
    if lifecycle_state == "BLOCKED_TEMPORARILY" and not _to_iso_utc(record.get("nextReviewAt")):
        errors.append("BLOCKED_TEMPORARILY requires nextReviewAt")
    if lifecycle_state == "REJECTED" and not str(record.get("rejectionReason") or "").strip():
        errors.append("REJECTED requires rejectionReason")
    if lifecycle_state == "STALE" and not _to_iso_utc(record.get("nextReviewAt")):
        errors.append("STALE requires nextReviewAt")

    return errors


def validate_os_contract_snapshot(snapshot: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    schema_version = str(snapshot.get("schemaVersion") or "").strip()
    supported_versions = [str(v).strip() for v in (snapshot.get("supportedVersions") or []) if str(v).strip()]

    if not schema_version:
        errors.append("schemaVersion is required")
    if not supported_versions:
        errors.append("supportedVersions is required")
    elif schema_version not in supported_versions:
        errors.append("schemaVersion must be included in supportedVersions")

    for index, record in enumerate(snapshot.get("records") or []):
        for error in validate_os_contract_record(record):
            errors.append(f"records[{index}]: {error}")

    if int(snapshot.get("recordCount") or 0) != len(snapshot.get("records") or []):
        errors.append("recordCount does not match records length")

    return errors


def normalize_policy_outcome_to_os(policy_outcome: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "policyStatus": policy_outcome.get("policy_status"),
        "proposedLifecycleState": map_lifecycle_state_to_os(policy_outcome.get("proposed_lifecycle_status")),
        "policyConfidence": policy_outcome.get("policy_confidence"),
        "reasonCodes": map_reason_codes_to_os(policy_outcome.get("policy_reason_codes") or []),
        "missingEvidence": map_missing_evidence_to_os(policy_outcome.get("missing_evidence") or []),
        "nextAction": policy_outcome.get("next_action"),
        "nextReviewAt": _to_iso_utc(policy_outcome.get("next_review_date")),
        "ownerReviewRequired": bool(policy_outcome.get("owner_review_required")),
    }


def normalize_status_snapshot_to_os(status_snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    status_distribution: Dict[str, int] = {}
    for key, count in (status_snapshot.get("status_distribution") or {}).items():
        mapped = map_lifecycle_state_to_os(key)
        status_distribution[mapped] = status_distribution.get(mapped, 0) + int(count)

    segment_readiness: Dict[str, Dict[str, Any]] = {}
    for market, row in (status_snapshot.get("market_readiness") or {}).items():
        segment_readiness[str(market)] = {
            "terminalStateComplete": bool(row.get("terminal_state_complete")),
            "launchReady": bool(row.get("launch_ready")),
            "launchBlockerCount": int(row.get("launch_blocker_count") or 0),
            "estimatedCoverage": row.get("estimated_canonical_universe_completeness"),
        }

    return {
        "recordCount": int(status_snapshot.get("record_count") or 0),
        "statusDistribution": status_distribution,
        "ownerDecisionCount": int(status_snapshot.get("owner_decision_count") or 0),
        "ownerDecisionPercentage": float(status_snapshot.get("owner_decision_percentage") or 0),
        "launchBlockers": list(status_snapshot.get("launch_blockers") or []),
        "sourcesDueForRetry": list(status_snapshot.get("sources_due_for_retry") or []),
        "sourcesDueForValidation": list(status_snapshot.get("sources_due_for_validation") or []),
        "policyVersionDistribution": dict(status_snapshot.get("policy_version_distribution") or {}),
        "segmentReadiness": segment_readiness,
    }