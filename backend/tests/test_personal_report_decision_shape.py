from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_rendered_decision_shape_is_read_only_projection():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert set(report["decision"]) == {"phase", "finality", "can_show_recommendations"}
