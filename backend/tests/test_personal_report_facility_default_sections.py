from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportSection


def test_facility_default_sections_preserve_fact_vs_unknown():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[
        {"claim_id": "facility:v", "text": "Verified.", "verified": True, "provenance_ids": ["facility:v"]},
        {"claim_id": "facility:u", "text": "Unknown.", "unknown": True, "provenance_ids": ["facility:u:UNKNOWN"]},
    ])
    claims = {c.claim_id: c for c in payload.approved_claims}
    assert claims["facility:v"].allowed_sections == (ReportSection.WHY_THIS_PLACE,)
    assert claims["facility:u"].allowed_sections == (ReportSection.BEFORE_YOU_DECIDE,)
