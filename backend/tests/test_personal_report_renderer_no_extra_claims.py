from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_cannot_add_claims():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:x"]}])
    report = render_personal_report(payload)
    rendered_count = sum(len(s["claims"]) for s in report["sections"])
    assert rendered_count == len(payload.claim_uses)
