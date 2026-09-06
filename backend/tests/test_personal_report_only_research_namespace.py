from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_prefix_is_mandatory_for_every_research_provenance():
    good = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:good", "approved_text": "Good.", "provenance_ids": ["research:RI-1"]}])
    bad = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:bad", "approved_text": "Bad.", "provenance_ids": ["RI-1"]}])
    assert "research:good" in {c.claim_id for c in good.approved_claims}
    assert "research:bad" not in {c.claim_id for c in bad.approved_claims}
