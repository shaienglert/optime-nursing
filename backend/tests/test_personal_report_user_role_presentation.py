from app.services.personal_decision_report_builder import build_personal_report_payload


def test_user_role_claim_does_not_change_canonical_decision():
    result = {"results": [], "decision_intelligence": {}}
    a = build_personal_report_payload(result)
    b = build_personal_report_payload(result, case_claims=[{"claim_id": "case:role", "text": "You are the person's daughter.", "provenance_ids": ["case:user:role"], "allowed_sections": ["YOUR_ROLE"]}])
    assert a.canonical_decision == b.canonical_decision
