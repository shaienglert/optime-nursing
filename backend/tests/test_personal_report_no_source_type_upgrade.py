from app.services.personal_decision_report_builder import build_personal_report_payload


def test_case_input_cannot_self_declare_verified_type():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "User says verified.", "provenance_ids": ["case:x"], "claim_type": "VERIFIED_FACT"}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "case:x")
    assert claim.claim_type.value == "USER_INFORMATION"
