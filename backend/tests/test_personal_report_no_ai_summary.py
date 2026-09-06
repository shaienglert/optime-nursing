from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_has_no_generated_summary_or_narrative():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert not set(report).intersection({"summary", "narrative", "ai_summary", "executive_summary"})
