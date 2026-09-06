from app.services.personal_decision_report_builder import build_personal_report_payload


def test_decision_reason_is_canonical_not_freeform_input():
    result = {
        "results": [],
        "decision_intelligence": {
            "human_intelligence": {
                "decision_readiness": "NOT_READY",
                "readiness_guardian": {"client_owned_blockers": [{"field": "budget"}]},
            },
            "why_recommendation": "AI-authored alternative rationale must not be used",
        },
    }
    payload = build_personal_report_payload(result)
    claim = next(c for c in payload.approved_claims if c.claim_id == "decision:canonical-reason")
    assert claim.approved_text == "material client-owned blockers remain unresolved"
    assert "alternative rationale" not in claim.approved_text
