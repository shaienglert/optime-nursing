from app.services.personal_decision_report_builder import build_personal_report_payload


def test_case_claim_without_user_provenance_is_dropped():
    result = {"results": [], "decision_intelligence": {}}
    payload = build_personal_report_payload(result, case_claims=[{"claim_id": "case:guess", "text": "The person probably prefers quiet.", "provenance_ids": []}])
    assert "case:guess" not in {c.claim_id for c in payload.approved_claims}
