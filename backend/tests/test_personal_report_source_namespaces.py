from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ClaimType


def test_case_research_and_facility_claim_types_cannot_blur():
    result = {"results": [], "decision_intelligence": {}}
    payload = build_personal_report_payload(
        result,
        case_claims=[{"claim_id": "case:x", "text": "Family stated X.", "provenance_ids": ["case:user:x"]}],
        research_claims=[{"claim_id": "research:x", "approved_text": "Institute finding X.", "provenance_ids": ["research:RI-X"]}],
        facility_claims=[{"claim_id": "facility:x", "text": "Verified facility X.", "verified": True, "provenance_ids": ["facility:registry:x"]}],
    )
    types = {c.claim_id: c.claim_type for c in payload.approved_claims}
    assert types["case:x"] is ClaimType.USER_INFORMATION
    assert types["research:x"] is ClaimType.RESEARCH_FINDING
    assert types["facility:x"] is ClaimType.VERIFIED_FACT
