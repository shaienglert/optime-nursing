from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_runtime_report_retains_research_confidence():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"], "confidence": "MEDIUM"}]))
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "research:x")
    assert claim["confidence"] == "MEDIUM"
