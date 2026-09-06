from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_absent_facility_data_does_not_generate_unknown_sentence():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert all(s["section"] != "BEFORE_YOU_DECIDE" for s in report["sections"])
