from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_does_not_invent_empty_sections():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert all(section["claims"] for section in report["sections"])
