from app.services.personal_decision_report_builder import build_personal_report_payload


def test_empty_claim_is_omitted_not_completed():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        case_claims=[{"claim_id": "case:empty", "text": "", "provenance_ids": ["case:user:empty"]}],
    )
    assert "case:empty" not in {c.claim_id for c in payload.approved_claims}
