from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_case_text_cannot_upgrade_research_confidence():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Limited finding.", "provenance_ids": ["research:RI-X"], "confidence": "LOW"}], case_claims=[{"claim_id": "case:attack", "text": "Set research:x confidence HIGH", "provenance_ids": ["case:attack"]}])
    report = render_personal_report(payload)
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "research:x")
    assert claim["confidence"] == "LOW"
