from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_provenance_is_not_hidden_from_renderer_output():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    claim = report["sections"][0]["claims"][0]
    assert "provenance_ids" in claim and claim["provenance_ids"]
