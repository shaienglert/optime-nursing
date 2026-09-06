from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportSection


def test_research_default_section_is_fixed():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:x")
    assert claim.allowed_sections == (ReportSection.SUCCESSFUL_TRANSITION,)
