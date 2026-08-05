import hashlib
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agent_execution import (
    AgentJobRun,
    AgentKnowledgeRecord,
    AgentKnowledgeRefreshEvent,
    AgentKnowledgeReportSnapshot,
    RecommendationKnowledgeUsageLog,
    SupervisorIncidentLog,
)
from app.services.agent_knowledge_reports import compute_supervisor_metrics, refresh_all_agent_reports
from app.services.email_service import configured_recipients, send_email_detailed
from app.services.remediation_policy_engine import MODE_ACTIVE_SAFE, MODE_DRY_RUN, evaluate_remediation_policy
from app.services.report_archive_service import create_report_artifacts, mark_report_sent
from app.services.source_lifecycle_service import load_registry, validate as validate_source_registry
from app.services.canonical_universe import configured_canonical_market
from app.services.agent_knowledge_reports import refresh_all_agent_reports
from app.services.platform_registry_service import evaluate_capability_assignment, load_platform_registry, run_platform_registry_self_audit


REPO_ROOT = Path(__file__).resolve().parents[3]
READINESS_PATH = REPO_ROOT / "reports" / "PLATFORM_READINESS_MATRIX.json"
DAILY_HEALTH_MD = REPO_ROOT / "reports" / "DAILY_SYSTEM_HEALTH.md"
DAILY_HEALTH_JSON = REPO_ROOT / "reports" / "DAILY_SYSTEM_HEALTH.json"
REMEDIATION_REGISTRY_PATH = REPO_ROOT / "database" / "remediation_action_registry.json"
RECOVERY_STATE_PATH = REPO_ROOT / "database" / "system_recovery_state.json"

STATUS_ACTIVE_AGENT = "ACTIVE_AGENT"
STATUS_IMPLEMENTED_NOT_SCHEDULED = "IMPLEMENTED_NOT_SCHEDULED"
STATUS_CONFIGURED_NOT_RUNNING = "CONFIGURED_NOT_RUNNING"
STATUS_SPECIFICATION_ONLY = "SPECIFICATION_ONLY"
STATUS_DISABLED = "DISABLED"
STATUS_RETIRED = "RETIRED"
STATUS_UNKNOWN = "UNKNOWN"

HEARTBEAT_RUN_ASSIGNED = "RUN_ASSIGNED"
HEARTBEAT_RUN_STARTED = "RUN_STARTED"
HEARTBEAT_RUN_HEARTBEAT = "RUN_HEARTBEAT"
HEARTBEAT_RUN_COMPLETED = "RUN_COMPLETED"
HEARTBEAT_RUN_FAILED = "RUN_FAILED"
HEARTBEAT_RUN_CANCELLED = "RUN_CANCELLED"
HEARTBEAT_RUN_TIMED_OUT = "RUN_TIMED_OUT"

TRACE_REQUESTED = "REQUESTED"
TRACE_ASSIGNED = "ASSIGNED"
TRACE_RUNNING = "RUNNING"
TRACE_BLOCKED = "BLOCKED"
TRACE_FAILED = "FAILED"
TRACE_COMPLETED_UNVALIDATED = "COMPLETED_UNVALIDATED"
TRACE_VALIDATED = "VALIDATED"
TRACE_STORED = "STORED"
TRACE_CONSUMED = "CONSUMED"
TRACE_ARCHIVED = "ARCHIVED"

OUTPUT_REUSABLE_KNOWLEDGE = "REUSABLE_KNOWLEDGE"
OUTPUT_FUTURE_MARKET_KNOWLEDGE = "FUTURE_MARKET_KNOWLEDGE"
OUTPUT_DUPLICATE = "DUPLICATE"
OUTPUT_STALE = "STALE"
OUTPUT_IRRELEVANT = "IRRELEVANT"
OUTPUT_NEEDS_REVIEW = "NEEDS_REVIEW"
OUTPUT_ORPHANED = "ORPHANED_OUTPUT"

QUALITY_ACCEPT = "ACCEPT"
QUALITY_ACCEPT_WARNING = "ACCEPT_WITH_WARNING"
QUALITY_RETURN = "RETURN_FOR_CORRECTION"
QUALITY_REJECT = "REJECT"
QUALITY_OWNER_REVIEW = "OWNER_REVIEW_REQUIRED"

WATCHDOG_INCIDENT_MISSED_CYCLE = "SUPERVISOR_MISSED_CYCLE_WATCHDOG"


def _read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _mode() -> str:
    mode = os.getenv("OPTIME_SUPERVISOR_MODE", MODE_DRY_RUN).strip().upper()
    return MODE_ACTIVE_SAFE if mode == MODE_ACTIVE_SAFE else MODE_DRY_RUN


def _resolve_active_market(market: str = "") -> str:
    resolved = str(market or configured_canonical_market() or "").strip().lower()
    normalized = {"nv": "nevada", "las vegas": "las-vegas", "fl": "florida", "miami": "florida"}.get(resolved, resolved)
    if normalized not in {"florida", "nevada", "las-vegas"}:
        raise ValueError(f"Unsupported active market '{normalized}'. Supported: florida, nevada, las-vegas")
    return normalized


def _now_iso() -> str:
    return _now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_recovery_state() -> Dict[str, object]:
    payload = _read_json(RECOVERY_STATE_PATH)
    return {
        "generated_at_utc": payload.get("generated_at_utc") or _now_iso(),
        "state_version": payload.get("state_version") or "system-recovery-state-v1.1.0",
        "mode": payload.get("mode") or _mode(),
        "quarantined_agents": payload.get("quarantined_agents") or [],
        "blocked_downstream_components": payload.get("blocked_downstream_components") or [],
        "last_successful_end_to_end_recovery": payload.get("last_successful_end_to_end_recovery"),
        "agent_retry_budgets": payload.get("agent_retry_budgets") or {},
        "supervisor_heartbeat": payload.get("supervisor_heartbeat") or {},
        "latest_generated_report": payload.get("latest_generated_report") or {},
        "latest_email_delivery": payload.get("latest_email_delivery") or {},
        "scheduler": payload.get("scheduler") or {},
    }


def _save_recovery_state(payload: Dict[str, object]) -> None:
    payload["generated_at_utc"] = _now_iso()
    _write_json(RECOVERY_STATE_PATH, payload)


def _load_remediation_registry() -> Dict[str, object]:
    payload = _read_json(REMEDIATION_REGISTRY_PATH)
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    return {
        "generated_at_utc": payload.get("generated_at_utc") or _now_iso(),
        "registry_version": payload.get("registry_version") or "remediation-registry-v1.1.0",
        "record_count": len(records),
        "records": records,
    }


def _save_remediation_registry(payload: Dict[str, object]) -> None:
    payload["generated_at_utc"] = _now_iso()
    payload["record_count"] = len(payload.get("records") or [])
    _write_json(REMEDIATION_REGISTRY_PATH, payload)


def _append_remediation_record(
    remediation_registry: Dict[str, object],
    *,
    alert_id: Optional[str],
    component_id: str,
    failure_type: str,
    action: str,
    remediation_class: str,
    status: str,
    evidence_before: Dict[str, object],
    evidence_after: Dict[str, object],
    verification_result: str,
    rollback_result: str,
    retry_count: int,
    owner_gate: bool,
    next_action: str,
) -> Dict[str, object]:
    records = remediation_registry.setdefault("records", [])
    remediation_id = f"REM-{len(records) + 1:05d}"
    row = {
        "remediation_id": remediation_id,
        "alert_id": alert_id,
        "component_id": component_id,
        "failure_type": failure_type,
        "action": action,
        "remediation_class": remediation_class,
        "started_at": _now_iso(),
        "completed_at": _now_iso(),
        "status": status,
        "evidence_before": evidence_before,
        "evidence_after": evidence_after,
        "verification_result": verification_result,
        "rollback_result": rollback_result,
        "retry_count": retry_count,
        "owner_gate": owner_gate,
        "next_action": next_action,
    }
    records.append(row)
    return row


def _readiness_layers() -> Dict[str, str]:
    payload = _read_json(READINESS_PATH)
    layers = payload.get("layers") if isinstance(payload.get("layers"), list) else []
    out: Dict[str, str] = {}
    for row in layers:
        if not isinstance(row, dict):
            continue
        layer_id = str(row.get("id") or "").strip()
        status = str(row.get("status") or "UNKNOWN").strip().upper()
        if layer_id:
            out[layer_id] = status
    return out


def _layer_passed(status: str) -> bool:
    return status == "PASS"


def _dependency_gate_map() -> Dict[str, List[str]]:
    return {
        "SOURCE_INTELLIGENCE": ["Layer 0"],
        "DATA_ACQUISITION": ["Layer 1"],
        "MARKET_BUILDER": ["Layer 1", "Layer 2"],
        "CANONICAL_UNIVERSE": ["Layer 2", "Layer 3"],
        "PROVIDER_INTELLIGENCE": ["Layer 3", "Layer 5"],
        "MEDIA_INTELLIGENCE": ["Layer 3", "Layer 5", "Layer 6"],
        "DECISION_ENGINE": ["Layer 4", "Layer 7", "Layer 8"],
        "EXPERIENCE_LAYER": ["Layer 8", "Layer 9"],
    }


def dependency_gate_decision(task_domain: str, market: str = "") -> Dict[str, object]:
    layers = _readiness_layers()
    required_layers = _dependency_gate_map().get(task_domain, [])
    unmet = [layer for layer in required_layers if not _layer_passed(layers.get(layer, "UNKNOWN"))]

    # Nevada control case guard: media work stays blocked while canonical/media pilot gate is not pass.
    if market.lower() in {"las-vegas", "nevada", "nv"} and task_domain == "MEDIA_INTELLIGENCE":
        nevada_report = _read_json(REPO_ROOT / "reports" / "NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.json")
        gate = ((nevada_report.get("media_pilot_gate") or {}).get("status") if isinstance(nevada_report, dict) else None) or "UNKNOWN"
        if str(gate).upper() != "PASS":
            unmet.append("NEVADA_MEDIA_PILOT_GATE")

    return {
        "allowed": len(unmet) == 0,
        "required_layers": required_layers,
        "unmet_prerequisites": unmet,
        "lowest_incomplete_prerequisite": unmet[0] if unmet else None,
        "failure_type": "DEPENDENCY_GATE_VIOLATION" if unmet else None,
    }


def _job_heartbeat_status(job: AgentJobRun) -> str:
    status = str(job.status or "").upper()
    if status == "RUNNING":
        return HEARTBEAT_RUN_STARTED
    if status == "SUCCESS":
        return HEARTBEAT_RUN_COMPLETED
    if status == "FAILED":
        return HEARTBEAT_RUN_FAILED
    if status == "CANCELLED":
        return HEARTBEAT_RUN_CANCELLED
    if status == "TIMEOUT":
        return HEARTBEAT_RUN_TIMED_OUT
    return HEARTBEAT_RUN_HEARTBEAT


def _agent_operational_status(schedule: str, has_runtime_evidence: bool, has_recent_run: bool) -> str:
    schedule_u = str(schedule or "").upper()
    if schedule_u in {"DISABLED"}:
        return STATUS_DISABLED
    if schedule_u in {"RETIRED"}:
        return STATUS_RETIRED
    if has_runtime_evidence and has_recent_run:
        return STATUS_ACTIVE_AGENT
    if has_runtime_evidence and not has_recent_run:
        return STATUS_IMPLEMENTED_NOT_SCHEDULED
    if schedule_u in {"CONFIGURED_NOT_RUNNING", "MANUAL_ONLY", "NOT_CONFIGURED"}:
        return STATUS_CONFIGURED_NOT_RUNNING
    if not has_runtime_evidence:
        return STATUS_SPECIFICATION_ONLY
    return STATUS_UNKNOWN


def operational_agent_registry(db: Session, market: str = "") -> List[Dict[str, object]]:
    from app.services.executive_report_service import _known_agent_catalog  # local import to avoid heavy import cycles

    now = _now()
    recent_window = now - timedelta(hours=24)
    snapshots = {row.agent_key: row for row in db.query(AgentKnowledgeReportSnapshot).all()}
    catalog = _known_agent_catalog()

    out: List[Dict[str, object]] = []
    for agent in catalog:
        agent_key = str(agent.get("agent_key") or "")
        schedule = str(agent.get("schedule") or "UNKNOWN")
        jobs = (
            db.query(AgentJobRun)
            .filter(AgentJobRun.agent_key == agent_key)
            .order_by(AgentJobRun.started_at.desc())
            .limit(50)
            .all()
        )
        refreshes = (
            db.query(AgentKnowledgeRefreshEvent)
            .filter(AgentKnowledgeRefreshEvent.agent_key == agent_key)
            .order_by(AgentKnowledgeRefreshEvent.started_at.desc())
            .limit(50)
            .all()
        )
        snapshot = snapshots.get(agent_key)
        latest_job = jobs[0] if jobs else None
        last_started = latest_job.started_at.isoformat() if latest_job and latest_job.started_at else None
        last_completed = latest_job.finished_at.isoformat() if latest_job and latest_job.finished_at else None
        success_jobs = [row for row in jobs if str(row.status or "").upper() == "SUCCESS"]
        failed_jobs = [row for row in jobs if str(row.status or "").upper() == "FAILED"]
        last_success = success_jobs[0].finished_at.isoformat() if success_jobs and success_jobs[0].finished_at else None
        last_failure = failed_jobs[0].finished_at.isoformat() if failed_jobs and failed_jobs[0].finished_at else None

        running_job = next((row for row in jobs if str(row.status or "").upper() == "RUNNING"), None)
        current_run_id = running_job.id if running_job else None

        has_runtime_evidence = bool(snapshot or jobs or refreshes)
        has_recent_run = any((_coerce_utc(row.started_at) and _coerce_utc(row.started_at) >= recent_window) for row in jobs)
        status = _agent_operational_status(schedule=schedule, has_runtime_evidence=has_runtime_evidence, has_recent_run=has_recent_run)

        heartbeat_at_dt = _coerce_utc(running_job.started_at) if running_job and running_job.started_at else (_coerce_utc(latest_job.finished_at) if latest_job and latest_job.finished_at else None)
        heartbeat_at = heartbeat_at_dt.isoformat() if heartbeat_at_dt else None
        if running_job and running_job.started_at and (now - _coerce_utc(running_job.started_at)) > timedelta(hours=2):
            heartbeat_status = "STUCK"
        elif running_job:
            heartbeat_status = "RUNNING"
        elif has_recent_run:
            heartbeat_status = "ALIVE"
        elif has_runtime_evidence:
            heartbeat_status = "INACTIVE"
        else:
            heartbeat_status = "UNKNOWN"

        latest_knowledge = (
            db.query(AgentKnowledgeRecord)
            .filter(AgentKnowledgeRecord.agent_key == agent_key)
            .order_by(AgentKnowledgeRecord.created_at.desc())
            .limit(5)
            .all()
        )
        actual_outputs = [
            {
                "record_type": row.record_type,
                "entity_key": row.entity_key,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in latest_knowledge
        ]

        uses = (
            db.query(RecommendationKnowledgeUsageLog)
            .filter(RecommendationKnowledgeUsageLog.agent_key == agent_key)
            .order_by(RecommendationKnowledgeUsageLog.logged_at.desc())
            .limit(5)
            .all()
        )
        consumers = [
            {
                "recommendation_key": row.recommendation_key,
                "consumed_at": row.logged_at.isoformat() if row.logged_at else None,
                "decision": row.decision,
            }
            for row in uses
        ]

        out.append(
            {
                "agent_key": agent_key,
                "agent_name": str(agent.get("agent_name") or "UNKNOWN"),
                "implementation_entry_point": str(agent.get("entry_point") or "UNKNOWN"),
                "operational_status": status,
                "schedule": schedule,
                "last_started_at": last_started,
                "last_completed_at": last_completed,
                "last_success_at": last_success,
                "last_failure_at": last_failure,
                "current_run_id": current_run_id,
                "assigned_task": "UNKNOWN",
                "market": market or "UNKNOWN",
                "expected_inputs": list(agent.get("dependencies") or []),
                "expected_outputs": list(agent.get("expected_outputs") or []),
                "actual_outputs": actual_outputs,
                "output_consumers": consumers,
                "heartbeat_at": heartbeat_at,
                "heartbeat_status": heartbeat_status,
                "retry_count": int(snapshot.failed_refresh_count if snapshot else 0),
                "health_status": str(snapshot.health_status if snapshot else "UNKNOWN"),
            }
        )

    return out


def task_output_consumer_trace(db: Session, limit: int = 200) -> List[Dict[str, object]]:
    jobs = db.query(AgentJobRun).order_by(AgentJobRun.started_at.desc()).limit(max(1, min(limit, 1000))).all()
    out: List[Dict[str, object]] = []
    for row in jobs:
        status = str(row.status or "").upper()
        if status == "RUNNING":
            terminal = TRACE_RUNNING
        elif status == "FAILED":
            terminal = TRACE_FAILED
        elif status == "SUCCESS":
            terminal = TRACE_VALIDATED
        elif status == "CANCELLED":
            terminal = TRACE_BLOCKED
        else:
            terminal = TRACE_COMPLETED_UNVALIDATED

        knowledge_records = (
            db.query(AgentKnowledgeRecord)
            .filter(AgentKnowledgeRecord.agent_key == row.agent_key)
            .order_by(AgentKnowledgeRecord.created_at.desc())
            .limit(5)
            .all()
        )
        output_artifacts = [
            {
                "record_type": item.record_type,
                "entity_key": item.entity_key,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in knowledge_records
        ]

        consumers = (
            db.query(RecommendationKnowledgeUsageLog)
            .filter(RecommendationKnowledgeUsageLog.agent_key == row.agent_key)
            .order_by(RecommendationKnowledgeUsageLog.logged_at.desc())
            .limit(5)
            .all()
        )
        actual_consumers = [
            {
                "recommendation_key": item.recommendation_key,
                "consumed_at": item.logged_at.isoformat() if item.logged_at else None,
                "decision": item.decision,
            }
            for item in consumers
        ]

        if terminal == TRACE_VALIDATED and output_artifacts and actual_consumers:
            contribution_status = TRACE_CONSUMED
        elif terminal == TRACE_VALIDATED and output_artifacts:
            contribution_status = TRACE_STORED
        elif terminal == TRACE_VALIDATED and not output_artifacts:
            contribution_status = TRACE_COMPLETED_UNVALIDATED
        else:
            contribution_status = terminal

        out.append(
            {
                "task_id": f"JOB-{row.id}",
                "agent_key": row.agent_key,
                "objective": "Agent job execution",
                "input_artifacts": ["backend/optime_nursing.db:agent_job_runs"],
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.finished_at.isoformat() if row.finished_at else None,
                "output_artifacts": output_artifacts,
                "validation_status": "PASS" if terminal == TRACE_VALIDATED else "FAIL" if terminal == TRACE_FAILED else "UNKNOWN",
                "stored_in": "backend/optime_nursing.db:agent_knowledge_records" if output_artifacts else "UNKNOWN",
                "expected_consumers": ["recommendation_engine", "reporting"],
                "actual_consumers": actual_consumers,
                "consumed_at": actual_consumers[0]["consumed_at"] if actual_consumers else None,
                "contribution_status": contribution_status,
                "terminal_status": terminal,
            }
        )
    return out


def classify_unconsumed_output(row: Dict[str, object]) -> str:
    status = str(row.get("terminal_status") or "")
    outputs = list(row.get("output_artifacts") or [])
    consumers = list(row.get("actual_consumers") or [])
    completed_at = str(row.get("completed_at") or "")
    if status in {TRACE_FAILED, TRACE_BLOCKED}:
        return OUTPUT_NEEDS_REVIEW
    if not outputs:
        return OUTPUT_IRRELEVANT
    if outputs and not consumers and completed_at:
        try:
            completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        except ValueError:
            completed_dt = None
        if completed_dt and (_now() - _coerce_utc(completed_dt)) >= timedelta(hours=24):
            return OUTPUT_ORPHANED
    if outputs and not consumers:
        return OUTPUT_REUSABLE_KNOWLEDGE
    return OUTPUT_REUSABLE_KNOWLEDGE


def review_task_output_quality(row: Dict[str, object], active_market: str) -> Dict[str, object]:
    output_artifacts = list(row.get("output_artifacts") or [])
    terminal_status = str(row.get("terminal_status") or "")
    validation_status = str(row.get("validation_status") or "UNKNOWN").upper()
    issues: List[str] = []

    if terminal_status in {TRACE_FAILED, TRACE_BLOCKED}:
        return {"decision": QUALITY_REJECT, "issues": ["task_terminal_failure"], "market_match": False}
    if terminal_status in {TRACE_VALIDATED, TRACE_STORED, TRACE_CONSUMED} and not output_artifacts:
        return {"decision": QUALITY_RETURN, "issues": ["missing_expected_output"], "market_match": False}
    if validation_status == "FAIL":
        return {"decision": QUALITY_REJECT, "issues": ["schema_or_validation_failed"], "market_match": False}

    market_match = True
    if active_market in {"nevada", "las-vegas"}:
        for artifact in output_artifacts:
            entity = str((artifact or {}).get("entity_key") or "").lower()
            if entity.startswith("fl-") or "florida" in entity:
                market_match = False
                issues.append("wrong_market_output")
                break

    if not market_match:
        return {"decision": QUALITY_REJECT, "issues": issues, "market_match": False}
    if not output_artifacts:
        return {"decision": QUALITY_ACCEPT_WARNING, "issues": ["completed_with_no_output"], "market_match": True}
    if terminal_status == TRACE_COMPLETED_UNVALIDATED:
        return {"decision": QUALITY_RETURN, "issues": ["completed_without_validation"], "market_match": True}
    return {"decision": QUALITY_ACCEPT, "issues": issues, "market_match": True}


def compute_agent_performance_metrics(registry: List[Dict[str, object]], traces: List[Dict[str, object]], active_objective: str) -> List[Dict[str, object]]:
    traces_by_agent: Dict[str, List[Dict[str, object]]] = {}
    for row in traces:
        traces_by_agent.setdefault(str(row.get("agent_key") or "UNKNOWN"), []).append(row)

    out: List[Dict[str, object]] = []
    for agent in registry:
        key = str(agent.get("agent_key") or "UNKNOWN")
        items = traces_by_agent.get(key, [])
        assigned = len(items)
        completed = sum(1 for row in items if str(row.get("terminal_status") or "") in {TRACE_VALIDATED, TRACE_STORED, TRACE_CONSUMED})
        validated = sum(1 for row in items if str(row.get("validation_status") or "").upper() == "PASS")
        consumed = sum(1 for row in items if str(row.get("contribution_status") or "") == TRACE_CONSUMED)
        correction_rate = (sum(1 for row in items if str(row.get("terminal_status") or "") == TRACE_COMPLETED_UNVALIDATED) / assigned) if assigned else 0.0
        failure_rate = (sum(1 for row in items if str(row.get("terminal_status") or "") == TRACE_FAILED) / assigned) if assigned else 0.0
        durations: List[float] = []
        for row in items:
            started = str(row.get("started_at") or "")
            completed_at = str(row.get("completed_at") or "")
            try:
                s_dt = datetime.fromisoformat(started.replace("Z", "+00:00")) if started else None
                c_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00")) if completed_at else None
            except ValueError:
                s_dt = None
                c_dt = None
            if s_dt and c_dt and c_dt >= s_dt:
                durations.append((c_dt - s_dt).total_seconds())

        out.append(
            {
                "agent_key": key,
                "agent_name": agent.get("agent_name"),
                "assigned_tasks": assigned,
                "completed_tasks": completed,
                "validated_outputs": validated,
                "consumed_outputs": consumed,
                "correction_rate": round(correction_rate, 4),
                "failure_rate": round(failure_rate, 4),
                "retry_rate": float(agent.get("retry_count") or 0),
                "average_duration_seconds": round((sum(durations) / len(durations)) if durations else 0.0, 3),
                "output_reuse_count": sum(1 for row in items if classify_unconsumed_output(row) == OUTPUT_REUSABLE_KNOWLEDGE),
                "orphaned_output_count": sum(1 for row in items if classify_unconsumed_output(row) == OUTPUT_ORPHANED),
                "contribution_to_active_objective": "HIGH" if completed > 0 else "LOW",
                "active_objective": active_objective,
            }
        )
    return out


def supervisor_self_health_status() -> Dict[str, object]:
    state = _load_recovery_state()
    heartbeat = state.get("supervisor_heartbeat") if isinstance(state.get("supervisor_heartbeat"), dict) else {}
    latest_report = state.get("latest_generated_report") if isinstance(state.get("latest_generated_report"), dict) else {}
    latest_email = state.get("latest_email_delivery") if isinstance(state.get("latest_email_delivery"), dict) else {}

    last_cycle_completion_raw = str(heartbeat.get("last_cycle_completion") or "")
    stale = True
    if last_cycle_completion_raw:
        try:
            last_cycle_completion = datetime.fromisoformat(last_cycle_completion_raw.replace("Z", "+00:00"))
            stale = (_now() - last_cycle_completion) > timedelta(hours=2)
        except ValueError:
            stale = True

    return {
        "supervisor_heartbeat": heartbeat,
        "latest_generated_report": latest_report,
        "latest_email_delivery": latest_email,
        "health": "DEGRADED" if stale else "HEALTHY",
        "stale_or_missed_cycle": stale,
    }


def evaluate_platform_registry_work_request(
    capability_id: str,
    db: Optional[Session] = None,
    agent_key: Optional[str] = None,
    domain: Optional[str] = None,
    *,
    require_evidence: bool = False,
    requested_output: Optional[str] = None,
) -> Dict[str, object]:
    decision = evaluate_capability_assignment(
        capability_id,
        load_platform_registry().get("capabilities") or [],
        require_evidence=require_evidence,
        requested_output=requested_output,
    )
    if db is not None and not decision.get("allowed"):
        _create_incident(
            db,
            incident_type="REGISTRY_ASSIGNMENT_REJECTED",
            severity="HIGH",
            summary=f"Registry rejected work request for {capability_id}: {decision.get('reason')}",
            agent_key=agent_key,
            domain=domain or "operations_supervisor",
            details={
                "capability_id": capability_id,
                "decision": decision,
            },
        )
    return decision


def run_independent_supervisor_watchdog(db: Session, max_allowed_lateness_seconds: int = 180) -> Dict[str, object]:
    state = _load_recovery_state()
    scheduler = state.get("scheduler") if isinstance(state.get("scheduler"), dict) else {}
    heartbeat = state.get("supervisor_heartbeat") if isinstance(state.get("supervisor_heartbeat"), dict) else {}
    latest_report = state.get("latest_generated_report") if isinstance(state.get("latest_generated_report"), dict) else {}

    heartbeat_interval = int(scheduler.get("heartbeat_interval_seconds") or 300)
    last_cycle_completion_raw = str(heartbeat.get("last_cycle_completion") or "")
    last_cycle_start_raw = str(heartbeat.get("last_cycle_start") or "")

    last_cycle_completion = None
    last_cycle_start = None
    if last_cycle_completion_raw:
        try:
            last_cycle_completion = datetime.fromisoformat(last_cycle_completion_raw.replace("Z", "+00:00"))
        except ValueError:
            last_cycle_completion = None
    if last_cycle_start_raw:
        try:
            last_cycle_start = datetime.fromisoformat(last_cycle_start_raw.replace("Z", "+00:00"))
        except ValueError:
            last_cycle_start = None

    now = _now()
    reference = _coerce_utc(last_cycle_completion) or _coerce_utc(last_cycle_start)
    expected_next_cycle = (reference + timedelta(seconds=heartbeat_interval)) if reference else None
    max_lateness = max(60, int(max_allowed_lateness_seconds))
    missed = bool(expected_next_cycle and now > (expected_next_cycle + timedelta(seconds=max_lateness)))

    report_deadline_missed = False
    report_path = str(latest_report.get("path_md") or "")
    if report_path:
        p = REPO_ROOT / report_path
        report_deadline_missed = not p.exists()

    stale_self_declared_healthy = str(heartbeat.get("status") or "").upper() == "HEALTHY" and missed

    created_incident_id = None
    if missed:
        _create_incident(
            db,
            incident_type=WATCHDOG_INCIDENT_MISSED_CYCLE,
            severity="CRITICAL",
            summary="Independent watchdog detected missed supervisor cycle.",
            domain="operations_supervisor_watchdog",
            details={
                "last_cycle_start": last_cycle_start_raw,
                "last_cycle_completion": last_cycle_completion_raw,
                "expected_next_cycle": expected_next_cycle.isoformat() if expected_next_cycle else None,
                "max_allowed_lateness_seconds": max_lateness,
                "scheduler_running_flag": bool(scheduler.get("running")),
                "stale_self_declared_healthy": stale_self_declared_healthy,
                "report_deadline_missed": report_deadline_missed,
            },
        )
        db.flush()
        newest = db.query(SupervisorIncidentLog).order_by(SupervisorIncidentLog.id.desc()).first()
        created_incident_id = newest.id if newest else None
        db.commit()

    return {
        "watchdog": "INDEPENDENT",
        "detected_missed_cycle": missed,
        "incident_created": bool(created_incident_id),
        "incident_id": created_incident_id,
        "last_cycle_start": last_cycle_start_raw,
        "last_cycle_completion": last_cycle_completion_raw,
        "expected_next_cycle": expected_next_cycle.isoformat() if expected_next_cycle else None,
        "max_allowed_lateness_seconds": max_lateness,
        "scheduler_running_flag": bool(scheduler.get("running")),
        "stale_self_declared_healthy": stale_self_declared_healthy,
        "report_deadline_missed": report_deadline_missed,
    }


def _build_daily_owner_payload(db: Session, mode: str, active_market: str) -> Dict[str, object]:
    resolved_market = _resolve_active_market(active_market)
    registry = operational_agent_registry(db, market=resolved_market)
    traces = task_output_consumer_trace(db, limit=200)
    quality_reviews = [
        {"task_id": row.get("task_id"), **review_task_output_quality(row, resolved_market)}
        for row in traces
    ]
    source_contract = validate_source_registry(load_registry())
    source_snapshot = source_contract["snapshot"]
    incidents = recent_incidents(db, limit=300)
    open_incidents = [row for row in incidents if str(row.get("status") or "").upper() == "OPEN"]
    p0 = [row for row in open_incidents if str(row.get("severity") or "").upper() == "CRITICAL"]
    p1 = [row for row in open_incidents if str(row.get("severity") or "").upper() == "HIGH"]

    expected_agents = [row for row in registry if row["operational_status"] in {STATUS_ACTIVE_AGENT, STATUS_IMPLEMENTED_NOT_SCHEDULED, STATUS_CONFIGURED_NOT_RUNNING}]
    ran_agents = [row for row in registry if row["heartbeat_status"] in {"ALIVE", "RUNNING"}]
    overdue = [row for row in registry if row["heartbeat_status"] in {"INACTIVE", "STUCK"}]
    failed = [row for row in registry if row["heartbeat_status"] == "UNKNOWN" or row["operational_status"] == STATUS_UNKNOWN]

    outputs_produced = [row for row in traces if row.get("output_artifacts")]
    outputs_validated = [row for row in traces if row.get("validation_status") == "PASS"]
    outputs_consumed = [row for row in traces if row.get("contribution_status") == TRACE_CONSUMED]
    reusable = [row for row in traces if classify_unconsumed_output(row) in {OUTPUT_REUSABLE_KNOWLEDGE, OUTPUT_FUTURE_MARKET_KNOWLEDGE}]
    orphaned = [row for row in traces if classify_unconsumed_output(row) == OUTPUT_ORPHANED]
    performance_metrics = compute_agent_performance_metrics(
        registry,
        traces,
        active_objective="Stabilize prerequisite layers and governed source integration before downstream expansion",
    )

    rem_registry = _load_remediation_registry()
    recent_remediations = []
    now = _now()
    for row in rem_registry.get("records", []):
        completed = str(row.get("completed_at") or "")
        try:
            completed_dt = _coerce_utc(datetime.fromisoformat(completed.replace("Z", "+00:00")))
        except ValueError:
            continue
        if completed_dt >= now - timedelta(hours=24):
            recent_remediations.append(row)
    rem_success = [row for row in recent_remediations if str(row.get("status") or "").upper() == "SUCCESS"]
    rem_failed = [row for row in recent_remediations if str(row.get("status") or "").upper() == "FAILED"]

    blocked_layers = [layer for layer, status in _readiness_layers().items() if not _layer_passed(status)]

    overall_status = "HEALTHY"
    if source_snapshot.get("launch_blockers") or blocked_layers:
        overall_status = "BLOCKED"
    if overdue or failed:
        overall_status = "DEGRADED"

    return {
        "generated_at_utc": _now_iso(),
        "mode": mode,
        "overall_operational_status": overall_status,
        "active_objective": "Stabilize prerequisite layers and governed source integration before downstream expansion",
        "objective_progress": {
            "launch_blockers": len(source_snapshot.get("launch_blockers") or []),
            "blocked_layers": len(blocked_layers),
            "integrated_sources": int((source_snapshot.get("status_distribution") or {}).get("INTEGRATED", 0)),
        },
        "agents_expected_to_run": expected_agents,
        "agents_that_actually_ran": ran_agents,
        "agents_overdue_stuck_failed": overdue + failed,
        "outputs_produced": outputs_produced,
        "outputs_validated": outputs_validated,
        "outputs_consumed": outputs_consumed,
        "outputs_reusable_knowledge": reusable,
        "orphaned_outputs": orphaned,
        "output_quality_reviews": quality_reviews,
        "corrections_performed_automatically": rem_success,
        "corrections_failed": rem_failed,
        "agent_performance": performance_metrics,
        "blocked_markets_layers": {
            "market_readiness": source_snapshot.get("market_readiness") or {},
            "blocked_layers": blocked_layers,
            "source_launch_blockers": source_snapshot.get("launch_blockers") or [],
        },
        "owner_decisions_required": [row for row in open_incidents if str(row.get("severity") or "").upper() in {"CRITICAL", "HIGH"}],
        "p0_alerts": p0,
        "p1_alerts": p1,
        "next_single_engineering_objective": str((_read_json(READINESS_PATH).get("executive_summary") or {}).get("next_single_engineering_objective") or "UNKNOWN"),
        "supervisor_self_health": supervisor_self_health_status(),
        "active_market": resolved_market,
    }


def _daily_owner_markdown(payload: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Daily System Health")
    lines.append("")
    lines.append(f"Generated: `{payload['generated_at_utc']}`")
    lines.append(f"Mode: **{payload['mode']}**")
    lines.append("")
    lines.append(f"- Overall operational status: **{payload['overall_operational_status']}**")
    lines.append(f"- Active objective: **{payload['active_objective']}**")
    progress = payload.get("objective_progress") or {}
    lines.append(f"- Objective progress: launch_blockers={progress.get('launch_blockers')} blocked_layers={progress.get('blocked_layers')} integrated_sources={progress.get('integrated_sources')}")
    lines.append("")
    lines.append(f"- Agents expected to run: **{len(payload.get('agents_expected_to_run') or [])}**")
    lines.append(f"- Agents that actually ran: **{len(payload.get('agents_that_actually_ran') or [])}**")
    lines.append(f"- Agents overdue/stuck/failed: **{len(payload.get('agents_overdue_stuck_failed') or [])}**")
    lines.append(f"- Outputs produced: **{len(payload.get('outputs_produced') or [])}**")
    lines.append(f"- Outputs validated: **{len(payload.get('outputs_validated') or [])}**")
    lines.append(f"- Outputs consumed: **{len(payload.get('outputs_consumed') or [])}**")
    lines.append(f"- Outputs reusable knowledge: **{len(payload.get('outputs_reusable_knowledge') or [])}**")
    lines.append(f"- Orphaned outputs: **{len(payload.get('orphaned_outputs') or [])}**")
    lines.append(f"- Corrections performed automatically: **{len(payload.get('corrections_performed_automatically') or [])}**")
    lines.append(f"- Corrections failed: **{len(payload.get('corrections_failed') or [])}**")
    lines.append(f"- Owner decisions required: **{len(payload.get('owner_decisions_required') or [])}**")
    lines.append(f"- Next single engineering objective: **{payload.get('next_single_engineering_objective', 'UNKNOWN')}**")
    lines.append("")
    lines.append("## Alerts")
    lines.append("")
    lines.append(f"- P0 alerts: **{len(payload.get('p0_alerts') or [])}**")
    lines.append(f"- P1 alerts: **{len(payload.get('p1_alerts') or [])}**")
    lines.append("")
    lines.append("## Blocked Markets/Layers")
    lines.append("")
    blocked = payload.get("blocked_markets_layers") or {}
    for market, readiness in (blocked.get("market_readiness") or {}).items():
        lines.append(f"- {market}: launch_ready={readiness.get('launch_ready')} blockers={readiness.get('launch_blocker_count')}")
    for layer in blocked.get("blocked_layers") or []:
        lines.append(f"- blocked_layer: {layer}")
    return "\n".join(lines) + "\n"


def generate_daily_owner_operations_brief(db: Session, mode: Optional[str] = None, active_market: str = "") -> Dict[str, object]:
    selected_mode = mode or _mode()
    payload = _build_daily_owner_payload(db, selected_mode, active_market=active_market)
    markdown = _daily_owner_markdown(payload)

    DAILY_HEALTH_MD.write_text(markdown, encoding="utf-8")
    DAILY_HEALTH_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    today = datetime.now(timezone.utc).date().isoformat()
    subject = f"OPTIME Daily Operations Brief — {today}"
    record = create_report_artifacts(subject=subject, markdown_text=markdown, report_json=payload)

    send_result = send_email_detailed(
        subject=subject,
        body_text=markdown,
        recipients=configured_recipients(),
        attachments=[str(DAILY_HEALTH_MD), str(DAILY_HEALTH_JSON)],
        max_retries=1,
    )

    delivery_confirmed = bool(send_result.ok and send_result.status == "DELIVERY_ACCEPTED" and "SMTP_ACCEPTED=True" in send_result.provider_response)

    rem_registry = _load_remediation_registry()
    if delivery_confirmed:
        mark_report_sent(record.report_id, send_result.recipients)
        _append_remediation_record(
            rem_registry,
            alert_id=f"daily-owner-email-{today}",
            component_id="daily_owner_email",
            failure_type="EMAIL_DELIVERY_OK",
            action="RETRY_WITH_BACKOFF",
            remediation_class="CLASS_A",
            status="SUCCESS",
            evidence_before={"subject": subject},
            evidence_after={"provider_response": send_result.provider_response},
            verification_result="DELIVERY_CONFIRMED",
            rollback_result="NO_OP",
            retry_count=int(send_result.retry_count),
            owner_gate=False,
            next_action="Send next daily report",
        )
    else:
        _append_remediation_record(
            rem_registry,
            alert_id="P1-EMAIL-DELIVERY",
            component_id="daily_owner_email",
            failure_type="TRANSIENT_NETWORK_FAILURE",
            action="RETRY_WITH_BACKOFF",
            remediation_class="CLASS_A",
            status="FAILED",
            evidence_before={"subject": subject, "message": send_result.message},
            evidence_after={"provider_response": send_result.provider_response},
            verification_result="DELIVERY_NOT_CONFIRMED",
            rollback_result="NO_OP",
            retry_count=int(send_result.retry_count),
            owner_gate=False,
            next_action="Retry according to bounded policy; use approved fallback when configured",
        )
        _create_incident(
            db,
            incident_type="DAILY_OWNER_EMAIL_FAILED",
            severity="HIGH",
            summary="Daily owner email delivery failed and is unconfirmed.",
            domain="operations_supervisor",
            details={
                "priority": "P1",
                "subject": subject,
                "provider_response": send_result.provider_response,
                "retry_count": send_result.retry_count,
            },
        )
        db.commit()

    _save_remediation_registry(rem_registry)

    recovery = _load_recovery_state()
    recovery["mode"] = selected_mode
    recovery["latest_generated_report"] = {
        "report_id": record.report_id,
        "subject": subject,
        "generated_at_utc": _now_iso(),
        "path_md": str(DAILY_HEALTH_MD.relative_to(REPO_ROOT)).replace("\\", "/"),
        "path_json": str(DAILY_HEALTH_JSON.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    recovery["latest_email_delivery"] = {
        "status": send_result.status,
        "delivery_confirmed": delivery_confirmed,
        "message": send_result.message,
        "provider_response": send_result.provider_response,
        "attempted_at_utc": send_result.attempted_at_utc,
        "recipients": send_result.recipients,
    }
    if delivery_confirmed:
        recovery["last_successful_end_to_end_recovery"] = _now_iso()
    _save_recovery_state(recovery)

    return {
        "delivery_confirmed": delivery_confirmed,
        "delivery_status": send_result.status,
        "delivery_message": send_result.message,
        "report_id": record.report_id,
        "mode": selected_mode,
        "recipients": send_result.recipients,
    }


def run_active_operations_supervisor_cycle(db: Session, mode: Optional[str] = None, active_market: str = "") -> Dict[str, object]:
    selected_mode = mode or _mode()
    resolved_market = _resolve_active_market(active_market)
    start = _now()
    registry_payload = load_platform_registry()
    registry_audit = run_platform_registry_self_audit(registry_payload)
    registry_payload["self_audit"] = registry_audit
    current_assignment_decision = registry_payload.get("assignment_decision") if isinstance(registry_payload.get("assignment_decision"), dict) else {}
    recovery = _load_recovery_state()
    recovery["supervisor_heartbeat"] = {
        "last_cycle_start": _now_iso(),
        "status": "DEGRADED" if registry_audit.get("has_p0_findings") else "RUNNING",
    }
    _save_recovery_state(recovery)

    if registry_audit.get("has_p0_findings"):
        _create_incident(
            db,
            incident_type="REGISTRY_AUDIT_FAILED",
            severity="CRITICAL",
            summary="Registry self-audit found P0 integrity findings before supervisor assignment work.",
            domain="operations_supervisor",
            details=registry_audit,
        )
    if current_assignment_decision and not current_assignment_decision.get("allowed"):
        _create_incident(
            db,
            incident_type="REGISTRY_CURRENT_ASSIGNMENT_BLOCKED",
            severity="HIGH",
            summary=f"Current executable capability is blocked by registry gate: {current_assignment_decision.get('reason')}",
            domain="operations_supervisor",
            details=current_assignment_decision,
        )

    registry_proof = {
        "observed_at": _now_iso(),
        "execution_type": "LIVE_EXECUTION",
        "registry_trust_verdict": registry_payload.get("registry_trust_verdict"),
        "audit_finding_count": registry_audit.get("finding_count"),
        "audit_has_p0": registry_audit.get("has_p0_findings"),
        "current_active_objective": (registry_payload.get("summary") or {}).get("current_active_objective"),
        "current_executable_capability": (registry_payload.get("summary") or {}).get("current_executable_capability"),
        "assignment_decision": current_assignment_decision,
        "claim_status_summary": registry_payload.get("claim_status_summary") or {},
        "registry_checksum": hashlib.sha1(json.dumps(registry_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
    }

    base = run_supervisor_cycle(db)
    registry = operational_agent_registry(db, market=resolved_market)
    traces = task_output_consumer_trace(db, limit=200)
    quality_reviews = [
        {"task_id": row.get("task_id"), **review_task_output_quality(row, resolved_market)}
        for row in traces
    ]

    # Detect heartbeat failures and stuck runs.
    stuck_agents = [row for row in registry if row.get("heartbeat_status") == "STUCK"]
    overdue_agents = [row for row in registry if row.get("heartbeat_status") in {"INACTIVE", "UNKNOWN"} and row.get("operational_status") in {STATUS_ACTIVE_AGENT, STATUS_IMPLEMENTED_NOT_SCHEDULED}]
    for row in stuck_agents:
        _create_incident(
            db,
            incident_type="AGENT_STUCK",
            severity="HIGH",
            summary=f"Agent {row.get('agent_key')} appears stuck in RUNNING state.",
            agent_key=str(row.get("agent_key") or None),
            domain="operations_supervisor",
            details={"current_run_id": row.get("current_run_id"), "heartbeat_at": row.get("heartbeat_at")},
        )
    for row in overdue_agents:
        _create_incident(
            db,
            incident_type="SCHEDULED_AGENT_OVERDUE",
            severity="HIGH",
            summary=f"Scheduled agent {row.get('agent_key')} is overdue/inactive.",
            agent_key=str(row.get("agent_key") or None),
            domain="operations_supervisor",
            details={"schedule": row.get("schedule"), "heartbeat_status": row.get("heartbeat_status")},
        )

    # Dependency gates for known downstream domains.
    dependency_checks = {
        "MEDIA_INTELLIGENCE": dependency_gate_decision("MEDIA_INTELLIGENCE", market=resolved_market),
        "EXPERIENCE_LAYER": dependency_gate_decision("EXPERIENCE_LAYER", market=resolved_market),
    }
    for domain, decision in dependency_checks.items():
        if decision.get("allowed"):
            continue
        _create_incident(
            db,
            incident_type="DEPENDENCY_GATE_VIOLATION",
            severity="HIGH",
            summary=f"{domain} blocked by unmet prerequisite: {decision.get('lowest_incomplete_prerequisite')}",
            domain="operations_supervisor",
            details=decision,
        )

    # Build remediations from incidents and dependency gate violations.
    open_incidents = recent_incidents(db, limit=400)
    remediation_registry = _load_remediation_registry()
    recovery_state = _load_recovery_state()
    retry_budgets = recovery_state.get("agent_retry_budgets") if isinstance(recovery_state.get("agent_retry_budgets"), dict) else {}

    remediation_attempts: List[Dict[str, object]] = []
    report_regenerated_during_cycle = False
    for incident in open_incidents:
        if str(incident.get("status") or "").upper() != "OPEN":
            continue
        incident_type = str(incident.get("incident_type") or "")
        agent_key = str(incident.get("agent_key") or incident_type)
        retry_count = int(retry_budgets.get(agent_key) or 0)
        failure_type = "UNKNOWN_FAILURE"
        if incident_type in {"TTL_EXPIRED", "SCHEDULED_AGENT_OVERDUE", "AGENT_STUCK"}:
            failure_type = "PIPELINE_TIMEOUT"
        elif incident_type == "DEPENDENCY_GATE_VIOLATION":
            failure_type = "DEPENDENCY_GATE_VIOLATION"
        elif incident_type == "DAILY_OWNER_EMAIL_FAILED":
            failure_type = "TRANSIENT_NETWORK_FAILURE"
        elif incident_type == "SUPERVISOR_REPORT_MISSING":
            failure_type = "REGISTRY_REPORT_MISMATCH"
        elif incident_type == "SUPERVISOR_EMAIL_UNCONFIRMED":
            failure_type = "TRANSIENT_NETWORK_FAILURE"

        component_type = "AGENT" if incident.get("agent_key") else "SUPERVISOR"
        if incident_type == "SUPERVISOR_REPORT_MISSING":
            component_type = "REPORT"

        policy = evaluate_remediation_policy(
            {
                "failure_type": failure_type,
                "component_type": component_type,
                "retry_count": retry_count,
                "retry_budget": 3,
                "dependency_impact": "DOWNSTREAM_BLOCKED" if failure_type == "DEPENDENCY_GATE_VIOLATION" else "LOCAL",
                "approved_fallback_available": False,
                "governed_machine_gate_passed": False,
            },
            mode=selected_mode,
        )

        remediation_action = str(policy.get("remediation_action") or "MARK_FAILED")
        executed = False
        status = "FAILED"
        verification_result = "NOT_EXECUTED"
        evidence_after: Dict[str, object] = {"policy": policy}
        rollback_result = "NO_OP"
        if bool(policy.get("allowed_to_execute")):
            executed = True
            status = "SUCCESS"
            verification_result = "EXECUTED"

            if remediation_action in {"RETRY", "RETRY_WITH_BACKOFF"} and incident.get("agent_key"):
                retry_result = refresh_all_agent_reports(
                    db,
                    refresh_mode="supervisor_remediation_retry",
                    agent_keys=[str(incident.get("agent_key"))],
                    force=True,
                    incremental=False,
                )
                status = "SUCCESS" if int(retry_result.get("failures") or 0) == 0 else "FAILED"
                verification_result = "VERIFIED_RECOVERED" if status == "SUCCESS" else "VERIFY_FAILED"
                evidence_after = {"policy": policy, "retry_result": retry_result}
            elif remediation_action == "REGENERATE_REPORT":
                report_result = generate_daily_owner_operations_brief(db, mode=selected_mode, active_market=resolved_market)
                report_exists = DAILY_HEALTH_MD.exists() and DAILY_HEALTH_JSON.exists()
                status = "SUCCESS" if report_exists else "FAILED"
                verification_result = "VERIFIED_RECOVERED" if status == "SUCCESS" else "VERIFY_FAILED"
                if status == "SUCCESS":
                    report_regenerated_during_cycle = True
                evidence_after = {
                    "policy": policy,
                    "report_result": report_result,
                    "report_md_exists": DAILY_HEALTH_MD.exists(),
                    "report_json_exists": DAILY_HEALTH_JSON.exists(),
                }

            if status == "SUCCESS":
                incident_row = db.query(SupervisorIncidentLog).filter(SupervisorIncidentLog.id == int(incident.get("id") or 0)).first()
                if incident_row is not None:
                    incident_row.status = "RESOLVED"

        remediation = _append_remediation_record(
            remediation_registry,
            alert_id=str(incident.get("id") or ""),
            component_id=agent_key,
            failure_type=failure_type,
            action=remediation_action,
            remediation_class=str(policy.get("remediation_class") or "CLASS_B"),
            status=status,
            evidence_before={"incident": incident},
            evidence_after=evidence_after,
            verification_result=verification_result,
            rollback_result=rollback_result,
            retry_count=retry_count,
            owner_gate=bool(str(policy.get("remediation_class") or "") == "CLASS_C"),
            next_action=str(policy.get("escalation_reason") or "Retry or escalate according to policy"),
        )
        remediation_attempts.append(remediation)
        retry_budgets[agent_key] = retry_count + 1

        # Quarantine on repeated identical failures.
        if retry_budgets[agent_key] >= 3:
            quarantined = list(recovery_state.get("quarantined_agents") or [])
            if agent_key not in quarantined:
                quarantined.append(agent_key)
            recovery_state["quarantined_agents"] = quarantined

    recovery_state["agent_retry_budgets"] = retry_budgets
    blocked_components = list(recovery_state.get("blocked_downstream_components") or [])
    for domain, decision in dependency_checks.items():
        if decision.get("allowed"):
            continue
        if domain not in blocked_components:
            blocked_components.append(domain)
    recovery_state["blocked_downstream_components"] = blocked_components

    _save_remediation_registry(remediation_registry)

    end = _now()
    recovery_state["supervisor_heartbeat"] = {
        "last_cycle_start": recovery.get("supervisor_heartbeat", {}).get("last_cycle_start") if isinstance(recovery.get("supervisor_heartbeat"), dict) else _now_iso(),
        "last_cycle_completion": _now_iso(),
        "last_successful_cycle": _now_iso(),
        "cycle_duration_ms": int((end - start).total_seconds() * 1000),
        "cycle_failures": len([row for row in remediation_attempts if str(row.get("status") or "").upper() == "FAILED"]),
        "status": "DEGRADED" if registry_audit.get("has_p0_findings") else "HEALTHY",
    }
    recovery_state["latest_registry_runtime_proof"] = registry_proof

    if report_regenerated_during_cycle:
        latest_state = _load_recovery_state()
        if isinstance(latest_state.get("latest_generated_report"), dict):
            recovery_state["latest_generated_report"] = latest_state.get("latest_generated_report")
        if isinstance(latest_state.get("latest_email_delivery"), dict):
            recovery_state["latest_email_delivery"] = latest_state.get("latest_email_delivery")

    latest_report = recovery_state.get("latest_generated_report") if isinstance(recovery_state.get("latest_generated_report"), dict) else {}
    latest_email = recovery_state.get("latest_email_delivery") if isinstance(recovery_state.get("latest_email_delivery"), dict) else {}
    if not latest_report:
        _create_incident(
            db,
            incident_type="SUPERVISOR_REPORT_MISSING",
            severity="HIGH",
            summary="Supervisor did not record a latest generated daily report.",
            domain="operations_supervisor",
            details={"required_report": str(DAILY_HEALTH_MD.relative_to(REPO_ROOT)).replace("\\", "/")},
        )
    if latest_email and not bool(latest_email.get("delivery_confirmed")):
        _create_incident(
            db,
            incident_type="SUPERVISOR_EMAIL_UNCONFIRMED",
            severity="HIGH",
            summary="Latest owner email delivery is not confirmed.",
            domain="operations_supervisor",
            details=latest_email,
        )
    _save_recovery_state(recovery_state)

    db.commit()
    return {
        "base": base,
        "mode": selected_mode,
        "active_market": resolved_market,
        "operational_agents": registry,
        "task_trace": traces,
        "output_quality_reviews": quality_reviews,
        "dependency_checks": dependency_checks,
        "remediation_attempts": remediation_attempts,
        "agent_performance": compute_agent_performance_metrics(
            registry,
            traces,
            active_objective="Stabilize prerequisite layers and governed source integration before downstream expansion",
        ),
        "quarantined_agents": recovery_state.get("quarantined_agents") or [],
        "scheduler": recovery_state.get("scheduler") or {},
        "business_progress": registry_payload.get("summary") or {},
        "current_objective_stack": registry_payload.get("objective_stack") or {},
        "objective_dashboards": registry_payload.get("objective_dashboards") or [],
        "registry_audit": registry_audit,
        "assignment_decision": current_assignment_decision,
        "self_health": supervisor_self_health_status(),
    }


def start_supervisor_scheduler() -> None:
    heartbeat_interval = max(60, int(os.getenv("OPTIME_SUPERVISOR_HEARTBEAT_SWEEP_SECONDS", "300")))
    dependency_interval = max(60, int(os.getenv("OPTIME_SUPERVISOR_DEPENDENCY_SWEEP_SECONDS", "900")))
    full_cycle_interval = max(300, int(os.getenv("OPTIME_SUPERVISOR_FULL_CYCLE_SECONDS", "3600")))
    daily_report_hour = int(os.getenv("OPTIME_SUPERVISOR_DAILY_REPORT_HOUR_UTC", "7"))

    state = _load_recovery_state()
    scheduler_state = state.get("scheduler") if isinstance(state.get("scheduler"), dict) else {}
    if scheduler_state.get("running"):
        heartbeat = state.get("supervisor_heartbeat") if isinstance(state.get("supervisor_heartbeat"), dict) else {}
        last_completion_raw = str(heartbeat.get("last_cycle_completion") or "")
        is_recent = False
        if last_completion_raw:
            try:
                last_completion_dt = datetime.fromisoformat(last_completion_raw.replace("Z", "+00:00"))
                grace_seconds = max(180, heartbeat_interval * 2)
                is_recent = (_now() - _coerce_utc(last_completion_dt)).total_seconds() <= grace_seconds
            except ValueError:
                is_recent = False
        if is_recent:
            return

    state["scheduler"] = {
        "running": True,
        "started_at": _now_iso(),
        "heartbeat_interval_seconds": heartbeat_interval,
        "dependency_interval_seconds": dependency_interval,
        "full_cycle_interval_seconds": full_cycle_interval,
        "daily_report_hour_utc": daily_report_hour,
    }
    _save_recovery_state(state)

    def _runner() -> None:
        last_heartbeat = _now()
        last_dependency = _now()
        last_full = _now() - timedelta(seconds=full_cycle_interval)
        last_daily_date: Optional[str] = None
        while True:
            now = _now()
            try:
                from app.database import SessionLocal

                with SessionLocal() as db:
                    if (now - last_heartbeat).total_seconds() >= heartbeat_interval:
                        run_active_operations_supervisor_cycle(db, mode=_mode())
                        last_heartbeat = now
                    if (now - last_dependency).total_seconds() >= dependency_interval:
                        run_active_operations_supervisor_cycle(db, mode=_mode())
                        last_dependency = now
                    if (now - last_full).total_seconds() >= full_cycle_interval:
                        run_active_operations_supervisor_cycle(db, mode=_mode())
                        last_full = now
                    if now.hour == daily_report_hour and now.strftime("%Y-%m-%d") != last_daily_date:
                        generate_daily_owner_operations_brief(db, mode=_mode())
                        last_daily_date = now.strftime("%Y-%m-%d")
            except Exception as exc:
                state_local = _load_recovery_state()
                state_local["supervisor_heartbeat"] = {
                    "last_cycle_start": state_local.get("supervisor_heartbeat", {}).get("last_cycle_start") if isinstance(state_local.get("supervisor_heartbeat"), dict) else _now_iso(),
                    "last_cycle_completion": _now_iso(),
                    "last_successful_cycle": state_local.get("supervisor_heartbeat", {}).get("last_successful_cycle") if isinstance(state_local.get("supervisor_heartbeat"), dict) else None,
                    "cycle_duration_ms": 0,
                    "cycle_failures": 1,
                    "status": "FAILED",
                    "error": str(exc),
                }
                _save_recovery_state(state_local)
            time.sleep(30)

    thread = threading.Thread(target=_runner, name="optime-active-operations-supervisor", daemon=True)
    thread.start()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_expired(row: AgentKnowledgeReportSnapshot, now: datetime) -> bool:
    verified_until = _coerce_utc(row.verified_until)
    if verified_until is None:
        return True
    return verified_until < now


def _knowledge_age_seconds(row: AgentKnowledgeReportSnapshot, now: datetime) -> int:
    last = _coerce_utc(row.last_successful_refresh) or _coerce_utc(row.last_refreshed_at) or now
    return max(0, int((now - last).total_seconds()))


def _create_incident(
    db: Session,
    *,
    incident_type: str,
    severity: str,
    summary: str,
    agent_key: Optional[str] = None,
    domain: Optional[str] = None,
    details: Optional[Dict[str, object]] = None,
) -> None:
    incident = SupervisorIncidentLog(
        incident_type=incident_type,
        severity=severity,
        status="OPEN",
        agent_key=agent_key,
        domain=domain,
        summary=summary,
        details_json=json.dumps(details or {}),
        created_at=_now(),
    )
    db.add(incident)


def _detect_duplicate_knowledge(db: Session) -> List[Dict[str, object]]:
    duplicates = (
        db.query(
            AgentKnowledgeRecord.agent_key,
            AgentKnowledgeRecord.entity_key,
            func.count(AgentKnowledgeRecord.id).label("n"),
        )
        .group_by(AgentKnowledgeRecord.agent_key, AgentKnowledgeRecord.entity_key)
        .having(func.count(AgentKnowledgeRecord.id) > 1)
        .all()
    )
    return [
        {
            "agent_key": row.agent_key,
            "entity_key": row.entity_key,
            "count": int(row.n),
        }
        for row in duplicates
    ]


def _detect_cross_agent_conflicts(db: Session) -> List[Dict[str, object]]:
    rows = (
        db.query(
            AgentKnowledgeRecord.entity_key,
            func.count(func.distinct(AgentKnowledgeRecord.summary)).label("distinct_summaries"),
            func.count(func.distinct(AgentKnowledgeRecord.agent_key)).label("agents"),
        )
        .group_by(AgentKnowledgeRecord.entity_key)
        .having(func.count(func.distinct(AgentKnowledgeRecord.summary)) > 1)
        .having(func.count(func.distinct(AgentKnowledgeRecord.agent_key)) > 1)
        .all()
    )
    return [
        {
            "entity_key": row.entity_key,
            "distinct_summaries": int(row.distinct_summaries),
            "agents": int(row.agents),
        }
        for row in rows
    ]


def run_supervisor_cycle(db: Session) -> Dict[str, object]:
    now = _now()
    rows = db.query(AgentKnowledgeReportSnapshot).order_by(AgentKnowledgeReportSnapshot.agent_key.asc()).all()

    refreshed_targets: List[str] = []
    retry_targets: List[str] = []
    incidents_created = 0

    # Decision rules and monitoring updates
    for row in rows:
        age = _knowledge_age_seconds(row, now)
        row.knowledge_age_seconds = age

        # Inactive agent detection
        if age > max(3600, int(row.ttl_seconds or 3600) * 2):
            _create_incident(
                db,
                incident_type="INACTIVE_AGENT",
                severity="HIGH",
                summary=f"Agent {row.agent_key} appears inactive.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"knowledge_age_seconds": age, "ttl_seconds": int(row.ttl_seconds or 0)},
            )
            incidents_created += 1

        # Health degradation rule
        if row.health_status not in {"HEALTHY", "DEGRADED"}:
            row.health_status = "DEGRADED"
        if float(row.average_confidence or 0.0) < 0.65:
            row.health_status = "DEGRADED"
            row.freshness_status = "NEEDS_REVIEW"
            row.pending_reviews = int(row.pending_reviews or 0) + 1
            _create_incident(
                db,
                incident_type="LOW_CONFIDENCE",
                severity="MEDIUM",
                summary=f"Agent {row.agent_key} confidence dropped below threshold.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"average_confidence": float(row.average_confidence or 0.0)},
            )
            incidents_created += 1

        # TTL expiry rule
        if _is_expired(row, now):
            row.freshness_status = "EXPIRED"
            _create_incident(
                db,
                incident_type="TTL_EXPIRED",
                severity="HIGH",
                summary=f"Knowledge expired for {row.agent_key}.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"verified_until": row.verified_until.isoformat() if row.verified_until else None},
            )
            incidents_created += 1
            refreshed_targets.append(row.agent_key)

        # Repeated refresh failures rule
        if int(row.failed_refresh_count or 0) >= 3:
            row.freshness_status = "STALE"
            _create_incident(
                db,
                incident_type="REPEATED_REFRESH_FAILURE",
                severity="HIGH",
                summary=f"Repeated refresh failures detected for {row.agent_key}.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"failed_refresh_count": int(row.failed_refresh_count or 0)},
            )
            incidents_created += 1
            retry_targets.append(row.agent_key)

        # Scheduled and priority refresh
        if row.next_refresh_at and _coerce_utc(row.next_refresh_at) <= now:
            refreshed_targets.append(row.agent_key)

    # Detect duplicate/conflicting/missing knowledge
    duplicates = _detect_duplicate_knowledge(db)
    if duplicates:
        _create_incident(
            db,
            incident_type="DUPLICATE_KNOWLEDGE",
            severity="MEDIUM",
            summary="Duplicate knowledge objects detected.",
            details={"count": len(duplicates), "sample": duplicates[:20]},
        )
        incidents_created += 1

    conflicts = _detect_cross_agent_conflicts(db)
    if conflicts:
        _create_incident(
            db,
            incident_type="CONFLICTING_KNOWLEDGE",
            severity="HIGH",
            summary="Conflicting knowledge ownership detected across agents.",
            details={"count": len(conflicts), "sample": conflicts[:20]},
        )
        incidents_created += 1

    missing = [r.agent_key for r in rows if int(r.knowledge_count or 0) <= 0]
    if missing:
        _create_incident(
            db,
            incident_type="MISSING_KNOWLEDGE",
            severity="HIGH",
            summary="One or more agents have missing prepared knowledge.",
            details={"agents": missing},
        )
        incidents_created += 1

    # Refresh queue handling: priority + retry + scheduled
    priority_keys = sorted(set(retry_targets + refreshed_targets))
    refreshed_count = 0
    refresh_failures = 0
    if priority_keys:
        refresh_result = refresh_all_agent_reports(db, refresh_mode="priority", agent_keys=priority_keys, force=False, incremental=False)
        refreshed_count += int(refresh_result.get("refreshed", 0))
        refresh_failures += int(refresh_result.get("failures", 0))

    # Escalate persistent failures after refresh attempt
    failed_rows = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.failed_refresh_count >= 5).all()
    for row in failed_rows:
        _create_incident(
            db,
            incident_type="ESCALATED_REFRESH_FAILURE",
            severity="CRITICAL",
            summary=f"Escalation: {row.agent_key} requires manual intervention.",
            agent_key=row.agent_key,
            domain=row.domain,
            details={"failed_refresh_count": int(row.failed_refresh_count or 0)},
        )
        incidents_created += 1

    db.commit()

    supervisor = compute_supervisor_metrics(db)
    return {
        "incidents_created": incidents_created,
        "priority_refresh_targets": priority_keys,
        "refreshed": refreshed_count,
        "refresh_failures": refresh_failures,
        "supervisor": supervisor,
    }


def recent_incidents(db: Session, limit: int = 200) -> List[Dict[str, object]]:
    rows = (
        db.query(SupervisorIncidentLog)
        .order_by(SupervisorIncidentLog.created_at.desc())
        .limit(max(1, min(limit, 1000)))
        .all()
    )
    out: List[Dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "id": row.id,
                "incident_type": row.incident_type,
                "severity": row.severity,
                "status": row.status,
                "agent_key": row.agent_key,
                "domain": row.domain,
                "summary": row.summary,
                "details": json.loads(row.details_json or "{}"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out


def stale_usage_summary(db: Session, hours: int = 24) -> Dict[str, object]:
    since = _now() - timedelta(hours=max(1, min(hours, 24 * 30)))
    rows = (
        db.query(RecommendationKnowledgeUsageLog)
        .filter(RecommendationKnowledgeUsageLog.logged_at >= since)
        .all()
    )
    total = len(rows)
    stale_used = [row for row in rows if int(row.used_stale or 0) == 1]
    stale_not_allowed = [row for row in rows if int(row.used_stale or 0) == 1 and int(row.policy_allowed or 0) == 0]

    return {
        "window_hours": hours,
        "total_usage_logs": total,
        "stale_usage_count": len(stale_used),
        "stale_not_allowed_count": len(stale_not_allowed),
        "sample": [
            {
                "recommendation_key": row.recommendation_key,
                "agent_key": row.agent_key,
                "freshness_status": row.freshness_status,
                "policy_allowed": bool(int(row.policy_allowed or 0)),
                "decision": row.decision,
                "reason": row.decision_reason,
            }
            for row in stale_not_allowed[:30]
        ],
    }
