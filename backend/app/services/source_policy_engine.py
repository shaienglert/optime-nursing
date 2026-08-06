from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Tuple
from urllib.parse import urlparse


POLICY_VERSION = "source-policy-v1.0.0"
SCHEMA_VERSION = "0.2.0"
SUPPORTED_VERSIONS = [SCHEMA_VERSION]

LIFECYCLE_DISCOVERED = "DISCOVERED"
LIFECYCLE_UNDER_REVIEW = "UNDER_REVIEW"
LIFECYCLE_VALIDATED = "VALIDATED"
LIFECYCLE_APPROVED = "APPROVED"
LIFECYCLE_INTEGRATION_IN_PROGRESS = "INTEGRATION_IN_PROGRESS"
LIFECYCLE_INTEGRATED = "INTEGRATED"
LIFECYCLE_BLOCKED_TEMPORARILY = "BLOCKED_TEMPORARILY"
LIFECYCLE_REJECTED = "REJECTED"
LIFECYCLE_OWNER_DECISION_REQUIRED = "OWNER_DECISION_REQUIRED"

POLICY_AUTO_APPROVE = "AUTO_APPROVE"
POLICY_AUTO_INTEGRATED = "AUTO_INTEGRATED"
POLICY_AUTO_BLOCK = "AUTO_BLOCK_TEMPORARILY"
POLICY_AUTO_REJECT = "AUTO_REJECT"
POLICY_NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
POLICY_OWNER_REVIEW = "OWNER_REVIEW_REQUIRED"

CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

REASON_GOV_OFFICIAL = "GOV_OFFICIAL"
REASON_AUTHORITY_VERIFIED = "AUTHORITY_VERIFIED"
REASON_AUTHORITY_UNKNOWN = "AUTHORITY_UNKNOWN"
REASON_FORMAT_SUPPORTED = "FORMAT_SUPPORTED"
REASON_FORMAT_UNSUPPORTED = "FORMAT_UNSUPPORTED"
REASON_FORMAT_UNKNOWN = "FORMAT_UNKNOWN"
REASON_ACCESS_OK = "ACCESS_OK"
REASON_ACCESS_TEMP_FAIL = "ACCESS_TEMPORARILY_FAILED"
REASON_AUTH_REQUIRED = "AUTH_REQUIRED"
REASON_NO_EXPORT = "NO_MACHINE_READABLE_EXPORT"
REASON_LEGAL_CLEAR = "LEGAL_CLEAR"
REASON_LEGAL_UNCLEAR = "LEGAL_UNCLEAR"
REASON_LEGAL_PROHIBITED = "LEGAL_PROHIBITED"
REASON_RELEVANT = "RELEVANT_FACILITY_TYPES"
REASON_IRRELEVANT = "IRRELEVANT_SOURCE"
REASON_DUPLICATE = "DUPLICATE_SOURCE"
REASON_DATA_OK = "DATA_QUALITY_ACCEPTABLE"
REASON_DATA_FAILED = "DATA_QUALITY_FAILED"
REASON_SUCCESS_IMPORT = "SUCCESSFUL_IMPORT_EVIDENCE"
REASON_NOT_STARTED = "INTEGRATION_NOT_STARTED"
REASON_POLICY_CONFLICT = "POLICY_CONFLICT"
REASON_OWNER_COMMERCIAL = "OWNER_COMMERCIAL_DECISION"

GOVERNMENT_TOKENS = (
    "federal government",
    "state",
    "government",
    "cms",
    "nppes",
    "ahca",
    "healthfinder",
    "medicare",
    "nevada",
    "florida",
    "texas",
)

COMMERCIAL_DIRECTORY_DOMAINS = {
    "seniorly.com",
    "caring.com",
    "aplaceformom.com",
    "seniorhousingnet.com",
    "assistedliving.org",
    "nursinghomes.com",
}

SUPPORTED_SOURCE_TYPES = {"CSV", "XML", "API", "WEBSITE", "PORTAL_EXPORT", "SCRAPER"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_supported_versions(values: Any) -> List[str]:
    supported_versions: List[str] = []
    for value in values or []:
        version = str(value or "").strip()
        if not version or version in supported_versions:
            continue
        supported_versions.append(version)
    return supported_versions


def migrate(record: Mapping[str, Any]) -> Dict[str, Any]:
    shaped = dict(record)
    shaped["schema_version"] = SCHEMA_VERSION
    shaped["supported_versions"] = list(SUPPORTED_VERSIONS)

    policy_outcome = evaluate_source_policy(shaped)
    shaped["policy_version"] = policy_outcome["policy_version"]
    shaped["policy_status"] = policy_outcome["policy_status"]
    shaped["policy_reason_codes"] = policy_outcome["policy_reason_codes"]
    shaped["policy_confidence"] = policy_outcome["policy_confidence"]
    shaped["policy_missing_evidence"] = policy_outcome["missing_evidence"]
    shaped["policy_owner_review_required"] = policy_outcome["owner_review_required"]
    shaped["next_action"] = policy_outcome["next_action"]
    if policy_outcome.get("next_review_date"):
        shaped["next_review_date"] = policy_outcome["next_review_date"]
    for key, value in policy_outcome["status_dimensions"].items():
        shaped[key] = value
    return shaped


def validate(record: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    schema_version = str(record.get("schema_version") or "").strip()
    supported_versions = _normalize_supported_versions(record.get("supported_versions"))
    lifecycle_status = str(record.get("lifecycle_status") or "").strip().upper()

    if schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not supported_versions:
        errors.append("supported_versions is required")
    elif schema_version not in supported_versions:
        errors.append("schema_version must be included in supported_versions")
    elif not all(version.count(".") == 2 for version in supported_versions):
        errors.append("supported_versions must use MAJOR.MINOR.PATCH")

    if lifecycle_status and lifecycle_status not in {
        LIFECYCLE_DISCOVERED,
        LIFECYCLE_UNDER_REVIEW,
        LIFECYCLE_VALIDATED,
        LIFECYCLE_APPROVED,
        LIFECYCLE_INTEGRATION_IN_PROGRESS,
        LIFECYCLE_INTEGRATED,
        LIFECYCLE_BLOCKED_TEMPORARILY,
        LIFECYCLE_REJECTED,
        LIFECYCLE_OWNER_DECISION_REQUIRED,
    }:
        errors.append(f"Unsupported lifecycle status: {lifecycle_status}")

    policy_outcome = evaluate_source_policy(record)
    for key in ("policy_version", "policy_status", "policy_confidence", "policy_reason_codes", "next_action"):
        if record.get(key) and record.get(key) != policy_outcome.get(key):
            errors.append(f"{key} does not match evaluated source policy")
    if record.get("policy_missing_evidence") and list(record.get("policy_missing_evidence") or []) != policy_outcome["missing_evidence"]:
        errors.append("policy_missing_evidence does not match evaluated source policy")
    if bool(record.get("policy_owner_review_required")) != bool(policy_outcome["owner_review_required"]):
        errors.append("policy_owner_review_required does not match evaluated source policy")

    return errors


def canonical_domain(url: Any) -> str:
    value = str(url or "").strip().lower()
    if not value:
        return ""
    if "://" not in value:
        value = "https://" + value
    host = urlparse(value).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def _authority_verified(record: Mapping[str, Any]) -> bool:
    authority = str(record.get("authority_level") or "").strip().lower()
    return bool(authority) and _contains_any(authority, GOVERNMENT_TOKENS)


def _source_is_commercial_directory(record: Mapping[str, Any]) -> bool:
    domain = canonical_domain(record.get("official_url") or record.get("download_url") or record.get("api_url"))
    if domain in COMMERCIAL_DIRECTORY_DOMAINS:
        return True
    name = str(record.get("source_name") or "").strip().lower()
    return any(token in name for token in ("seniorly", "caring", "place for mom", "directory")) and not _authority_verified(record)


def _is_robots_endpoint(record: Mapping[str, Any]) -> bool:
    source_name = str(record.get("source_name") or "").lower()
    official_url = str(record.get("official_url") or "").lower()
    blocking_issue = str(record.get("blocking_issue") or "").lower()
    return "robots" in source_name or official_url.endswith("/robots.txt") or "non-facility-data endpoint" in blocking_issue


def _format_supported(record: Mapping[str, Any]) -> Tuple[str, List[str], List[str]]:
    source_type = str(record.get("source_type") or "").strip().upper()
    missing: List[str] = []
    reason_codes: List[str] = []
    if source_type in {"CSV", "XML", "API"}:
        if record.get("download_url") or record.get("api_url") or record.get("csv") or record.get("xml") or record.get("api"):
            reason_codes.append(REASON_FORMAT_SUPPORTED)
            return "SUPPORTED", reason_codes, missing
        missing.append("download_or_api_endpoint")
        reason_codes.append(REASON_FORMAT_UNKNOWN)
        return "UNKNOWN", reason_codes, missing
    if source_type in {"WEBSITE", "PORTAL_EXPORT", "SCRAPER"}:
        if record.get("scraper") or record.get("official_url"):
            reason_codes.append(REASON_FORMAT_SUPPORTED)
            return "SUPPORTED", reason_codes, missing
        missing.append("supported_connector")
        reason_codes.append(REASON_FORMAT_UNKNOWN)
        return "UNKNOWN", reason_codes, missing
    reason_codes.append(REASON_FORMAT_UNSUPPORTED)
    return "UNSUPPORTED", reason_codes, missing


def _access_status(record: Mapping[str, Any]) -> Tuple[str, List[str], List[str]]:
    reason_codes: List[str] = []
    missing: List[str] = []
    lifecycle = str(record.get("lifecycle_status") or "").strip().upper()
    blocking_issue = str(record.get("blocking_issue") or "").strip().lower()
    auth_req = str(record.get("authentication_requirement") or record.get("authentication") or "").strip().lower()
    if record.get("last_successful_import") or lifecycle == LIFECYCLE_INTEGRATED:
        reason_codes.append(REASON_ACCESS_OK)
        return "ACCESS_OK", reason_codes, missing
    if "paid" in auth_req or "subscription" in auth_req:
        reason_codes.append(REASON_AUTH_REQUIRED)
        return "AUTH_REQUIRED", reason_codes, missing
    if any(token in blocking_issue for token in ("403", "redirect", "loop", "outage", "rate limit", "temporarily", "fetch failure", "failed")):
        reason_codes.append(REASON_ACCESS_TEMP_FAIL)
        return "TEMPORARY_FAILURE", reason_codes, missing
    if "auth" in blocking_issue or "login" in blocking_issue:
        reason_codes.append(REASON_AUTH_REQUIRED)
        return "AUTH_REQUIRED", reason_codes, missing
    if "machine-readable" in blocking_issue or "no export" in blocking_issue:
        reason_codes.append(REASON_NO_EXPORT)
        return "NO_EXPORT", reason_codes, missing
    if record.get("official_url") or record.get("download_url") or record.get("api_url"):
        missing.append("access_test")
        return "UNKNOWN", reason_codes, missing
    missing.append("official_endpoint")
    return "UNKNOWN", reason_codes, missing


def _legal_status(record: Mapping[str, Any]) -> Tuple[str, List[str], List[str]]:
    reason_codes: List[str] = []
    missing: List[str] = []
    blocking_issue = str(record.get("blocking_issue") or "").lower()
    auth_req = str(record.get("authentication_requirement") or record.get("authentication") or "").lower()
    if "prohibited" in blocking_issue or "terms" in blocking_issue or "legal" in blocking_issue:
        if "unclear" in blocking_issue:
            reason_codes.append(REASON_LEGAL_UNCLEAR)
            return "LEGAL_UNCLEAR", reason_codes, missing
        reason_codes.append(REASON_LEGAL_PROHIBITED)
        return "LEGAL_PROHIBITED", reason_codes, missing
    if "paid" in auth_req or "subscription" in auth_req:
        reason_codes.append(REASON_LEGAL_UNCLEAR)
        return "LEGAL_UNCLEAR", reason_codes, missing
    reason_codes.append(REASON_LEGAL_CLEAR)
    return "LEGAL_CLEAR", reason_codes, missing


def _relevance_status(record: Mapping[str, Any]) -> Tuple[str, List[str], List[str]]:
    reason_codes: List[str] = []
    missing: List[str] = []
    facility_types = [str(item).strip() for item in (record.get("facility_types_covered") or []) if str(item).strip()]
    if _is_robots_endpoint(record) or _source_is_commercial_directory(record):
        reason_codes.append(REASON_IRRELEVANT)
        return "IRRELEVANT", reason_codes, missing
    if facility_types:
        reason_codes.append(REASON_RELEVANT)
        return "RELEVANT", reason_codes, missing
    missing.append("facility_types_covered")
    return "UNKNOWN", reason_codes, missing


def _data_quality_status(record: Mapping[str, Any]) -> Tuple[str, List[str], List[str]]:
    reason_codes: List[str] = []
    missing: List[str] = []
    if _is_robots_endpoint(record) or _source_is_commercial_directory(record):
        reason_codes.append(REASON_DATA_FAILED)
        return "DATA_QUALITY_FAILED", reason_codes, missing
    if record.get("failure_category") == "DATA_QUALITY":
        reason_codes.append(REASON_DATA_FAILED)
        return "DATA_QUALITY_FAILED", reason_codes, missing
    reason_codes.append(REASON_DATA_OK)
    return "DATA_QUALITY_ACCEPTABLE", reason_codes, missing


def _has_successful_import_evidence(record: Mapping[str, Any]) -> bool:
    lifecycle = str(record.get("lifecycle_status") or "").strip().upper()
    reason = str(record.get("reason") or "").lower()
    return bool(record.get("last_successful_import")) and (lifecycle == LIFECYCLE_INTEGRATED or "integrated" in reason or "successful import" in reason)


def _owner_review_required(record: Mapping[str, Any], legal_status: str, confidence: str, reason_codes: List[str]) -> bool:
    auth_req = str(record.get("authentication_requirement") or record.get("authentication") or "").lower()
    if record.get("owner_decision"):
        return True
    if "paid" in auth_req or "subscription" in auth_req:
        reason_codes.append(REASON_OWNER_COMMERCIAL)
        return True
    if legal_status == "LEGAL_UNCLEAR":
        return True
    return False


def _confidence(record: Mapping[str, Any], missing: List[str], reason_codes: List[str]) -> str:
    if REASON_SUCCESS_IMPORT in reason_codes or (_authority_verified(record) and REASON_FORMAT_SUPPORTED in reason_codes and REASON_ACCESS_OK in reason_codes):
        return CONFIDENCE_HIGH
    if missing:
        return CONFIDENCE_MEDIUM if len(missing) == 1 else CONFIDENCE_LOW
    return CONFIDENCE_MEDIUM


def evaluate_source_policy(record: Mapping[str, Any]) -> Dict[str, Any]:
    reason_codes: List[str] = []
    missing: List[str] = []

    if _authority_verified(record):
        reason_codes.extend([REASON_GOV_OFFICIAL, REASON_AUTHORITY_VERIFIED])
        authority_status = "AUTHORITY_VERIFIED"
    else:
        reason_codes.append(REASON_AUTHORITY_UNKNOWN)
        authority_status = "AUTHORITY_UNKNOWN"
        missing.append("authority_level")

    format_status, format_reasons, format_missing = _format_supported(record)
    access_status, access_reasons, access_missing = _access_status(record)
    legal_status, legal_reasons, legal_missing = _legal_status(record)
    relevance_status, relevance_reasons, relevance_missing = _relevance_status(record)
    data_quality_status, data_reasons, data_missing = _data_quality_status(record)

    reason_codes.extend(format_reasons + access_reasons + legal_reasons + relevance_reasons + data_reasons)
    missing.extend(format_missing + access_missing + legal_missing + relevance_missing + data_missing)

    if _has_successful_import_evidence(record):
        reason_codes.append(REASON_SUCCESS_IMPORT)
    else:
        reason_codes.append(REASON_NOT_STARTED)

    confidence = _confidence(record, missing, reason_codes)
    owner_review_required = _owner_review_required(record, legal_status, confidence, reason_codes)

    policy_status = POLICY_NEEDS_MORE_EVIDENCE
    proposed_lifecycle = LIFECYCLE_UNDER_REVIEW
    next_action = "Collect missing source evidence"
    next_review_date = None

    if _is_robots_endpoint(record) or _source_is_commercial_directory(record) or relevance_status == "IRRELEVANT":
        policy_status = POLICY_AUTO_REJECT
        proposed_lifecycle = LIFECYCLE_REJECTED
        next_action = "Retain rejection history; do not integrate"
    elif _has_successful_import_evidence(record):
        policy_status = POLICY_AUTO_INTEGRATED
        proposed_lifecycle = LIFECYCLE_INTEGRATED
        next_action = "Continue scheduled refresh"
    elif owner_review_required:
        policy_status = POLICY_OWNER_REVIEW
        proposed_lifecycle = LIFECYCLE_OWNER_DECISION_REQUIRED
        next_action = "Route to owner for explicit decision"
    elif access_status in {"TEMPORARY_FAILURE", "AUTH_REQUIRED", "NO_EXPORT"} and authority_status == "AUTHORITY_VERIFIED" and relevance_status == "RELEVANT":
        policy_status = POLICY_AUTO_BLOCK
        proposed_lifecycle = LIFECYCLE_BLOCKED_TEMPORARILY
        next_action = "Retry source access and re-run policy evaluation"
        next_review_date = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    elif authority_status == "AUTHORITY_VERIFIED" and relevance_status == "RELEVANT" and format_status == "SUPPORTED" and legal_status == "LEGAL_CLEAR" and data_quality_status == "DATA_QUALITY_ACCEPTABLE":
        policy_status = POLICY_AUTO_APPROVE
        proposed_lifecycle = LIFECYCLE_INTEGRATION_IN_PROGRESS if str(record.get("lifecycle_status") or "") == LIFECYCLE_INTEGRATION_IN_PROGRESS else LIFECYCLE_APPROVED
        next_action = "Queue source for governed integration"
    else:
        policy_status = POLICY_NEEDS_MORE_EVIDENCE
        proposed_lifecycle = LIFECYCLE_UNDER_REVIEW
        next_action = "Collect missing evidence and validate authority, format, and access"

    if policy_status == POLICY_OWNER_REVIEW:
        confidence = CONFIDENCE_LOW
    if policy_status == POLICY_AUTO_BLOCK and not next_review_date:
        next_review_date = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # Deduplicate reason codes while preserving order.
    deduped: List[str] = []
    seen = set()
    for code in reason_codes:
        if code in seen:
            continue
        seen.add(code)
        deduped.append(code)

    deduped_missing: List[str] = []
    missing_seen = set()
    for item in missing:
        if not item or item in missing_seen:
            continue
        missing_seen.add(item)
        deduped_missing.append(item)

    return {
        "policy_version": POLICY_VERSION,
        "policy_status": policy_status,
        "proposed_lifecycle_status": proposed_lifecycle,
        "policy_confidence": confidence,
        "policy_reason_codes": deduped,
        "missing_evidence": deduped_missing,
        "next_action": next_action,
        "next_review_date": next_review_date,
        "owner_review_required": owner_review_required,
        "status_dimensions": {
            "access_status": access_status,
            "format_status": format_status,
            "authority_status": authority_status,
            "relevance_status": relevance_status,
            "legal_status": legal_status,
            "data_quality_status": data_quality_status,
        },
    }