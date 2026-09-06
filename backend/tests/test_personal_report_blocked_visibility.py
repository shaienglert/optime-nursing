from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_client_blocker_forces_hidden_recommendation_in_report():
    result = {"results": [], "decision_intelligence": {"human_intelligence": {"readiness_guardian": {"client_owned_blockers": [{"field": "budget"}]}}}}
    report = render_personal_report(build_personal_report_payload(result))
    assert report["decision"] == {"phase": "CLIENT_INPUT_REQUIRED", "finality": "NONE", "can_show_recommendations": False}
