from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_output_has_no_case_mutation_fields():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    forbidden = {"update_profile", "infer_profile", "fill_missing_case_data", "case_write"}
    assert not forbidden.intersection(report)
