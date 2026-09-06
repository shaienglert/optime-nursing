from app.services.personal_decision_report_builder import build_personal_report_payload


def test_case_claim_with_research_like_id_stays_user_information():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "research:fake", "text": "User-provided research claim.", "provenance_ids": ["case:user:x"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:fake")
    assert claim.claim_type.value == "USER_INFORMATION"
