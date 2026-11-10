from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent


def _intent(activities=None):
    state = {"humanIntelligenceV2": {"socialProfile": {
        "hobbyParticipation": ["Music"] if activities is None else activities,
        "activityRequirementLevel": "Requirement",
    }}}
    return build_client_intent(state, "", {}, state["humanIntelligenceV2"])


def _fit(activities, schedule, wanted=None):
    row = {
        "canonical_facility_id": "PILOT-NV-027",
        "synthetic_pilot": True,
        "verified_capabilities": {"activities": activities},
        "pilot_service_evidence": {
            "activity_schedule": schedule,
            "canonical_facility_id": "PILOT-NV-027",
            "source": "SYNTHETIC_PILOT_SERVICE_FIXTURE",
            "verification_status": "VERIFIED",
            "provenance": {"synthetic_pilot": True, "not_real_world_evidence": True},
        },
    }
    return evaluate_candidate_intent(row, _intent(wanted))


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


def test_multiple_required_activities_all_documented_pass():
    fit = _fit("YES", "Music groups and painting classes", ["Music", "Painting"])
    assert "REQUIRED_ACTIVITIES" in fit["must_pass"]


def test_multiple_required_activities_missing_one_stays_unknown():
    fit = _fit("YES", "Music groups and exercise", ["Music", "Painting"])
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]


def test_missing_capability_even_with_schedule_is_not_verified_pass():
    fit = _fit(None, "Daily organized music")
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_pass"]


def test_explicit_no_overrides_conflicting_schedule():
    fit = _fit("NO", "Daily organized music")
    assert "REQUIRED_ACTIVITIES" in fit["must_fail"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_pass"]


def test_missing_schedule_stays_unknown():
    fit = _fit("YES", "")
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]


def test_substring_is_not_activity_evidence():
    fit = _fit("YES", "Weekly parties", ["Art"])
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]


def test_empty_activities_do_not_create_vacuous_verified_pass():
    fit = _fit("YES", "Music groups", [])
    assert "REQUIRED_ACTIVITIES" not in fit["must_pass"]


def test_unrecognized_capability_is_unknown_not_verified_failure():
    fit = _fit("SOMETIMES", "Daily music")
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_fail"]


def test_unverified_pilot_schedule_cannot_prove_required_activity():
    row = {
        "canonical_facility_id": "PILOT-NV-027",
        "synthetic_pilot": True,
        "verified_capabilities": {"activities": "YES"},
        "pilot_service_evidence": {
            "activity_schedule": "Daily music",
            "canonical_facility_id": "PILOT-NV-027",
            "source": "SYNTHETIC_PILOT_SERVICE_FIXTURE",
            "verification_status": "UNVERIFIED",
            "provenance": {"synthetic_pilot": True, "not_real_world_evidence": True},
        },
    }
    fit = evaluate_candidate_intent(row, _intent())
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_pass"]


def test_pilot_schedule_with_wrong_facility_identity_is_not_proof():
    row = {
        "canonical_facility_id": "PILOT-NV-028",
        "synthetic_pilot": True,
        "verified_capabilities": {"activities": "YES"},
        "pilot_service_evidence": {
            "activity_schedule": "Daily music",
            "canonical_facility_id": "PILOT-NV-027",
            "source": "SYNTHETIC_PILOT_SERVICE_FIXTURE",
            "verification_status": "VERIFIED",
            "provenance": {"synthetic_pilot": True, "not_real_world_evidence": True},
        },
    }
    fit = evaluate_candidate_intent(row, _intent())
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_pass"]


def test_real_facility_cannot_use_synthetic_schedule_as_must_proof():
    row = {
        "canonical_facility_id": "PILOT-NV-027",
        "synthetic_pilot": False,
        "verified_capabilities": {"activities": "YES"},
        "pilot_service_evidence": {
            "activity_schedule": "Daily music",
            "canonical_facility_id": "PILOT-NV-027",
            "source": "SYNTHETIC_PILOT_SERVICE_FIXTURE",
            "verification_status": "VERIFIED",
            "provenance": {"synthetic_pilot": True, "not_real_world_evidence": True},
        },
    }
    fit = evaluate_candidate_intent(row, _intent())
    assert "REQUIRED_ACTIVITIES" in fit["must_unknown"]
    assert "REQUIRED_ACTIVITIES" not in fit["must_pass"]
