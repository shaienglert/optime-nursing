from app.services.personal_decision_report_builder import build_personal_report_payload


def test_external_source_cannot_fallback_into_research_claim():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        research_claims=[{"claim_id": "outside", "approved_text": "Outside finding.", "provenance_ids": ["document:1"]}],
    )
    assert "outside" not in {c.claim_id for c in payload.approved_claims}
