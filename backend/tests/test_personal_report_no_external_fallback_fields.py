from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_runtime_report_has_no_external_fallback_channel():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert not set(report).intersection({"web_sources", "documents", "external_sources", "fallback_research"})
