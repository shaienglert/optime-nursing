import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_has_no_unknown_resolution_function():
    source = inspect.getsource(build_personal_report_payload).lower()
    assert "resolve_unknown" not in source
    assert "verify_unknown" not in source
