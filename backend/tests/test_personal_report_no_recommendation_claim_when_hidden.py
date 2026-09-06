from app.services.personal_decision_report_builder import build_personal_report_payload


def test_hidden_state_is_explicit_in_payload():
    result = {
        "results": [],
        "decision_intelligence": {"human_intelligence": {"decision_readiness": "NOT_READY", "readiness_guardian": {"client_owned_blockers": [{"field": "care_needs"}]}}},
    }
    payload = build_personal_report_payload(result)
    assert payload.canonical_decision["can_show_recommendations"] is False
    assert payload.canonical_decision["finality"] == "NONE"
