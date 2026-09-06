from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_canonical_reason_is_not_rewritten_for_user_friendliness():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    report = render_personal_report(payload)
    rendered = next(c["text"] for s in report["sections"] for c in s["claims"] if c["claim_id"] == "decision:canonical-reason")
    approved = next(c.approved_text for c in payload.approved_claims if c.claim_id == "decision:canonical-reason")
    assert rendered == approved
