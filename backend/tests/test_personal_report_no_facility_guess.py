from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_why_this_place_absent_without_verified_facility_fact():
    report = render_personal_report(build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        facility_claims=[{"claim_id": "facility:guess", "text": "Probably has a nurse.", "verified": False, "provenance_ids": ["facility:marketing"]}],
    ))
    assert "WHY_THIS_PLACE" not in {section["section"] for section in report["sections"]}
