from __future__ import annotations

"""Compatibility adapter that delegates to the canonical chief supervisor.

Daily owner report flow ownership remains in chief_ai_supervisor.py.
"""

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.services.chief_ai_supervisor import generate_daily_owner_operations_brief

REPORT_MD_PATH = Path(__file__).resolve().parents[3] / "reports" / "DAILY_SYSTEM_HEALTH.md"
REPORT_JSON_PATH = Path(__file__).resolve().parents[3] / "reports" / "DAILY_SYSTEM_HEALTH.json"


def generate_daily_system_health(db: Session) -> Dict[str, Any]:
    return generate_daily_owner_operations_brief(db)
