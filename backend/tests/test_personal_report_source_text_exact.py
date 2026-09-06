from app.services.personal_decision_report_builder import build_personal_report_payload


def test_approved_research_text_is_exact():
    exact = "Evidence is limited."
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": exact, "provenance_ids": ["research:RI-X"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:x")
    assert claim.approved_text == exact
