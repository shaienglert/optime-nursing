from app.services.personal_decision_report_builder import build_personal_report_payload


def test_one_non_institute_source_rejects_entire_research_claim():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        research_claims=[{"claim_id": "research:mixed", "approved_text": "Mixed.", "provenance_ids": ["research:RI-1", "document:1"]}],
    )
    assert "research:mixed" not in {c.claim_id for c in payload.approved_claims}
