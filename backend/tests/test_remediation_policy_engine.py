from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.remediation_policy_engine import (
    ACTION_MARK_FAILED,
    ACTION_REGENERATE_REPORT,
    ACTION_REQUEUE_ARTIFACT,
    ACTION_RESTART_IDEMPOTENT_JOB,
    ACTION_RETRY,
    ACTION_RETRY_WITH_BACKOFF,
    ACTION_OPEN_OWNER_DECISION,
    CLASS_A,
    CLASS_B,
    CLASS_C,
    FAILURE_ARTIFACT_NOT_CONSUMED,
    FAILURE_DATA_CONFLICT,
    FAILURE_LEGAL_UNCLEAR,
    FAILURE_SOURCE_APPROVED_NOT_INTEGRATED,
    FAILURE_TRANSIENT_NETWORK,
    FAILURE_VALIDATION_FAILED,
    FAILURE_WRONG_MARKET_DATASET,
    MODE_ACTIVE_SAFE,
    MODE_DRY_RUN,
    evaluate_remediation_policy,
)


def test_transient_source_failure_auto_retried() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_TRANSIENT_NETWORK, "retry_count": 0, "component_type": "SOURCE"}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_action"] == ACTION_RETRY
    assert decision["remediation_class"] == CLASS_A
    assert decision["allowed_to_execute"] is True


def test_repeated_failure_stops_after_retry_budget() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_TRANSIENT_NETWORK, "retry_count": 3, "retry_budget": 3, "component_type": "SOURCE"}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_action"] != ACTION_RETRY


def test_stale_report_regenerated_from_registry() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_ARTIFACT_NOT_CONSUMED, "component_type": "REPORT"}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_action"] == ACTION_REQUEUE_ARTIFACT


def test_unconsumed_artifact_requeued() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_ARTIFACT_NOT_CONSUMED, "component_type": "REPORT"}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_action"] == ACTION_REQUEUE_ARTIFACT


def test_wrong_market_dataset_blocks_downstream() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_WRONG_MARKET_DATASET, "component_type": "CANONICAL", "dependency_impact": "DOWNSTREAM_BLOCKED", "governed_machine_gate_passed": False}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_class"] == CLASS_B
    assert decision["allowed_to_execute"] is False


def test_validation_failure_prevents_downstream_resume() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_VALIDATION_FAILED, "component_type": "CANONICAL", "governed_machine_gate_passed": False}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_class"] == CLASS_B
    assert decision["allowed_to_execute"] is False


def test_class_c_action_requires_owner_approval() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_LEGAL_UNCLEAR, "component_type": "SOURCE"}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_class"] == CLASS_C
    assert decision["allowed_to_execute"] is False
    assert decision["remediation_action"] == ACTION_OPEN_OWNER_DECISION


def test_no_arbitrary_command_execution() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_SOURCE_APPROVED_NOT_INTEGRATED, "component_type": "SOURCE"}, mode=MODE_DRY_RUN)
    assert decision["remediation_action"] in {
        ACTION_MARK_FAILED,
        ACTION_OPEN_OWNER_DECISION,
        ACTION_REQUEUE_ARTIFACT,
        ACTION_REGENERATE_REPORT,
        ACTION_RESTART_IDEMPOTENT_JOB,
        ACTION_RETRY,
        ACTION_RETRY_WITH_BACKOFF,
    }


def test_data_conflict_escalates_to_owner() -> None:
    decision = evaluate_remediation_policy({"failure_type": FAILURE_DATA_CONFLICT, "component_type": "CANONICAL"}, mode=MODE_ACTIVE_SAFE)
    assert decision["remediation_class"] == CLASS_C