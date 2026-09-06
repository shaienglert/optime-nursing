from app.services.personal_decision_report_builder import build_personal_report_payload


def test_engine_conclusion_has_only_canonical_decision_provenance():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    claim = next(c for c in payload.approved_claims if c.claim_id == "decision:canonical-reason")
    assert claim.provenance_ids == ("decision:canonical",)
