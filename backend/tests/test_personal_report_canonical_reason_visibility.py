from app.services.personal_decision_report_builder import build_personal_report_payload


def test_blocked_report_explains_canonical_blocker_without_inventing_recommendation():
    payload = build_personal_report_payload({
        "results": [],
        "decision_intelligence": {"human_intelligence": {"readiness_guardian": {"client_owned_blockers": [{"field": "budget"}]}}},
    })
    claim = next(c for c in payload.approved_claims if c.claim_id == "decision:canonical-reason")
    assert claim.approved_text == "material client-owned blockers remain unresolved"
    assert payload.canonical_decision["can_show_recommendations"] is False
