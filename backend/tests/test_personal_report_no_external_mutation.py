from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_output_has_no_external_action_fields():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    forbidden = {"send_email", "book_tour", "contact_facility", "update_case", "save_decision"}
    assert not forbidden.intersection(report)
