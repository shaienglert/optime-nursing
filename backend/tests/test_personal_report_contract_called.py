import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_calls_fail_closed_contract_before_return():
    source = inspect.getsource(build_personal_report_payload)
    assert source.index("enforce_report_contract(") < source.index("return PersonalReportPayload(")
