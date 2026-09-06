from app.services.personal_decision_report_builder import build_personal_report_payload


def _result():
    return {
        "results": [{"client_intent_fit": {"hard_gate": "MUST_ELIGIBLE"}}],
        "must_eligible_count": 1,
        "must_pending_verification_count": 0,
        "decision_intelligence": {
            "human_intelligence": {"decision_readiness": "READY"},
            "facility_selection_pipeline": {"ai_ranking": {"status": "AI_RANKED"}, "dynamic_preferences": {"preference_count": 0}},
        },
    }


def test_document_or_web_content_cannot_enter_as_research():
    payload = build_personal_report_payload(_result(), research_claims=[
        {"claim_id": "doc:new-domain", "approved_text": "A document suggests a new research domain.", "provenance_ids": ["document:uploaded:1"]},
        {"claim_id": "web:new-domain", "approved_text": "A web result suggests a new research domain.", "provenance_ids": ["web:source:1"]},
    ])
    ids = {c.claim_id for c in payload.approved_claims}
    assert "doc:new-domain" not in ids
    assert "web:new-domain" not in ids


def test_only_preapproved_research_namespace_can_enter():
    payload = build_personal_report_payload(_result(), research_claims=[
        {"claim_id": "research:approved", "approved_text": "Institute-approved finding.", "provenance_ids": ["research:RI-DEFINED-TOPIC-1"]},
    ])
    assert "research:approved" in {c.claim_id for c in payload.approved_claims}
