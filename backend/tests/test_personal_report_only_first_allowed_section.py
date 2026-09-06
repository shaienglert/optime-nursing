from app.services.personal_decision_report_builder import build_personal_report_payload


def test_renderer_use_selects_first_explicit_allowed_section_without_reasoning():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "Fact.", "provenance_ids": ["case:x"], "allowed_sections": ["YOUR_ROLE", "YOUR_SITUATION"]}])
    use = next(u for u in payload.claim_uses if u.claim_id == "case:x")
    assert use.section.value == "YOUR_ROLE"
