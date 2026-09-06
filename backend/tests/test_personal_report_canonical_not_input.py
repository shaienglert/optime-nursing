import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_caller_has_no_canonical_state_override_parameter():
    assert "canonical_state" not in inspect.signature(build_personal_report_payload).parameters
