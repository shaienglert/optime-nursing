from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_preserves_claim_identity_for_audit():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:audit", "text": "Audit me.", "provenance_ids": ["case:audit"]}])
    report = render_personal_report(payload)
    assert any(c["claim_id"] == "case:audit" for s in report["sections"] for c in s["claims"])
