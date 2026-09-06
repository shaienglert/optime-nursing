from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportSection


def test_case_default_section_is_fixed():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "User fact.", "provenance_ids": ["case:x"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "case:x")
    assert claim.allowed_sections == (ReportSection.YOUR_SITUATION,)
