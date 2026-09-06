from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_claim_with_mixed_external_provenance_is_rejected():
    result = {"results": [], "decision_intelligence": {}}
    payload = build_personal_report_payload(result, research_claims=[{
        "claim_id": "research:mixed",
        "approved_text": "Claim partly based on an external source.",
        "provenance_ids": ["research:RI-1", "web:outside"],
    }])
    assert "research:mixed" not in {c.claim_id for c in payload.approved_claims}
