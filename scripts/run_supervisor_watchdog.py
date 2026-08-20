from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.models.agent_execution import SupervisorIncidentLog

HEARTBEAT_TYPE = "SUPERVISOR_HEARTBEAT"
MISSED_TYPE = "SUPERVISOR_MISSED_CYCLE_WATCHDOG"
MIN_LATE_SECONDS = 480  # supervisor runs every 5m; allow one delayed tick before CRITICAL


def _utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> int:
    max_lateness = MIN_LATE_SECONDS
    if len(sys.argv) > 1:
        try:
            max_lateness = max(MIN_LATE_SECONDS, int(sys.argv[1]))
        except ValueError:
            max_lateness = MIN_LATE_SECONDS

    db = SessionLocal()
    try:
        heartbeat = (
            db.query(SupervisorIncidentLog)
            .filter(SupervisorIncidentLog.incident_type == HEARTBEAT_TYPE)
            .order_by(SupervisorIncidentLog.created_at.desc())
            .first()
        )
        now = datetime.now(timezone.utc)
        heartbeat_at = _utc(heartbeat.created_at) if heartbeat is not None else None
        age_seconds = int((now - heartbeat_at).total_seconds()) if heartbeat_at else None
        missed = heartbeat_at is None or age_seconds > max_lateness

        existing_alert = (
            db.query(SupervisorIncidentLog)
            .filter(
                SupervisorIncidentLog.incident_type == MISSED_TYPE,
                SupervisorIncidentLog.status == "OPEN",
            )
            .order_by(SupervisorIncidentLog.id.desc())
            .first()
        )

        incident_created = False
        incident_resolved = False
        if missed and existing_alert is None:
            db.add(
                SupervisorIncidentLog(
                    incident_type=MISSED_TYPE,
                    severity="CRITICAL",
                    status="OPEN",
                    domain="operations_supervisor_watchdog",
                    summary="Independent watchdog detected missing/stale Chief AI Supervisor heartbeat.",
                    details_json=json.dumps(
                        {
                            "heartbeat_at": heartbeat_at.isoformat() if heartbeat_at else None,
                            "age_seconds": age_seconds,
                            "max_allowed_lateness_seconds": max_lateness,
                            "required_action": "SYSTEM_ALERT_SUPERVISOR_RECOVERY",
                        },
                        sort_keys=True,
                    ),
                    created_at=now,
                )
            )
            incident_created = True
        elif not missed and existing_alert is not None:
            existing_alert.status = "RESOLVED"
            incident_resolved = True
        db.commit()

        result = {
            "watchdog": "INDEPENDENT_SHARED_DB",
            "detected_missed_cycle": missed,
            "heartbeat_at": heartbeat_at.isoformat() if heartbeat_at else None,
            "heartbeat_age_seconds": age_seconds,
            "max_allowed_lateness_seconds": max_lateness,
            "incident_created": incident_created,
            "incident_resolved": incident_resolved,
        }
    finally:
        db.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if bool(result["detected_missed_cycle"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
