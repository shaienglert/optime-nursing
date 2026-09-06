from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_blocked_case_cannot_be_presented_as_recommendation():
    result = {
        "results": [],
        "decision_intelligence": {
            "human_intelligence": {
                "decision_readiness": "NOT_READY",
                "readiness_guardian": {"client_owned_blockers": [{"field": "budget"}]},
            }
        },
    }
    report = render_personal_report(build_personal_report_payload(result))
    assert report["decision"]["can_show_recommendations"] is False
    assert report["decision"]["finality"] == "NONE"
    assert report["decision"]["phase"] == "CLIENT_INPUT_REQUIRED"
