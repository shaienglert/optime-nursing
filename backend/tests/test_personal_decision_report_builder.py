from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ClaimType, ReportSection


def _result():
    return {
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


def test_builds_from_canonical_authority_without_researching():
    payload = build_personal_report_payload(_result())
    assert payload.canonical_decision["phase"] == "FINAL_RECOMMENDATION"
    assert payload.canonical_decision["finality"] == "FINAL"
    decision = next(c for c in payload.approved_claims if c.claim_id == "decision:canonical-reason")
    assert decision.claim_type is ClaimType.ENGINE_CONCLUSION
    assert decision.provenance_ids == ("decision:canonical",)


def test_accepts_only_explicit_research_institute_claims():
    payload = build_personal_report_payload(
        _result(),
        research_claims=[
            {"claim_id": "research:good", "approved_text": "Approved transition finding.", "provenance_ids": ["research:RI-1"], "confidence": "HIGH"},
            {"claim_id": "research:web", "approved_text": "Interesting web advice.", "provenance_ids": ["web:random"]},
            {"claim_id": "research:none", "approved_text": "Unsupported advice.", "provenance_ids": []},
        ],
    )
    ids = {c.claim_id for c in payload.approved_claims}
    assert "research:good" in ids
    assert "research:web" not in ids
    assert "research:none" not in ids


def test_unverified_facility_assertion_is_not_renderable():
    payload = build_personal_report_payload(
        _result(),
        facility_claims=[
            {"claim_id": "facility:bad", "text": "24/7 nurse onsite.", "verified": False, "provenance_ids": ["facility:marketing"]},
            {"claim_id": "facility:good", "text": "Licensed for assisted living.", "verified": True, "provenance_ids": ["facility:license:123"]},
        ],
    )
    ids = {c.claim_id for c in payload.approved_claims}
    assert "facility:bad" not in ids
    assert "facility:good" in ids


def test_unknown_stays_unknown_and_goes_to_before_you_decide():
    payload = build_personal_report_payload(
        _result(),
        facility_claims=[{
            "claim_id": "facility:night-staff",
            "approved_text": "Night staffing has not been verified.",
            "unknown": True,
            "provenance_ids": ["facility:night_staffing:UNKNOWN"],
        }],
    )
    claim = next(c for c in payload.approved_claims if c.claim_id == "facility:night-staff")
    use = next(u for u in payload.claim_uses if u.claim_id == claim.claim_id)
    assert claim.claim_type is ClaimType.UNKNOWN
    assert use.section is ReportSection.BEFORE_YOU_DECIDE
    assert use.rendered_text == "Night staffing has not been verified."


def test_user_fact_is_not_upgraded_to_verified_fact():
    payload = build_personal_report_payload(
        _result(),
        case_claims=[{
            "claim_id": "case:mobility",
            "text": "Family reports that she walks independently.",
            "provenance_ids": ["case:user_input:mobility"],
        }],
    )
    claim = next(c for c in payload.approved_claims if c.claim_id == "case:mobility")
    assert claim.claim_type is ClaimType.USER_INFORMATION


def test_every_rendered_material_sentence_is_byte_identical_to_approved_claim():
    payload = build_personal_report_payload(
        _result(),
        research_claims=[{"claim_id": "research:r1", "approved_text": "Exact approved sentence.", "provenance_ids": ["research:RI-1"]}],
    )
    approved = {c.claim_id: c.approved_text for c in payload.approved_claims}
    assert all(use.rendered_text == approved[use.claim_id] for use in payload.claim_uses)
