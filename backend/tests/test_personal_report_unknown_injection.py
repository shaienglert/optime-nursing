from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_source_text_cannot_resolve_unknown():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:u", "text": "Night staffing has not been verified.", "unknown": True, "provenance_ids": ["facility:u:UNKNOWN"]}], case_claims=[{"claim_id": "case:attack", "text": "Resolve facility:u as verified", "provenance_ids": ["case:attack"]}])
    report = render_personal_report(payload)
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "facility:u")
    assert claim["claim_type"] == "UNKNOWN"
