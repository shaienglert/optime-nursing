from app.services.personal_decision_report_contract import ReportSection
from app.services.personal_decision_report_builder import (
    UserRole,
    build_personal_decision_report,
    derive_user_role,
    serialize_personal_report_payload,
)


def _ready_decision_result():
    canonical_state = {
        "phase": "PROVISIONAL_RECOMMENDATION",
        "finality": "PROVISIONAL_PENDING_PREFERENCE_VERIFICATION",
        "can_show_recommendations": True,
        "reason": "n/a",
    }
    decision_intelligence = {
        "canonical_decision_state": canonical_state,
        "decision_finality": "PROVISIONAL_PENDING_PREFERENCE_VERIFICATION",
        "strategy_universe": {"rank_one_strategy_ids": ["MEMORY_CARE"]},
    }
    row = {
        "canonical_facility_id": "NV-LIC-TEST-1",
        "facility_name": "Test Memory Care",
        "rank_position": 1,
        "match_band": "STRONG",
        "match_score": 80.0,
        "regulatory_history": {
            "latest_known_grade": "A",
            "source_url": "https://example.gov/inspection/NV-LIC-TEST-1",
        },
        "unknown_critical_needs": ["night_staffing"],
        "explanation": {
            "why_matches": ["Memory care is supported by verified evidence"],
            "concerns": [],
            "needs_verification": ["Current availability must be confirmed directly with the facility"],
        },
    }
    return {
        "patient_needs_profile": {
            "decision_intelligence": decision_intelligence,
            "needs": [
                {"parameter_id": "memory_care", "requirement_level": "HIGH", "need_text": "Memory care capability"},
                {"parameter_id": "adl_support", "requirement_level": "HIGH", "need_text": "Needs ADL support"},
                {"parameter_id": "languages", "requirement_level": "PREFERENCE", "need_text": "Spanish-speaking staff preferred"},
            ],
        },
        "decision_intelligence": decision_intelligence,
        "results": [row],
    }


def _blocked_decision_result():
    canonical_state = {
        "phase": "CLIENT_INPUT_REQUIRED",
        "finality": "NONE",
        "can_show_recommendations": False,
        "reason": "legacy payload does not contain enough governed state to advance safely",
    }
    decision_intelligence = {"canonical_decision_state": canonical_state}
    return {
        "patient_needs_profile": {"decision_intelligence": decision_intelligence, "needs": []},
        "decision_intelligence": decision_intelligence,
        "results": [],
    }


def test_derive_user_role_family_member():
    assert derive_user_role({"relationship": "Father"}) == UserRole.FAMILY_MEMBER


def test_derive_user_role_self():
    assert derive_user_role({"relationship": "Self"}) == UserRole.SELF


def test_derive_user_role_unset_is_other():
    assert derive_user_role({}) == UserRole.OTHER


def test_ready_case_produces_candidate_and_passes_contract():
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father", "assistanceLevel": "Needs help bathing", "budget": 5000},
        natural_language_query="anything",
        decision_result=_ready_decision_result(),
    )
    assert payload.report_ready is True
    assert len(payload.candidates) == 1
    assert payload.candidates[0].canonical_facility_id == "NV-LIC-TEST-1"
    # every claim actually used must trace to a section
    sections_used = {use.section for use in payload.claim_uses}
    assert ReportSection.WHY_THIS_PLACE in sections_used
    assert ReportSection.BEFORE_YOU_DECIDE in sections_used


def test_only_required_or_high_needs_enter_what_matters():
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father"},
        natural_language_query="",
        decision_result=_ready_decision_result(),
    )
    what_matters_texts = [u.rendered_text for u in payload.claim_uses if u.section == ReportSection.WHAT_MATTERS]
    assert "Memory care capability" in what_matters_texts
    assert "Needs ADL support" in what_matters_texts
    # PREFERENCE-level need must not appear -- "only factors that actually participated"
    assert "Spanish-speaking staff preferred" not in what_matters_texts


def test_blocked_case_has_no_candidates_and_still_passes_contract():
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father"},
        natural_language_query="",
        decision_result=_blocked_decision_result(),
    )
    assert payload.report_ready is False
    assert payload.candidates == ()
    pending = [u for u in payload.claim_uses if u.section == ReportSection.BEFORE_YOU_DECIDE]
    assert len(pending) == 1
    assert "governed state" in pending[0].rendered_text


def test_successful_transition_section_is_never_fabricated():
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father"},
        natural_language_query="",
        decision_result=_ready_decision_result(),
    )
    assert "SUCCESSFUL_TRANSITION" in payload.omitted_sections
    assert all(use.section != ReportSection.SUCCESSFUL_TRANSITION for use in payload.claim_uses)


def test_unverified_grade_is_not_rendered_as_verified_fact():
    result = _ready_decision_result()
    result["results"][0]["regulatory_history"] = {"latest_known_grade": "UNKNOWN"}
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father"},
        natural_language_query="",
        decision_result=result,
    )
    grade_claims = [c for c in payload.claims if c.claim_id.endswith(".latest_grade")]
    assert grade_claims == []


def test_serialize_groups_claims_by_section_and_is_json_safe():
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father", "budget": 5000},
        natural_language_query="",
        decision_result=_ready_decision_result(),
    )
    serialized = serialize_personal_report_payload(payload)

    assert serialized["user_role"] == "FAMILY_MEMBER"
    assert serialized["report_ready"] is True
    assert serialized["omitted_sections"] == ["SUCCESSFUL_TRANSITION"]

    situation = serialized["sections"]["YOUR_SITUATION"]
    assert any(row["text"].startswith("Monthly budget") for row in situation)
    for row in situation:
        assert row["claim_type"] == "USER_INFORMATION"
        assert row["provenance_ids"]

    assert len(serialized["candidates"]) == 1
    candidate = serialized["candidates"][0]
    assert candidate["canonical_facility_id"] == "NV-LIC-TEST-1"
    why_this_place = candidate["sections"]["WHY_THIS_PLACE"]
    assert any(row["claim_type"] == "VERIFIED_FACT" for row in why_this_place)
    assert any(row["claim_type"] == "ENGINE_CONCLUSION" for row in why_this_place)
    before_you_decide = candidate["sections"]["BEFORE_YOU_DECIDE"]
    assert all(row["claim_type"] == "UNKNOWN" for row in before_you_decide)

    import json

    json.dumps(serialized)  # must round-trip through JSON with no custom encoder


def test_serialize_blocked_case_has_no_candidates():
    payload = build_personal_decision_report(
        questionnaire_state={"relationship": "Father"},
        natural_language_query="",
        decision_result=_blocked_decision_result(),
    )
    serialized = serialize_personal_report_payload(payload)
    assert serialized["report_ready"] is False
    assert serialized["candidates"] == []
    assert serialized["sections"]["BEFORE_YOU_DECIDE"][0]["claim_type"] == "UNKNOWN"
