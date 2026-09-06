import pytest

from app.services.personal_decision_report_contract import (
    ApprovedReportClaim,
    ClaimType,
    ReportClaimUse,
    ReportContractViolation,
    ReportSection,
    enforce_report_contract,
    validate_report_contract,
)


def _claims():
    return [
        ApprovedReportClaim(
            claim_id="case:role",
            claim_type=ClaimType.USER_INFORMATION,
            approved_text="You are a family member helping with this decision.",
            provenance_ids=("case:user_role",),
            allowed_sections=(ReportSection.YOUR_ROLE,),
        ),
        ApprovedReportClaim(
            claim_id="research:transition-1",
            claim_type=ClaimType.RESEARCH_FINDING,
            approved_text="Preserving autonomy is relevant to this transition.",
            provenance_ids=("research:RI-TRANSITION-001",),
            allowed_sections=(ReportSection.SUCCESSFUL_TRANSITION,),
            confidence="HIGH",
        ),
        ApprovedReportClaim(
            claim_id="decision:why-1",
            claim_type=ClaimType.ENGINE_CONCLUSION,
            approved_text="The current recommendation remains provisional.",
            provenance_ids=("decision:canonical",),
            allowed_sections=(ReportSection.WHY_RECOMMENDATION,),
        ),
        ApprovedReportClaim(
            claim_id="unknown:night-staff",
            claim_type=ClaimType.UNKNOWN,
            approved_text="Night staffing has not been verified.",
            provenance_ids=("facility:night_staffing:UNKNOWN",),
            allowed_sections=(ReportSection.BEFORE_YOU_DECIDE,),
        ),
    ]


def _state():
    return {
        "phase": "PROVISIONAL_RECOMMENDATION",
        "finality": "PROVISIONAL",
        "can_show_recommendations": True,
    }


def test_valid_closed_world_report_passes():
    uses = [
        ReportClaimUse("case:role", ReportSection.YOUR_ROLE, "You are a family member helping with this decision."),
        ReportClaimUse("research:transition-1", ReportSection.SUCCESSFUL_TRANSITION, "Preserving autonomy is relevant to this transition."),
        ReportClaimUse("decision:why-1", ReportSection.WHY_RECOMMENDATION, "The current recommendation remains provisional."),
        ReportClaimUse("unknown:night-staff", ReportSection.BEFORE_YOU_DECIDE, "Night staffing has not been verified."),
    ]
    result = validate_report_contract(
        approved_claims=_claims(), claim_uses=uses, canonical_state=_state(),
        report_decision={"phase": "PROVISIONAL_RECOMMENDATION", "finality": "PROVISIONAL", "can_show_recommendations": True},
    )
    assert result.valid
    assert result.violations == ()


def test_unapproved_helpful_advice_is_blocked():
    result = validate_report_contract(
        approved_claims=_claims(),
        claim_uses=[ReportClaimUse("ai:helpful-advice", ReportSection.SUCCESSFUL_TRANSITION, "Visit twice before moving.")],
        canonical_state=_state(), report_decision={},
    )
    assert not result.valid
    assert any("outside the allowlist" in v for v in result.violations)


def test_paraphrase_that_upgrades_unknown_is_blocked():
    result = validate_report_contract(
        approved_claims=_claims(),
        claim_uses=[ReportClaimUse("unknown:night-staff", ReportSection.BEFORE_YOU_DECIDE, "24/7 night staff are available.")],
        canonical_state=_state(), report_decision={},
    )
    assert not result.valid
    assert any("altered" in v for v in result.violations)


def test_research_claim_without_research_institute_provenance_is_blocked():
    bad = [ApprovedReportClaim(
        claim_id="research:bad", claim_type=ClaimType.RESEARCH_FINDING,
        approved_text="A professional claim.", provenance_ids=("web:random",),
        allowed_sections=(ReportSection.SUCCESSFUL_TRANSITION,),
    )]
    result = validate_report_contract(approved_claims=bad, claim_uses=[], canonical_state=_state(), report_decision={})
    assert not result.valid
    assert any("Research Institute provenance" in v for v in result.violations)


def test_report_cannot_upgrade_provisional_to_final():
    result = validate_report_contract(
        approved_claims=_claims(), claim_uses=[], canonical_state=_state(),
        report_decision={"finality": "FINAL"},
    )
    assert not result.valid
    assert any("cannot override canonical finality" in v for v in result.violations)


def test_report_cannot_hide_canonical_visibility():
    result = validate_report_contract(
        approved_claims=_claims(), claim_uses=[], canonical_state=_state(),
        report_decision={"can_show_recommendations": False},
    )
    assert not result.valid


@pytest.mark.parametrize("escape", [
    {"research_performed": True},
    {"ranking_recalculated": True},
    {"resolved_unknowns": ["night_staffing"]},
])
def test_report_cannot_gain_research_ranking_or_unknown_authority(escape):
    result = validate_report_contract(
        approved_claims=_claims(), claim_uses=[], canonical_state=_state(), report_decision=escape,
    )
    assert not result.valid


def test_wrong_section_is_blocked():
    result = validate_report_contract(
        approved_claims=_claims(),
        claim_uses=[ReportClaimUse("research:transition-1", ReportSection.WHY_THIS_PLACE, "Preserving autonomy is relevant to this transition.")],
        canonical_state=_state(), report_decision={},
    )
    assert not result.valid
    assert any("unauthorized section" in v for v in result.violations)


def test_enforcer_fails_closed():
    with pytest.raises(ReportContractViolation):
        enforce_report_contract(
            approved_claims=_claims(), claim_uses=[], canonical_state=_state(),
            report_decision={"finality": "FINAL"},
        )
