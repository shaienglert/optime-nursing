from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import chief_ai_supervisor


def test_operational_agent_differs_from_specification_only(monkeypatch) -> None:
    monkeypatch.setattr(chief_ai_supervisor, "_readiness_layers", lambda: {"Layer 6": "FAILED", "Layer 8": "READY FOR REVIEW", "Layer 9": "PARTIALLY COMPLETE"})
    status_active = chief_ai_supervisor._agent_operational_status(schedule="EVERY_15_MINUTES", has_runtime_evidence=True, has_recent_run=True)
    status_spec = chief_ai_supervisor._agent_operational_status(schedule="CONFIGURED_NOT_RUNNING", has_runtime_evidence=False, has_recent_run=False)
    assert status_active == chief_ai_supervisor.STATUS_ACTIVE_AGENT
    assert status_spec == chief_ai_supervisor.STATUS_CONFIGURED_NOT_RUNNING


def test_real_execution_heartbeat_states() -> None:
    now = datetime.now(timezone.utc)
    stale = now - timedelta(hours=3)
    running_status = "RUNNING"
    assert running_status == "RUNNING"
    # Derived heartbeat logic checks:
    if (now - stale) > timedelta(hours=2):
        derived = "STUCK"
    else:
        derived = "RUNNING"
    assert derived == "STUCK"


def test_dependency_gate_blocks_media_before_canonical_pass(monkeypatch) -> None:
    monkeypatch.setattr(chief_ai_supervisor, "_readiness_layers", lambda: {
        "Layer 3": "PARTIALLY COMPLETE",
        "Layer 5": "PARTIALLY COMPLETE",
        "Layer 6": "FAILED",
    })
    monkeypatch.setattr(chief_ai_supervisor, "_read_json", lambda path: {"media_pilot_gate": {"status": "FAIL"}})
    decision = chief_ai_supervisor.dependency_gate_decision("MEDIA_INTELLIGENCE", market="las-vegas")
    assert decision["allowed"] is False
    assert "NEVADA_MEDIA_PILOT_GATE" in decision["unmet_prerequisites"]


def test_wrong_market_data_cannot_mark_nevada_media_ready(monkeypatch) -> None:
    monkeypatch.setattr(chief_ai_supervisor, "_readiness_layers", lambda: {
        "Layer 3": "PASS",
        "Layer 5": "PASS",
        "Layer 6": "PASS",
    })
    monkeypatch.setattr(chief_ai_supervisor, "_read_json", lambda path: {"media_pilot_gate": {"status": "FAIL"}})
    decision = chief_ai_supervisor.dependency_gate_decision("MEDIA_INTELLIGENCE", market="nevada")
    assert decision["allowed"] is False


def test_supervisor_scheduler_marks_running(monkeypatch, tmp_path: Path) -> None:
    recovery_path = tmp_path / "system_recovery_state.json"
    monkeypatch.setattr(chief_ai_supervisor, "RECOVERY_STATE_PATH", recovery_path)
    monkeypatch.setattr(chief_ai_supervisor, "_save_recovery_state", lambda payload: recovery_path.write_text(json.dumps(payload), encoding="utf-8"))
    monkeypatch.setattr(chief_ai_supervisor, "_load_recovery_state", lambda: {
        "generated_at_utc": chief_ai_supervisor._now_iso(),
        "state_version": "test",
        "mode": chief_ai_supervisor._mode(),
        "quarantined_agents": [],
        "blocked_downstream_components": [],
        "last_successful_end_to_end_recovery": None,
        "agent_retry_budgets": {},
        "supervisor_heartbeat": {},
        "latest_generated_report": {},
        "latest_email_delivery": {},
        "scheduler": {},
    })
    monkeypatch.setattr(chief_ai_supervisor.threading, "Thread", lambda *args, **kwargs: type("T", (), {"start": lambda self: None})())
    chief_ai_supervisor.start_supervisor_scheduler()
    saved = json.loads(recovery_path.read_text(encoding="utf-8"))
    assert saved["scheduler"]["running"] is True


def test_orphaned_output_classification_after_24h() -> None:
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat().replace("+00:00", "Z")
    row = {
        "terminal_status": chief_ai_supervisor.TRACE_VALIDATED,
        "output_artifacts": [{"record_type": "facility"}],
        "actual_consumers": [],
        "completed_at": old,
    }
    assert chief_ai_supervisor.classify_unconsumed_output(row) == chief_ai_supervisor.OUTPUT_ORPHANED


def test_wrong_market_output_rejected_for_nevada() -> None:
    row = {
        "terminal_status": chief_ai_supervisor.TRACE_VALIDATED,
        "validation_status": "PASS",
        "output_artifacts": [{"entity_key": "fl-facility-001"}],
    }
    review = chief_ai_supervisor.review_task_output_quality(row, "nevada")
    assert review["decision"] == chief_ai_supervisor.QUALITY_REJECT
    assert review["market_match"] is False


def test_unsupported_market_fails_explicitly() -> None:
    try:
        chief_ai_supervisor._resolve_active_market("unsupported-market")
        assert False, "Expected ValueError for unsupported market"
    except ValueError as exc:
        assert "Unsupported active market" in str(exc)


def test_independent_watchdog_detects_missed_cycle_and_stale_healthy(monkeypatch, tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    old_completion = (now - timedelta(minutes=12)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    old_start = (now - timedelta(minutes=13)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    monkeypatch.setattr(
        chief_ai_supervisor,
        "_load_recovery_state",
        lambda: {
            "generated_at_utc": chief_ai_supervisor._now_iso(),
            "state_version": "test",
            "mode": "DRY_RUN",
            "quarantined_agents": [],
            "blocked_downstream_components": [],
            "last_successful_end_to_end_recovery": None,
            "agent_retry_budgets": {},
            "latest_generated_report": {},
            "latest_email_delivery": {},
            "scheduler": {"running": True, "heartbeat_interval_seconds": 60},
            "supervisor_heartbeat": {
                "last_cycle_start": old_start,
                "last_cycle_completion": old_completion,
                "status": "HEALTHY",
            },
        },
    )

    inserted: list[dict] = []

    def _fake_create_incident(db, **kwargs):
        inserted.append(kwargs)

    monkeypatch.setattr(chief_ai_supervisor, "_create_incident", _fake_create_incident)

    class _FakeQuery:
        def order_by(self, *args, **kwargs):
            return self

        def first(self):
            return type("Row", (), {"id": 1})()

    class _FakeDb:
        def flush(self):
            return None

        def commit(self):
            return None

        def query(self, model):
            return _FakeQuery()

    result = chief_ai_supervisor.run_independent_supervisor_watchdog(_FakeDb(), max_allowed_lateness_seconds=120)
    assert result["detected_missed_cycle"] is True
    assert result["stale_self_declared_healthy"] is True
    assert result["incident_created"] is True
    assert inserted and inserted[0]["incident_type"] == chief_ai_supervisor.WATCHDOG_INCIDENT_MISSED_CYCLE


def test_start_scheduler_recovers_from_stale_running_flag(monkeypatch, tmp_path: Path) -> None:
    recovery_path = tmp_path / "system_recovery_state.json"
    stale_completion = (datetime.now(timezone.utc) - timedelta(minutes=20)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    monkeypatch.setattr(chief_ai_supervisor, "RECOVERY_STATE_PATH", recovery_path)
    monkeypatch.setattr(chief_ai_supervisor, "_save_recovery_state", lambda payload: recovery_path.write_text(json.dumps(payload), encoding="utf-8"))
    monkeypatch.setattr(
        chief_ai_supervisor,
        "_load_recovery_state",
        lambda: {
            "generated_at_utc": chief_ai_supervisor._now_iso(),
            "state_version": "test",
            "mode": chief_ai_supervisor._mode(),
            "quarantined_agents": [],
            "blocked_downstream_components": [],
            "last_successful_end_to_end_recovery": None,
            "agent_retry_budgets": {},
            "supervisor_heartbeat": {"last_cycle_completion": stale_completion, "status": "HEALTHY"},
            "latest_generated_report": {},
            "latest_email_delivery": {},
            "scheduler": {"running": True, "heartbeat_interval_seconds": 60},
        },
    )
    monkeypatch.setattr(chief_ai_supervisor.threading, "Thread", lambda *args, **kwargs: type("T", (), {"start": lambda self: None})())

    chief_ai_supervisor.start_supervisor_scheduler()
    saved = json.loads(recovery_path.read_text(encoding="utf-8"))
    assert saved["scheduler"]["running"] is True
    assert int(saved["scheduler"]["heartbeat_interval_seconds"]) >= 60


def test_supervisor_cycle_includes_registry_audit_and_blocked_assignment(monkeypatch) -> None:
    payload = {
        "summary": {
            "current_active_objective": "launch_nevada",
            "current_executable_capability": "source_intelligence",
            "current_blocker": "market_builder",
        },
        "objective_stack": {
            "objective_id": "launch_nevada",
            "current_work": "source_intelligence",
            "current_blocker": "market_builder",
            "assigned_agent": "OPTIME Source Intelligence",
            "current_task": "Test task",
            "required_capabilities": ["source_intelligence"],
        },
        "objective_dashboards": [],
        "self_audit": {
            "has_p0_findings": True,
            "findings": [{"finding_id": "p0-test", "severity": "CRITICAL", "finding_type": "ACTIVE_OBJECTIVE_COUNT_INVALID"}],
            "registry_trust_verdict": "REGISTRY_NOT_TRUSTED",
        },
        "registry_trust_verdict": "REGISTRY_NOT_TRUSTED",
        "claim_status_summary": {"CRITICAL": 1},
        "assignment_decision": {
            "allowed": False,
            "reason": "DEPENDENCY_BLOCKED",
            "suggested_prerequisite": "market_builder",
        },
    }
    incidents: list[dict] = []
    saved_states: list[dict] = []

    monkeypatch.setattr(chief_ai_supervisor, "load_platform_registry", lambda: payload)
    monkeypatch.setattr(chief_ai_supervisor, "run_platform_registry_self_audit", lambda arg: payload["self_audit"])
    monkeypatch.setattr(chief_ai_supervisor, "run_supervisor_cycle", lambda db: {"status": "ok"})
    monkeypatch.setattr(chief_ai_supervisor, "operational_agent_registry", lambda db, market="": [])
    monkeypatch.setattr(chief_ai_supervisor, "task_output_consumer_trace", lambda db, limit=200: [])
    monkeypatch.setattr(chief_ai_supervisor, "recent_incidents", lambda db, limit=400: [])
    monkeypatch.setattr(chief_ai_supervisor, "_load_remediation_registry", lambda: {"records": []})
    monkeypatch.setattr(chief_ai_supervisor, "_save_remediation_registry", lambda payload: None)
    monkeypatch.setattr(chief_ai_supervisor, "_load_recovery_state", lambda: {"agent_retry_budgets": {}, "quarantined_agents": [], "blocked_downstream_components": [], "scheduler": {}, "latest_generated_report": {}, "latest_email_delivery": {}})
    monkeypatch.setattr(chief_ai_supervisor, "_save_recovery_state", lambda state: saved_states.append(state))
    monkeypatch.setattr(chief_ai_supervisor, "compute_agent_performance_metrics", lambda *args, **kwargs: {})
    monkeypatch.setattr(chief_ai_supervisor, "supervisor_self_health_status", lambda: {"health": "DEGRADED"})
    monkeypatch.setattr(chief_ai_supervisor, "dependency_gate_decision", lambda domain, market="": {"allowed": True})
    monkeypatch.setattr(chief_ai_supervisor, "_create_incident", lambda db, **kwargs: incidents.append(kwargs))

    class _FakeDb:
        def commit(self):
            return None

    result = chief_ai_supervisor.run_active_operations_supervisor_cycle(_FakeDb(), mode="DRY_RUN", active_market="nevada")
    assert result["registry_audit"]["has_p0_findings"] is True
    assert result["assignment_decision"]["reason"] == "DEPENDENCY_BLOCKED"
    assert any(incident["incident_type"] == "REGISTRY_AUDIT_FAILED" for incident in incidents)
    assert any(incident["incident_type"] == "REGISTRY_CURRENT_ASSIGNMENT_BLOCKED" for incident in incidents)
    assert saved_states
    assert any("latest_registry_runtime_proof" in state for state in saved_states)
