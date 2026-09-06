from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_confidence_is_not_normalized_or_upgraded():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"], "confidence": "limited-evidence"}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:x")
    assert claim.confidence == "limited-evidence"
