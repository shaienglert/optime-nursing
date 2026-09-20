from __future__ import annotations

from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key
from app.services.living_strategy_runtime import build_living_strategy_context


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


def test_memory_need_becomes_an_explicit_client_intent_must():
    intent = build_client_intent(
        {},
        "My mother has Alzheimer's and wanders at night. She needs secure memory care.",
        {"signals": {"memory_care_needed": True}, "household": {}},
        {},
    )
    keys = {item["key"] for item in intent["must_haves"]}
    assert "SECURE_MEMORY_CARE_CONFIRMED" in keys


def test_only_officially_confirmed_memory_care_passes_memory_must():
    confirmed = evaluate_candidate_intent(
        _row("ASSISTED_LIVING_RFG", memory_care_classification="CONFIRMED"),
        _intent("SECURE_MEMORY_CARE_CONFIRMED"),
    )
    independent = evaluate_candidate_intent(
        _row("INDEPENDENT_LIVING", memory_care_classification="UNKNOWN"),
        _intent("SECURE_MEMORY_CARE_CONFIRMED"),
    )
    assert confirmed["hard_gate"] == "PASS"
    assert "SECURE_MEMORY_CARE_CONFIRMED" in confirmed["must_pass"]
    assert independent["hard_gate"] == "PENDING_VERIFICATION"
    assert "SECURE_MEMORY_CARE_CONFIRMED" in independent["must_unknown"]


def _must_keys_for_story(story: str) -> set[str]:
    strategy = build_living_strategy_context({}, story)
    intent = build_client_intent({}, story, strategy, {})
    return {item["key"] for item in intent["must_haves"]}


def test_dialysis_launch_story_preserves_valley_and_adl_musts():
    keys = _must_keys_for_story(
        "My 81-year-old father needs assistance with daily activities and transportation "
        "to dialysis three times a week. He needs medication support, lives near Henderson, "
        "and has a $7,500 monthly budget."
    )
    assert {"LICENSE_CURRENTLY_VALID", "LAS_VEGAS", "ADL_SUPPORT_AVAILABLE", "MEDICATION_SUPPORT_AVAILABLE"} <= keys


def test_hospice_launch_story_preserves_adl_must():
    keys = _must_keys_for_story(
        "My mother is 88 and needs substantial daily assistance and medication management. "
        "Her doctor is discussing hospice. We need a calm Las Vegas Valley community that "
        "can coordinate with hospice and keep family closely involved. Budget is $9,000 monthly."
    )
    assert {"LICENSE_CURRENTLY_VALID", "LAS_VEGAS", "ADL_SUPPORT_AVAILABLE", "MEDICATION_SUPPORT_AVAILABLE"} <= keys


def test_spanish_launch_story_preserves_adl_must():
    keys = _must_keys_for_story(
        "My 80-year-old father speaks mainly Spanish. He needs light daily assistance and "
        "medication reminders, wants frequent family visits and an active social setting in "
        "the Las Vegas Valley, with a budget of $6,000 per month."
    )
    assert {"LICENSE_CURRENTLY_VALID", "LAS_VEGAS", "ADL_SUPPORT_AVAILABLE", "MEDICATION_SUPPORT_AVAILABLE"} <= keys


def test_future_care_preference_becomes_explicit_continuum_nice_to_have():
    intent = build_client_intent(
        {
            "humanIntelligenceV2": {
                "futureCareProfile": {"avoidFutureMovesPreference": "Important"},
            }
        },
        "We want to avoid another move as care needs increase.",
        {"signals": {}, "household": {}},
        {},
    )

    keys = {item["key"] for item in intent["nice_to_haves"]}
    assert "CONTINUUM_OF_CARE" in keys


def test_continuing_care_matches_continuum_preference_and_active_adult_does_not():
    intent = {"must_haves": [], "nice_to_haves": [{"key": "CONTINUUM_OF_CARE"}]}

    continuing_care = evaluate_candidate_intent(
        _row("ASSISTED_LIVING_RFG", synthetic_archetype="CONTINUING_CARE"),
        intent,
    )
    active_adult = evaluate_candidate_intent(
        _row("INDEPENDENT_LIVING", synthetic_archetype="ACTIVE_ADULT"),
        intent,
    )

    assert "CONTINUUM_OF_CARE" in continuing_care["nice_match"]
    assert "CONTINUUM_OF_CARE" in active_adult["nice_mismatch"]


def test_explicit_continuum_match_ranks_above_generic_active_adult_fit():
    intent = {"must_haves": [], "nice_to_haves": [{"key": "CONTINUUM_OF_CARE"}]}
    continuing_care = _row(
        "ASSISTED_LIVING_RFG",
        synthetic_archetype="CONTINUING_CARE",
        care_setting_fit={"status": "POSSIBLE_FIT"},
    )
    active_adult = _row(
        "INDEPENDENT_LIVING",
        synthetic_archetype="ACTIVE_ADULT_55_PLUS",
        care_setting_fit={"status": "PRIMARY_FIT"},
    )
    continuing_care["client_intent_fit"] = evaluate_candidate_intent(continuing_care, intent)
    active_adult["client_intent_fit"] = evaluate_candidate_intent(active_adult, intent)

    assert intent_rank_key(continuing_care) < intent_rank_key(active_adult)
