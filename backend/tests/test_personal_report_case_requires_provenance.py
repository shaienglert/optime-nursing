from app.services.personal_decision_report_builder import build_personal_report_payload


def test_user_fact_without_provenance_is_not_rendered():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        case_claims=[{"claim_id": "case:no-source", "text": "Unsupported case statement.", "provenance_ids": []}],
    )
    assert "case:no-source" not in {c.claim_id for c in payload.approved_claims}
