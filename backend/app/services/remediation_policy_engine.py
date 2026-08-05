from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping


MODE_DRY_RUN = "DRY_RUN"
MODE_ACTIVE_SAFE = "ACTIVE_SAFE"

CLASS_A = "CLASS_A"
CLASS_B = "CLASS_B"
CLASS_C = "CLASS_C"

ACTION_RETRY = "RETRY"
ACTION_RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
ACTION_REFRESH_AUTH = "REFRESH_AUTH"
ACTION_SWITCH_TO_APPROVED_ENDPOINT = "SWITCH_TO_APPROVED_ENDPOINT"
ACTION_SWITCH_TO_APPROVED_SOURCE = "SWITCH_TO_APPROVED_SOURCE"
ACTION_RESUME_FROM_CHECKPOINT = "RESUME_FROM_CHECKPOINT"
ACTION_REGENERATE_REPORT = "REGENERATE_REPORT"
ACTION_INVALIDATE_CACHE = "INVALIDATE_CACHE"
ACTION_REQUEUE_ARTIFACT = "REQUEUE_ARTIFACT"
ACTION_RERUN_VALIDATION = "RERUN_VALIDATION"
ACTION_RESTART_IDEMPOTENT_JOB = "RESTART_IDEMPOTENT_JOB"
ACTION_PAUSE_DOWNSTREAM = "PAUSE_DOWNSTREAM"
ACTION_RESUME_DOWNSTREAM = "RESUME_DOWNSTREAM"
ACTION_OPEN_OWNER_DECISION = "OPEN_OWNER_DECISION"
ACTION_MARK_TEMP_BLOCKED = "MARK_TEMPORARILY_BLOCKED"
ACTION_MARK_FAILED = "MARK_FAILED"

FAILURE_TRANSIENT_NETWORK = "TRANSIENT_NETWORK_FAILURE"
FAILURE_AUTH_EXPIRED = "AUTHENTICATION_EXPIRED"
FAILURE_RATE_LIMITED = "RATE_LIMITED"
FAILURE_REDIRECT_LOOP = "REDIRECT_LOOP"
FAILURE_ENDPOINT_MOVED = "ENDPOINT_MOVED"
FAILURE_FORMAT_CHANGED = "FORMAT_CHANGED"
FAILURE_SCHEMA_CHANGED = "SCHEMA_CHANGED"
FAILURE_EMPTY_OUTPUT = "EMPTY_UNEXPECTED_OUTPUT"
FAILURE_STALE_OUTPUT = "STALE_OUTPUT"
FAILURE_ARTIFACT_NOT_CONSUMED = "ARTIFACT_NOT_CONSUMED"
FAILURE_REGISTRY_REPORT_MISMATCH = "REGISTRY_REPORT_MISMATCH"
FAILURE_SOURCE_APPROVED_NOT_INTEGRATED = "SOURCE_APPROVED_NOT_INTEGRATED"
FAILURE_PIPELINE_TIMEOUT = "PIPELINE_TIMEOUT"
FAILURE_PROCESS_CRASHED = "PROCESS_CRASHED"
FAILURE_CHECKPOINT_CORRUPT = "CHECKPOINT_CORRUPT"
FAILURE_WRONG_MARKET_DATASET = "WRONG_MARKET_DATASET"
FAILURE_VALIDATION_FAILED = "VALIDATION_FAILED"
FAILURE_DEPENDENCY_GATE = "DEPENDENCY_GATE_VIOLATION"
FAILURE_DATA_CONFLICT = "DATA_CONFLICT"
FAILURE_LEGAL_UNCLEAR = "LEGAL_STATUS_UNCLEAR"
FAILURE_UNKNOWN = "UNKNOWN_FAILURE"

ALL_ACTIONS = {
    ACTION_RETRY,
    ACTION_RETRY_WITH_BACKOFF,
    ACTION_REFRESH_AUTH,
    ACTION_SWITCH_TO_APPROVED_ENDPOINT,
    ACTION_SWITCH_TO_APPROVED_SOURCE,
    ACTION_RESUME_FROM_CHECKPOINT,
    ACTION_REGENERATE_REPORT,
    ACTION_INVALIDATE_CACHE,
    ACTION_REQUEUE_ARTIFACT,
    ACTION_RERUN_VALIDATION,
    ACTION_RESTART_IDEMPOTENT_JOB,
    ACTION_PAUSE_DOWNSTREAM,
    ACTION_RESUME_DOWNSTREAM,
    ACTION_OPEN_OWNER_DECISION,
    ACTION_MARK_TEMP_BLOCKED,
    ACTION_MARK_FAILED,
}


@dataclass
class RemediationDecision:
    remediation_action: str
    remediation_class: str
    confidence: str
    allowed_to_execute: bool
    verification_plan: List[str]
    rollback_plan: List[str]
    escalation_reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "remediation_action": self.remediation_action,
            "remediation_class": self.remediation_class,
            "confidence": self.confidence,
            "allowed_to_execute": self.allowed_to_execute,
            "verification_plan": list(self.verification_plan),
            "rollback_plan": list(self.rollback_plan),
            "escalation_reason": self.escalation_reason,
        }


def evaluate_remediation_policy(event: Mapping[str, Any], mode: str = MODE_DRY_RUN) -> Dict[str, Any]:
    failure_type = str(event.get("failure_type") or FAILURE_UNKNOWN)
    retry_count = int(event.get("retry_count") or 0)
    owner_gate_required = bool(event.get("owner_gate_required"))
    data_mutation_risk = str(event.get("data_mutation_risk") or "LOW").upper()
    legal_risk = str(event.get("legal_risk") or "LOW").upper()
    approved_fallback_available = bool(event.get("approved_fallback_available"))
    component_type = str(event.get("component_type") or "UNKNOWN")
    dependency_impact = str(event.get("dependency_impact") or "LOCAL").upper()

    action = ACTION_MARK_FAILED
    remediation_class = CLASS_A
    confidence = "MEDIUM"
    verification_plan = ["Confirm failure classification", "Confirm no unrelated data changed"]
    rollback_plan = ["No-op"]
    escalation_reason = ""

    if failure_type in {FAILURE_TRANSIENT_NETWORK, FAILURE_PIPELINE_TIMEOUT, FAILURE_PROCESS_CRASHED}:
        action = ACTION_RETRY_WITH_BACKOFF if retry_count > 0 else ACTION_RETRY
        remediation_class = CLASS_A
        confidence = "HIGH"
        verification_plan.extend(["Confirm command reran", "Confirm expected output exists", "Confirm output is non-empty and plausible"])
    elif failure_type == FAILURE_AUTH_EXPIRED:
        action = ACTION_REFRESH_AUTH
        remediation_class = CLASS_A
        confidence = "HIGH"
        verification_plan.extend(["Confirm refreshed credentials are valid", "Confirm source fetch succeeds"])
    elif failure_type in {FAILURE_REDIRECT_LOOP, FAILURE_ENDPOINT_MOVED}:
        action = ACTION_SWITCH_TO_APPROVED_ENDPOINT if approved_fallback_available else ACTION_MARK_TEMP_BLOCKED
        remediation_class = CLASS_A if approved_fallback_available else CLASS_B
        confidence = "MEDIUM"
        verification_plan.extend(["Confirm endpoint returns expected schema or page class"])
    elif failure_type in {FAILURE_STALE_OUTPUT, FAILURE_REGISTRY_REPORT_MISMATCH}:
        action = ACTION_REGENERATE_REPORT
        remediation_class = CLASS_A
        confidence = "HIGH"
        verification_plan.extend(["Confirm regenerated report matches authoritative registry state"])
    elif failure_type == FAILURE_ARTIFACT_NOT_CONSUMED:
        action = ACTION_REQUEUE_ARTIFACT
        remediation_class = CLASS_A
        confidence = "HIGH"
        verification_plan.extend(["Confirm downstream consumer receives artifact", "Confirm queue clears"])
    elif failure_type == FAILURE_WRONG_MARKET_DATASET:
        action = ACTION_PAUSE_DOWNSTREAM
        remediation_class = CLASS_B
        confidence = "HIGH"
        verification_plan.extend(["Confirm downstream paused", "Confirm lowest failed prerequisite identified"])
        rollback_plan = ["Restore prior downstream state after correct prerequisite passes"]
    elif failure_type in {FAILURE_SOURCE_APPROVED_NOT_INTEGRATED, FAILURE_VALIDATION_FAILED, FAILURE_FORMAT_CHANGED, FAILURE_SCHEMA_CHANGED, FAILURE_CHECKPOINT_CORRUPT}:
        action = ACTION_RERUN_VALIDATION if failure_type == FAILURE_VALIDATION_FAILED else ACTION_RESTART_IDEMPOTENT_JOB
        remediation_class = CLASS_B
        confidence = "MEDIUM"
        verification_plan.extend(["Confirm validator PASS", "Confirm registry updated", "Confirm downstream remains paused until PASS"])
        rollback_plan = ["Restore affected registry snapshot", "Restore prior artifact version and checksums"]
    elif failure_type in {FAILURE_DATA_CONFLICT, FAILURE_LEGAL_UNCLEAR}:
        action = ACTION_OPEN_OWNER_DECISION
        remediation_class = CLASS_C
        confidence = "LOW"
        escalation_reason = "Owner review required by policy"
        rollback_plan = ["Preserve current governed state"]
    else:
        action = ACTION_MARK_FAILED
        remediation_class = CLASS_B if component_type in {"SOURCE", "CANONICAL", "REPORT"} else CLASS_A
        confidence = "LOW"
        escalation_reason = "No deterministic automatic remediation classified"

    if retry_count >= int(event.get("retry_budget", 3) or 3) and remediation_class != CLASS_C:
        action = ACTION_OPEN_OWNER_DECISION if owner_gate_required or legal_risk == "HIGH" else ACTION_MARK_TEMP_BLOCKED
        remediation_class = CLASS_C if owner_gate_required or legal_risk == "HIGH" else CLASS_B
        confidence = "LOW"
        escalation_reason = "Retry budget exhausted"

    if dependency_impact == "DOWNSTREAM_BLOCKED":
        verification_plan.insert(0, "Confirm dependent components paused before remediation")

    if data_mutation_risk == "HIGH" or legal_risk == "HIGH":
        remediation_class = CLASS_C
        action = ACTION_OPEN_OWNER_DECISION
        confidence = "LOW"
        escalation_reason = escalation_reason or "High risk remediation requires owner approval"

    allowed_to_execute = mode == MODE_ACTIVE_SAFE and remediation_class == CLASS_A
    if remediation_class == CLASS_B:
        allowed_to_execute = mode == MODE_ACTIVE_SAFE and bool(event.get("governed_machine_gate_passed"))
    if remediation_class == CLASS_C:
        allowed_to_execute = False

    decision = RemediationDecision(
        remediation_action=action,
        remediation_class=remediation_class,
        confidence=confidence,
        allowed_to_execute=allowed_to_execute,
        verification_plan=verification_plan,
        rollback_plan=rollback_plan,
        escalation_reason=escalation_reason,
    )
    return decision.as_dict()