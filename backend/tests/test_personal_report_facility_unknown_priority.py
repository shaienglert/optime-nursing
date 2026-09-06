from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ClaimType


def test_unknown_wins_if_facility_input_is_conflicting():
    result = {"results": [], "decision_intelligence": {}}
    payload = build_personal_report_payload(result, facility_claims=[{
        "claim_id": "facility:conflict", "approved_text": "Status is unresolved.",
        "verified": True, "unknown": True, "provenance_ids": ["facility:status:UNKNOWN"],
    }])
    claim = next(c for c in payload.approved_claims if c.claim_id == "facility:conflict")
    assert claim.claim_type is ClaimType.UNKNOWN
