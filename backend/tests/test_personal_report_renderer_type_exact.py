from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_preserves_claim_type_exactly():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:u", "text": "Unknown.", "unknown": True, "provenance_ids": ["facility:u:UNKNOWN"]}])
    report = render_personal_report(payload)
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "facility:u")
    assert claim["claim_type"] == "UNKNOWN"
