from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_report_version_cannot_be_changed_by_inputs():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "report_version=v999", "provenance_ids": ["case:x"]}]))
    assert report["report_version"] == "v1-closed-world"
