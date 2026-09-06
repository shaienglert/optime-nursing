from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_has_no_financial_advice_channel():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert "financial_advice" not in report
    assert "funding_strategy" not in report
