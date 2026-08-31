from unittest.mock import patch

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


def test_agent_reported_no_outside_care_alone_does_not_fail_must():
    # decision_research_worker.py stamps outside_care_allowed_verified=False by default
    # on every research record regardless of which dimension was actually requested, so
    # an agent payload's False here is frequently "never researched", not a confirmed
    # negative -- it must never alone hard-fail this MUST (see combined_care_solution_
    # runtime.py's outside_allowed_false, sourced only from the curated
    # facility_service_delivery_runtime.py registry, same policy as the ADL/MEDICATION/
    # REHAB/RECOVERY_TRANSITION gates in client_intent_runtime.py).
    row = _row(agent_person_fit_evidence=[{"payload": {"outside_care_allowed_verified": False}}])
    result = build_combined_care_solution(row, {}, "Needs bathing help")
    assert result["combined_must_coverage"] == "PENDING_VERIFICATION"
    assert result["delivery_model"] == "CARE_DELIVERY_UNKNOWN"


def test_curated_registry_no_outside_care_is_fail_when_no_in_house_path():
    row = _row(canonical_type="INDEPENDENT_LIVING")
    with patch(
        "app.services.combined_care_solution_runtime.get_facility_service_delivery_evidence",
        return_value={"personal_care_delivery": {"outside_care_allowed": False}},
    ):
        result = build_combined_care_solution(row, {}, "Needs bathing help")
    assert result["combined_must_coverage"] == "FAIL"
    assert result["delivery_model"] == "NO_VALID_EXTERNAL_PATH"
