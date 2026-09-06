from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_does_not_rewrite_provenance():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:a", "case:b"]}])
    report = render_personal_report(payload)
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "case:x")
    assert claim["provenance_ids"] == ["case:a", "case:b"]
