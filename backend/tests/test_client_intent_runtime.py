from __future__ import annotations

from app.services.client_intent_runtime import evaluate_candidate_intent


def _intent(*must_keys: str) -> dict:
    return {"must_haves": [{"key": key} for key in must_keys], "nice_to_haves": []}


def _row(canonical_type: str, **extra) -> dict:
    return {"canonical_type": canonical_type, "city": "LAS VEGAS", "state": "NV", **extra}


def test_skilled_nursing_auto_passes_adl_support_available():
    # Same regulatory logic already applied to ASSISTED_LIVING_RFG below: a licensed
    # skilled nursing facility cannot hold that license without providing ADL
    # assistance, so it must not sit in MUST_PENDING_VERIFICATION on this alone --
    # see facility_parameter_service.py's REGULATORY_VERIFIED adl_support evidence
    # for skilled nursing facilities, which this gate previously never consulted.
    fit = evaluate_candidate_intent(_row("SKILLED_NURSING"), _intent("ADL_SUPPORT_AVAILABLE"))
    assert fit["hard_gate"] == "PASS"
    assert "ADL_SUPPORT_AVAILABLE" in fit["must_pass"]
    assert "ADL_SUPPORT_AVAILABLE" not in fit["must_unknown"]


def test_assisted_living_rfg_still_auto_passes_adl_support_available():
    # Regression guard: the pre-existing RFG shortcut must keep working unchanged.
    fit = evaluate_candidate_intent(_row("ASSISTED_LIVING_RFG"), _intent("ADL_SUPPORT_AVAILABLE"))
    assert fit["hard_gate"] == "PASS"
    assert "ADL_SUPPORT_AVAILABLE" in fit["must_pass"]


def test_independent_living_does_not_auto_pass_adl_support_available():
    # Regression guard: an IL property must stay a housing classification, not an
    # implied care commitment, per the existing "never infer care for IL" rule.
    fit = evaluate_candidate_intent(_row("INDEPENDENT_LIVING"), _intent("ADL_SUPPORT_AVAILABLE"))
    assert fit["hard_gate"] == "PENDING_VERIFICATION"
    assert "ADL_SUPPORT_AVAILABLE" in fit["must_unknown"]


def test_independent_living_with_verified_agent_evidence_still_passes():
    # The agent-evidence fallback path must still resolve it for types with no
    # taxonomy shortcut, once real per-facility evidence exists.
    row = _row(
        "INDEPENDENT_LIVING",
        provider_housing_evidence={"evidence": {"adl_support_verified": True}},
    )
    fit = evaluate_candidate_intent(row, _intent("ADL_SUPPORT_AVAILABLE"))
    assert fit["hard_gate"] == "PASS"
    assert "ADL_SUPPORT_AVAILABLE" in fit["must_pass"]
