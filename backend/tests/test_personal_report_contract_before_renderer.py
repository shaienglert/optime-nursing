from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_returns_governed_payload_after_contract_enforcement():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    assert payload.approved_claims
    assert payload.claim_uses
