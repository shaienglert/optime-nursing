from app.services.personal_decision_report_builder import build_personal_report_payload


def test_claim_order_is_canonical_then_input_order():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[
        {"claim_id": "case:1", "text": "One.", "provenance_ids": ["case:1"]},
        {"claim_id": "case:2", "text": "Two.", "provenance_ids": ["case:2"]},
    ])
    assert [c.claim_id for c in payload.approved_claims][:3] == ["decision:canonical-reason", "case:1", "case:2"]
