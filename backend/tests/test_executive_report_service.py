from __future__ import annotations

from app.database import SessionLocal
from app.services.executive_report_service import _build_report_payload, _load_evidence_parity_audit, _to_markdown


def test_load_evidence_parity_audit_is_a_module_level_function():
    # Regression guard: a prior commit accidentally nested this function inside
    # _extract_int, making it unreachable and crashing every report generation
    # (and, in production, the daily report scheduler) with a NameError.
    result = _load_evidence_parity_audit()
    assert "status" in result


def test_build_report_payload_does_not_raise():
    db = SessionLocal()
    try:
        payload = _build_report_payload(db, previous_payload=None)
    finally:
        db.close()
    assert isinstance(payload, dict)
    markdown = _to_markdown(payload)
    assert isinstance(markdown, str)
    assert len(markdown) > 0
