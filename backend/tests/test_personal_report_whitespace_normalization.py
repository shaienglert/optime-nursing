from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_only_trims_outer_whitespace():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "  Exact internal   spacing.  ", "provenance_ids": ["case:x"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "case:x")
    assert claim.approved_text == "Exact internal   spacing."
