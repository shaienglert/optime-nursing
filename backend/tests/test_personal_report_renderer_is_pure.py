from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_does_not_mutate_payload():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    before = (payload.canonical_decision.copy(), payload.approved_claims, payload.claim_uses)
    render_personal_report(payload)
    assert (payload.canonical_decision, payload.approved_claims, payload.claim_uses) == before
