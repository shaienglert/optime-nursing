from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_no_verified_facility_claim_means_no_why_this_place_section():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert all(s["section"] != "WHY_THIS_PLACE" for s in report["sections"])
