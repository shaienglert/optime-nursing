from app.services.personal_decision_report_builder import build_personal_report_payload


def test_same_text_keeps_distinct_source_classification():
    text = "Same sentence."
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": text, "provenance_ids": ["case:x"]}], research_claims=[{"claim_id": "research:x", "approved_text": text, "provenance_ids": ["research:RI-X"]}], facility_claims=[{"claim_id": "facility:x", "text": text, "verified": True, "provenance_ids": ["facility:x"]}])
    types = {c.claim_id: c.claim_type.value for c in payload.approved_claims}
    assert types["case:x"] == "USER_INFORMATION"
    assert types["research:x"] == "RESEARCH_FINDING"
    assert types["facility:x"] == "VERIFIED_FACT"
