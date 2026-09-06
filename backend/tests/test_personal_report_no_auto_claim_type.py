from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_claim_type_equals_governed_claim_type():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:x"]}])
    report = render_personal_report(payload)
    rendered = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "case:x")
    approved = next(c for c in payload.approved_claims if c.claim_id == "case:x")
    assert rendered["claim_type"] == approved.claim_type.value
