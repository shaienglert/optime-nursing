from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_claim_ids_equal_governed_use_ids():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:x"]}])
    report = render_personal_report(payload)
    assert {c["claim_id"] for s in report["sections"] for c in s["claims"]} == {u.claim_id for u in payload.claim_uses}
