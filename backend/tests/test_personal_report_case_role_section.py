from app.services.personal_decision_report_builder import build_personal_report_payload


def test_explicit_role_claim_uses_role_section_only_when_upstream_assigns_it():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:role", "text": "You are the son.", "provenance_ids": ["case:role"], "allowed_sections": ["YOUR_ROLE"]}])
    use = next(u for u in payload.claim_uses if u.claim_id == "case:role")
    assert use.section.value == "YOUR_ROLE"
