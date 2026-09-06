from app.services.personal_decision_report_builder import build_personal_report_payload


def test_only_automatic_claim_is_canonical_engine_conclusion():
    claim = build_personal_report_payload({"results": [], "decision_intelligence": {}}).approved_claims[0]
    assert claim.claim_id == "decision:canonical-reason"
    assert claim.claim_type.value == "ENGINE_CONCLUSION"
    assert claim.provenance_ids == ("decision:canonical",)
