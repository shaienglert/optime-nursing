from app.services.personal_decision_report_builder import build_personal_report_payload


def test_approved_research_defaults_to_transition_section():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"]}])
    use = next(u for u in payload.claim_uses if u.claim_id == "research:x")
    assert use.section.value == "SUCCESSFUL_TRANSITION"
