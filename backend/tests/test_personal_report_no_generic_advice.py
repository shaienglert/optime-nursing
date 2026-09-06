from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_does_not_fill_transition_section_with_generic_advice():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "A transition is planned.", "provenance_ids": ["case:x"]}]))
    assert all(s["section"] != "SUCCESSFUL_TRANSITION" for s in report["sections"])
