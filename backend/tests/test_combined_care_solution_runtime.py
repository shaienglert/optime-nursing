from app.services.combined_care_solution_runtime import build_combined_care_solution


def _row(**extra):
    row = {
        "canonical_facility_id": "nv-test",
        "facility_name": "Test Community",
        "canonical_type": "INDEPENDENT_LIVING",
        "housing_modalities": ["INDEPENDENT_LIVING"],
        "agent_person_fit_evidence": [],
    }
    row.update(extra)
    return row


def test_outside_care_permission_without_agency_does_not_pass_must():
    row = _row(agent_person_fit_evidence=[{"payload": {"outside_care_allowed_verified": True}}])
    result = build_combined_care_solution(row, {}, "Needs bathing help for three months in a small home-like community")
    assert result["combined_must_coverage"] == "PENDING_VERIFICATION"
    assert result["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"


def test_verified_agency_plus_outside_permission_passes():
    row = _row(
        agent_person_fit_evidence=[{"payload": {"outside_care_allowed_verified": True}}],
        external_care_agency_match={
            "canonical_agency_id": "agency-1",
            "agency_name": "Verified Home Care",
            "verification_status": "VERIFIED",
            "service_area_match": True,
            "can_cover_required_services": True,
            "services": ["bathing", "dressing"],
        },
    )
    result = build_combined_care_solution(row, {}, "Needs bathing and dressing help temporarily")
    assert result["combined_must_coverage"] == "PASS"
    assert result["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY"


def test_in_house_adl_remains_valid_path():
    row = _row(canonical_type="ASSISTED_LIVING_RFG")
    result = build_combined_care_solution(row, {}, "Needs help bathing")
    assert result["combined_must_coverage"] == "PASS"
    assert result["delivery_model"] == "FACILITY_IN_HOUSE"


def test_verified_no_outside_care_is_fail_when_no_in_house_path():
    row = _row(agent_person_fit_evidence=[{"payload": {"outside_care_allowed_verified": False}}])
    result = build_combined_care_solution(row, {}, "Needs bathing help")
    assert result["combined_must_coverage"] == "FAIL"
    assert result["delivery_model"] == "NO_VALID_EXTERNAL_PATH"
