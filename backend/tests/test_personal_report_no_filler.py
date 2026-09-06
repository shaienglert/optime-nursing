from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_every_runtime_text_is_a_governed_claim_text():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    report = render_personal_report(payload)
    texts = {c["text"] for s in report["sections"] for c in s["claims"]}
    assert texts == {c.approved_text for c in payload.approved_claims}
