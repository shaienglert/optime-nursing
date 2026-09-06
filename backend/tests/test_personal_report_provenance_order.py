from app.services.personal_decision_report_builder import build_personal_report_payload


def test_provenance_order_is_not_reweighted_by_report_layer():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:second", "case:first"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "case:x")
    assert claim.provenance_ids == ("case:second", "case:first")
