from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_input_is_always_research_finding():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"], "claim_type": "VERIFIED_FACT"}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:x")
    assert claim.claim_type.value == "RESEARCH_FINDING"
