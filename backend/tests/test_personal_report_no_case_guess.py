from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_absent_case_data_does_not_generate_situation_or_role_claims():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert not {"YOUR_SITUATION", "YOUR_ROLE", "WHAT_MATTERS"}.intersection({s["section"] for s in report["sections"]})
