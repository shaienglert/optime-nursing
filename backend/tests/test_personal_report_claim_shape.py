from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_rendered_claim_shape_is_closed():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    claim = report["sections"][0]["claims"][0]
    assert set(claim) == {"claim_id", "text", "claim_type", "provenance_ids", "confidence"}
