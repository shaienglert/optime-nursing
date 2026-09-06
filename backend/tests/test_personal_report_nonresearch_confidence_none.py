from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_runtime_user_fact_has_no_manufactured_confidence():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "User fact.", "provenance_ids": ["case:x"]}]))
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "case:x")
    assert claim["confidence"] is None
