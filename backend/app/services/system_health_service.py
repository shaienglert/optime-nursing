from __future__ import annotations

"""Compatibility adapter for daily system health generation.

Canonical ownership is in chief_ai_supervisor.py.
This module preserves existing call sites while avoiding parallel supervisor logic.
"""

from typing import Any, Dict

from app.database import SessionLocal
from app.services.chief_ai_supervisor import (
    generate_daily_owner_operations_brief,
    run_active_operations_supervisor_cycle,
)


def generate_and_send_daily_system_health_report() -> Dict[str, Any]:
    with SessionLocal() as db:
        run_active_operations_supervisor_cycle(db)
        result = generate_daily_owner_operations_brief(db)

    return {
        "report_markdown": "reports/DAILY_SYSTEM_HEALTH.md",
        "report_json": "reports/DAILY_SYSTEM_HEALTH.json",
        "report_id": result.get("report_id"),
        "delivery_confirmed": bool(result.get("delivery_confirmed")),
        "delivery_status": result.get("delivery_status"),
        "delivery_message": result.get("delivery_message"),
        "recipients": result.get("recipients") or [],
        "mode": result.get("mode"),
    }
