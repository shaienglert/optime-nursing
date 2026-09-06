import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_caller_has_no_report_decision_override_parameter():
    assert "report_decision" not in inspect.signature(build_personal_report_payload).parameters
