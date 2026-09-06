import json
from pathlib import Path

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_example_fixture_generates_a_governed_report_payload():
    fixture = json.loads((Path(__file__).parent / "fixtures" / "personal_report_example.json").read_text())
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
        case_claims=fixture["case_claims"],
        research_claims=fixture["research_claims"],
        facility_claims=fixture["facility_claims"],
    )
    ids = [c.claim_id for c in payload.approved_claims]
    assert ids == [
        "decision:canonical-reason",
        "case:role",
        "case:priority",
        "research:transition-autonomy",
        "facility:night-staff",
    ]
    assert payload.canonical_decision["finality"] == "FINAL"
    assert payload.canonical_decision["can_show_recommendations"] is True
