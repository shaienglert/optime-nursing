from app.services.personal_decision_report_builder import build_personal_report_payload


def test_multiple_institute_sources_are_allowed_only_when_all_are_institute_scoped():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:multi", "approved_text": "Finding.", "provenance_ids": ["research:RI-1", "research:RI-2"]}])
    claim = next(c for c in payload.approved_claims if c.claim_id == "research:multi")
    assert claim.provenance_ids == ("research:RI-1", "research:RI-2")
