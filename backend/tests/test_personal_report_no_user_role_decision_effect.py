from app.services.personal_decision_report_builder import build_personal_report_payload


def test_different_user_roles_produce_same_decision_state():
    result = {"results": [], "decision_intelligence": {}}
    child = build_personal_report_payload(result, case_claims=[{"claim_id": "case:role", "text": "You are the child.", "provenance_ids": ["case:role"], "allowed_sections": ["YOUR_ROLE"]}])
    spouse = build_personal_report_payload(result, case_claims=[{"claim_id": "case:role", "text": "You are the spouse.", "provenance_ids": ["case:role"], "allowed_sections": ["YOUR_ROLE"]}])
    assert child.canonical_decision == spouse.canonical_decision
