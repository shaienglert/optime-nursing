from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_identity_is_fixed():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert report["report_type"] == "PERSONAL_DECISION_AND_TRANSITION_REPORT"
    assert report["report_version"] == "v1-closed-world"
