from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_id_without_approved_text_is_not_written_by_report_layer():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        research_claims=[{"claim_id": "research:no-text", "provenance_ids": ["research:RI-1"]}],
    )
    assert "research:no-text" not in {c.claim_id for c in payload.approved_claims}
