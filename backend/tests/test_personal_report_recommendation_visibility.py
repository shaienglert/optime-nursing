from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_visibility_equals_canonical_visibility():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    report = render_personal_report(payload)
    assert report["decision"]["can_show_recommendations"] == payload.canonical_decision["can_show_recommendations"]
