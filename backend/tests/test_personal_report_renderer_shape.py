from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_runtime_report_shape_is_minimal():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert set(report) == {"report_type", "report_version", "decision", "sections"}
