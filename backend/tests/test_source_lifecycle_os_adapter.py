from __future__ import annotations

from datetime import datetime, timezone

from app.services.source_lifecycle_os_adapter import (
    map_lifecycle_state_to_os,
    map_reason_codes_to_os,
    normalize_policy_outcome_to_os,
    normalize_source_lifecycle_record_to_os,
    normalize_source_lifecycle_snapshot_to_os,
    normalize_status_snapshot_to_os,
    validate_os_contract_record,
    validate_os_contract_snapshot,
)
from app.services.source_lifecycle_service import generate_status_snapshot, migrate
from app.services.source_policy_engine import evaluate_source_policy


def _base_record() -> dict:
    return {
        "source_id": "SRC-EQ-001",
        "source_name": "Public Registry",
        "market": "global",
        "state": "NA",
        "authority_level": "government authority",
        "source_type": "API",
        "api_url": "https://public.example/api",
        "facility_types_covered": ["TypeA"],
        "supported_versions": ["0.2.0"],
        "schema_version": "0.2.0",
        "lifecycle_status": "UNDER_REVIEW",
    }


def test_normalized_records_validate_against_os_contract_shape() -> None:
    payload = migrate(
        {
            "records": [
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-002",
                    "lifecycle_status": "INTEGRATED",
                    "last_successful_import": "2026-08-06T00:00:00Z",
                    "reason": "integrated from successful import",
                },
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-003",
                    "source_name": "Rejected Source",
                    "lifecycle_status": "REJECTED",
                    "reason": "Retain rejection history; do not integrate",
                    "official_url": "https://public.example/robots.txt",
                },
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-004",
                    "source_name": "Blocked Source",
                    "lifecycle_status": "BLOCKED_TEMPORARILY",
                    "next_review_date": "2026-08-10T00:00:00Z",
                    "blocking_issue": "403 temporary failure",
                },
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-005",
                    "source_name": "Owner Decision Source",
                    "lifecycle_status": "OWNER_DECISION_REQUIRED",
                    "owner_decision": "Commercial contract review required",
                },
            ]
        }
    )

    normalized = normalize_source_lifecycle_snapshot_to_os(payload)
    assert validate_os_contract_snapshot(normalized) == []


def test_explicit_state_mapping_and_stale_projection_behavior() -> None:
    record = normalize_source_lifecycle_record_to_os(
        {
            **_base_record(),
            "lifecycle_status": "INTEGRATED",
            "last_successful_import": "2026-08-01T00:00:00Z",
            "next_review_date": "2026-08-02T00:00:00Z",
        },
        os_contract_requires_stale=False,
        reference_time=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    assert record["lifecycleState"] == "INTEGRATED"

    stale_projected = normalize_source_lifecycle_record_to_os(
        {
            **_base_record(),
            "lifecycle_status": "INTEGRATED",
            "last_successful_import": "2026-08-01T00:00:00Z",
            "next_review_date": "2026-08-02T00:00:00Z",
        },
        os_contract_requires_stale=True,
        reference_time=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )
    assert stale_projected["lifecycleState"] == "STALE"

    assert map_lifecycle_state_to_os("OWNER_DECISION_REQUIRED") == "OWNER_DECISION_REQUIRED"


def test_explicit_reason_code_alias_mapping() -> None:
    mapped = map_reason_codes_to_os(
        [
            "RELEVANT_FACILITY_TYPES",
            "SUCCESSFUL_IMPORT_EVIDENCE",
            "AUTHORITY_VERIFIED",
            "RELEVANT_FACILITY_TYPES",
        ]
    )
    assert mapped == [
        "RELEVANT_SOURCE",
        "SUCCESSFUL_INTEGRATION_EVIDENCE",
        "AUTHORITY_VERIFIED",
    ]


def test_policy_status_confidence_missing_evidence_and_scheduling_parity() -> None:
    policy_outcome = evaluate_source_policy(
        {
            **_base_record(),
            "authentication_requirement": "paid subscription",
        }
    )
    normalized_policy = normalize_policy_outcome_to_os(policy_outcome)

    assert normalized_policy["policyStatus"] == policy_outcome["policy_status"]
    assert normalized_policy["policyConfidence"] == policy_outcome["policy_confidence"]
    assert normalized_policy["nextAction"] == policy_outcome["next_action"]
    assert normalized_policy["ownerReviewRequired"] == bool(policy_outcome["owner_review_required"])
    assert normalized_policy["missingEvidence"] == []

    blocked_outcome = evaluate_source_policy(
        {
            **_base_record(),
            "blocking_issue": "403 temporary failure",
        }
    )
    blocked_normalized = normalize_policy_outcome_to_os(blocked_outcome)
    assert blocked_normalized["policyStatus"] == "AUTO_BLOCK_TEMPORARILY"
    assert blocked_normalized["nextReviewAt"] is not None


def test_blockers_and_readiness_counts_remain_equivalent() -> None:
    payload = migrate(
        {
            "records": [
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-A1",
                    "source_name": "Integrated Source",
                    "priority": "P0",
                    "lifecycle_status": "INTEGRATED",
                    "last_successful_import": "2026-08-06T00:00:00Z",
                    "reason": "integrated from successful import",
                },
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-A2",
                    "source_name": "Blocked Source",
                    "priority": "P0",
                    "lifecycle_status": "BLOCKED_TEMPORARILY",
                    "next_review_date": "2026-08-10T00:00:00Z",
                    "blocking_issue": "403 temporary failure",
                    "policy_reason_codes": ["ACCESS_TEMPORARILY_FAILED"],
                },
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-A3",
                    "source_name": "Under Review Source",
                    "priority": "P0",
                    "lifecycle_status": "UNDER_REVIEW",
                },
                {
                    **_base_record(),
                    "source_id": "SRC-EQ-A4",
                    "source_name": "Owner Decision Source",
                    "priority": "P0",
                    "lifecycle_status": "OWNER_DECISION_REQUIRED",
                    "policy_owner_review_required": True,
                },
            ]
        }
    )

    nursing_snapshot = generate_status_snapshot(payload)
    normalized_snapshot = normalize_status_snapshot_to_os(nursing_snapshot)

    assert normalized_snapshot["recordCount"] == nursing_snapshot["record_count"]
    assert len(normalized_snapshot["launchBlockers"]) == len(nursing_snapshot["launch_blockers"])
    assert len(normalized_snapshot["sourcesDueForRetry"]) == len(nursing_snapshot["sources_due_for_retry"])
    assert len(normalized_snapshot["sourcesDueForValidation"]) == len(nursing_snapshot["sources_due_for_validation"])
    assert normalized_snapshot["ownerDecisionCount"] == nursing_snapshot["owner_decision_count"]
    assert normalized_snapshot["segmentReadiness"]["global"]["launchBlockerCount"] == nursing_snapshot["market_readiness"]["global"]["launch_blocker_count"]


def test_missing_evidence_is_not_treated_as_negative_evidence() -> None:
    policy_outcome = evaluate_source_policy(
        {
            "source_id": "SRC-EQ-UNKNOWN",
            "source_name": "Unknown Evidence Source",
            "market": "global",
            "state": "NA",
            "authority_level": "",
            "source_type": "API",
            "api_url": "https://unknown.example/api",
            "lifecycle_status": "UNDER_REVIEW",
            "facility_types_covered": [],
        }
    )
    normalized = normalize_policy_outcome_to_os(policy_outcome)

    assert normalized["policyStatus"] == "NEEDS_MORE_EVIDENCE"
    assert "IRRELEVANT_SOURCE" not in normalized["reasonCodes"]
    assert "entity_types_covered" in normalized["missingEvidence"]
    assert normalized["proposedLifecycleState"] == "UNDER_REVIEW"


def test_record_validation_rejects_invalid_rejected_record_without_reason() -> None:
    record = normalize_source_lifecycle_record_to_os(
        {
            **_base_record(),
            "lifecycle_status": "REJECTED",
            "reason": "",
        }
    )
    errors = validate_os_contract_record(record)
    assert "REJECTED requires rejectionReason" in errors