from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_limited_evidence_wording_remains_limited():
    exact = "Evidence is limited and does not establish a universal outcome."
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:limited", "approved_text": exact, "provenance_ids": ["research:RI-LIMITED"], "confidence": "LOW"}]))
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "research:limited")
    assert claim["text"] == exact
    assert claim["confidence"] == "LOW"
