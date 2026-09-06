from app.services.personal_decision_report_builder import build_personal_report_payload


def test_empty_external_inputs_produce_only_canonical_claim():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    assert [c.claim_id for c in payload.approved_claims] == ["decision:canonical-reason"]
