from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_has_no_auto_generated_questions_channel():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert "questions" not in report
    assert "visit_questions" not in report
