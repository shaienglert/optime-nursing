from app.services.personal_decision_report_builder import build_personal_report_payload


def test_unknown_claim_without_provenance_is_omitted():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        facility_claims=[{"claim_id": "facility:u", "text": "Unknown.", "unknown": True, "provenance_ids": []}],
    )
    assert "facility:u" not in {c.claim_id for c in payload.approved_claims}
