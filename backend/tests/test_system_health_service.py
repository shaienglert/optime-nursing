from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import system_health_service


def test_adapter_returns_delivery_false_when_chief_reports_failure(monkeypatch) -> None:
    monkeypatch.setattr(system_health_service, "SessionLocal", lambda: type("Ctx", (), {
        "__enter__": lambda self: object(),
        "__exit__": lambda self, exc_type, exc, tb: None,
    })())
    monkeypatch.setattr(system_health_service, "run_active_operations_supervisor_cycle", lambda db: {"ok": True})
    monkeypatch.setattr(
        system_health_service,
        "generate_daily_owner_operations_brief",
        lambda db: {
            "report_id": "2026-08-05",
            "delivery_confirmed": False,
            "delivery_status": "DELIVERY_BLOCKED",
            "delivery_message": "smtp missing",
            "recipients": ["owner@example.com"],
            "mode": "DRY_RUN",
        },
    )

    result = system_health_service.generate_and_send_daily_system_health_report()
    assert result["delivery_confirmed"] is False
    assert result["delivery_status"] == "DELIVERY_BLOCKED"


def test_adapter_returns_delivery_true_when_chief_reports_success(monkeypatch) -> None:
    monkeypatch.setattr(system_health_service, "SessionLocal", lambda: type("Ctx", (), {
        "__enter__": lambda self: object(),
        "__exit__": lambda self, exc_type, exc, tb: None,
    })())
    monkeypatch.setattr(system_health_service, "run_active_operations_supervisor_cycle", lambda db: {"ok": True})
    monkeypatch.setattr(
        system_health_service,
        "generate_daily_owner_operations_brief",
        lambda db: {
            "report_id": "2026-08-05",
            "delivery_confirmed": True,
            "delivery_status": "DELIVERY_ACCEPTED",
            "delivery_message": "sent",
            "recipients": ["owner@example.com"],
            "mode": "DRY_RUN",
        },
    )

    result = system_health_service.generate_and_send_daily_system_health_report()
    assert result["delivery_confirmed"] is True
    assert result["delivery_status"] == "DELIVERY_ACCEPTED"
