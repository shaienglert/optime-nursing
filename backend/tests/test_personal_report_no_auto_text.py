from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_text_equals_governed_use_text():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "Exact X.", "provenance_ids": ["case:x"]}])
    report = render_personal_report(payload)
    rendered = next(c["text"] for s in report["sections"] for c in s["claims"] if c["claim_id"] == "case:x")
    use = next(u for u in payload.claim_uses if u.claim_id == "case:x")
    assert rendered == use.rendered_text
