from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_research_confidence_is_passed_through_not_upgraded():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        research_claims=[{"claim_id": "research:low", "approved_text": "Limited evidence finding.", "provenance_ids": ["research:RI-LOW"], "confidence": "LOW"}],
    )
    report = render_personal_report(payload)
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "research:low")
    assert claim["confidence"] == "LOW"
