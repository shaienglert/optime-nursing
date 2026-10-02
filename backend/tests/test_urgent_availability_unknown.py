from app.services.decision_engine_core import build_patient_needs_profile, _eligibility_from_needs, _score_result


def profile():
    return build_patient_needs_profile({"assistanceLevel": "Fully independent", "memoryStatus": "Mild concerns",
        "budget": 5000, "moveTiming": "Within 30 days"})


def test_urgent_move_with_unknown_openings_does_not_block_independent_care_fit():
    result = _eligibility_from_needs(profile()["needs"], {"current_availability": {"raw_value": "UNKNOWN"}})
    assert result["eligibility_status"] == "ELIGIBLE"
    assert not result["unknown_critical_needs"]
    assert any(n["parameter_id"] == "current_availability" and n["status"] == "UNKNOWN" for n in result["unknown_preferences"])
    assert not any(n["parameter_id"] == "current_availability" for n in result["matched_needs"])


def test_missing_and_unknown_availability_have_identical_eligibility_and_score():
    needs = profile()["needs"]
    absent = _eligibility_from_needs(needs, {})
    unknown = _eligibility_from_needs(needs, {"current_availability": {"raw_value": "UNKNOWN"}})
    assert absent["eligibility_status"] == unknown["eligibility_status"] == "ELIGIBLE"
    assert _score_result(needs, absent) == _score_result(needs, unknown)


def test_verified_no_opening_still_remains_a_known_gap():
    result = _eligibility_from_needs(profile()["needs"], {"current_availability": {"raw_value": "NO", "source": "Direct confirmation"}})
    assert result["eligibility_status"] == "INELIGIBLE"
    assert any(n["parameter_id"] == "current_availability" for n in result["unmet_verified_needs"])


def test_unknown_clinical_must_is_not_relaxed():
    needs = profile()["needs"] + [{"parameter_id": "dialysis_arrangements", "requirement_level": "REQUIRED", "desired_value": "YES", "acceptable_values": ["YES"]}]
    result = _eligibility_from_needs(needs, {"current_availability": {"raw_value": "UNKNOWN"}})
    assert result["eligibility_status"] == "INSUFFICIENT_EVIDENCE"
    assert [n["parameter_id"] for n in result["unknown_critical_needs"]] == ["dialysis_arrangements"]
