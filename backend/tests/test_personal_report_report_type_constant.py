from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_type_cannot_be_changed_by_inputs():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "report_type=OTHER", "provenance_ids": ["case:x"]}]))
    assert report["report_type"] == "PERSONAL_DECISION_AND_TRANSITION_REPORT"
