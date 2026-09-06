from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_final_canonical_state_is_mirrored_not_created_by_report():
    result = {"results": [{"client_intent_fit": {"hard_gate": "MUST_ELIGIBLE"}}], "must_eligible_count": 1, "must_pending_verification_count": 0, "decision_intelligence": {"human_intelligence": {"decision_readiness": "READY"}, "facility_selection_pipeline": {"ai_ranking": {"status": "AI_RANKED"}, "dynamic_preferences": {"preference_count": 0}}}}
    report = render_personal_report(build_personal_report_payload(result))
    assert report["decision"] == {"phase": "FINAL_RECOMMENDATION", "finality": "FINAL", "can_show_recommendations": True}
