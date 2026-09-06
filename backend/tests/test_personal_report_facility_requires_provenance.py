from app.services.personal_decision_report_builder import build_personal_report_payload


def test_verified_flag_without_provenance_is_not_enough():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        facility_claims=[{"claim_id": "facility:no-source", "text": "Claimed verified.", "verified": True, "provenance_ids": []}],
    )
    assert "facility:no-source" not in {c.claim_id for c in payload.approved_claims}
