from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_transition_section_is_absent_without_approved_research_claim():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert "SUCCESSFUL_TRANSITION" not in {section["section"] for section in report["sections"]}
