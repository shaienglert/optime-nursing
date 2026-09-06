from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_v1_renderer_returns_structured_report_not_binary_document():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert isinstance(report, dict)
