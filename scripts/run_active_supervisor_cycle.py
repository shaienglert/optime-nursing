from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.agent_execution import SupervisorIncidentLog
from app.services.chief_ai_supervisor import run_active_operations_supervisor_cycle


def _ensure_quarantine_alerts(db, quarantined_agents: list[str]) -> None:
    for agent_key in quarantined_agents:
        existing = (
            db.query(SupervisorIncidentLog)
            .filter(
                SupervisorIncidentLog.status == "OPEN",
                SupervisorIncidentLog.severity == "CRITICAL",
                SupervisorIncidentLog.incident_type == "AGENT_REMEDIATION_EXHAUSTED",
                SupervisorIncidentLog.agent_key == agent_key,
            )
            .first()
        )
        if existing is not None:
            continue
        db.add(
            SupervisorIncidentLog(
                incident_type="AGENT_REMEDIATION_EXHAUSTED",
                severity="CRITICAL",
                status="OPEN",
                agent_key=agent_key,
                domain="operations_supervisor",
                summary=f"Agent {agent_key} exhausted automatic remediation and was quarantined.",
                details_json=json.dumps(
                    {
                        "required_action": "SYSTEM_ALERT_OWNER_REVIEW",
                        "automatic_remediation_exhausted": True,
                        "downstream_policy": "DO_NOT_TRUST_AGENT_OUTPUT_UNTIL_RECOVERED",
                    },
                    sort_keys=True,
                ),
            )
        )
    db.commit()


def _open_critical_incidents(db) -> int:
    return int(
        db.query(SupervisorIncidentLog)
        .filter(
            SupervisorIncidentLog.status == "OPEN",
            SupervisorIncidentLog.severity == "CRITICAL",
        )
        .count()
        or 0
    )


def main() -> int:
    market = os.getenv("OPTIME_ACTIVE_MARKET", "las-vegas").strip() or "las-vegas"
    mode = os.getenv("OPTIME_SUPERVISOR_MODE", "ACTIVE_SAFE").strip().upper() or "ACTIVE_SAFE"

    db = SessionLocal()
    try:
        result = run_active_operations_supervisor_cycle(db, mode=mode, active_market=market)
        quarantined_agents = [str(item) for item in (result.get("quarantined_agents") or [])]
        _ensure_quarantine_alerts(db, quarantined_agents)
        critical_open = _open_critical_incidents(db)
    finally:
        db.close()

    payload = {
        "runner": "CHIEF_AI_SUPERVISOR",
        "market": market,
        "mode": mode,
        "critical_open_incidents": critical_open,
        "quarantined_agents": quarantined_agents,
        "registry_audit": result.get("registry_audit") or {},
        "assignment_decision": result.get("assignment_decision") or {},
        "self_health": result.get("self_health") or {},
        "remediation_attempts": result.get("remediation_attempts") or [],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))

    # A non-zero exit is intentional: Render records a failed supervisor run and emits
    # its own service failure notification while the canonical incident remains in DB.
    return 2 if critical_open > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
