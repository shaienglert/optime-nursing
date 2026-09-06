from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_can_show_recommendations_matches_canonical_exactly():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    assert render_personal_report(payload)["decision"]["can_show_recommendations"] is payload.canonical_decision["can_show_recommendations"]
