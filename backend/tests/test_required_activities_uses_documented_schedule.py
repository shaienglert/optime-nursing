from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent


def _intent():
    state = {"humanIntelligenceV2": {"socialProfile": {"hobbyParticipation": ["Music"], "activityRequirementLevel": "Requirement"}}}
    return build_client_intent(state, "", {}, state["humanIntelligenceV2"])


def _fit(activities, schedule):
    row = {"verified_capabilities": {"activities": activities}, "pilot_service_evidence": {"activity_schedule": schedule}}
    return evaluate_candidate_intent(row, _intent())


def test_documented_schedule_naming_the_activity_passes():
    fit = _fit("YES", "Daily organized music, classes and social activities")
    assert "REQUIRED_ACTIVITIES" in fit["must_pass"]


def test_activity_program_without_the_named_activity_is_unknown_not_a_verified_fail():
    fit = _fit("YES", "Weekly bingo")
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_fail"]


def test_verified_no_activities_still_fails():
    fit = _fit("NO", "")
    assert "REQUIRED_ACTIVITIES" in fit["must_fail"]
