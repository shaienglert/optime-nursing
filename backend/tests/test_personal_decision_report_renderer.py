from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_renderer_emits_only_approved_byte_identical_claims():
    result = {
        "results": [{"client_intent_fit": {"hard_gate": "MUST_ELIGIBLE"}}],
        "must_eligible_count": 1,
        "must_pending_verification_count": 0,
        "decision_intelligence": {
            "human_intelligence": {"decision_readiness": "READY"},
            "facility_selection_pipeline": {
                "ai_ranking": {"status": "AI_RANKED"},
                "dynamic_preferences": {"preference_count": 0},
            },
        },
    }
    payload = build_personal_report_payload(
        result,
        case_claims=[{"claim_id": "case:role", "text": "You are helping a family member.", "provenance_ids": ["case:user_input:role"]}],
        research_claims=[{"claim_id": "research:r1", "approved_text": "Approved research sentence.", "provenance_ids": ["research:RI-1"]}],
        facility_claims=[{"claim_id": "facility:u1", "approved_text": "Night staffing has not been verified.", "unknown": True, "provenance_ids": ["facility:night:UNKNOWN"]}],
    )
    report = render_personal_report(payload)
    rendered = {c["claim_id"]: c["text"] for s in report["sections"] for c in s["claims"]}
    approved = {c.claim_id: c.approved_text for c in payload.approved_claims}
    assert rendered == approved
    assert report["decision"]["finality"] == payload.canonical_decision["finality"]
    assert report["report_version"] == "v1-closed-world"
