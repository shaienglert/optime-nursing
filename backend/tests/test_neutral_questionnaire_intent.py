"""Client controls must not create provider obligations or a preference advantage."""
from copy import deepcopy

import pytest

from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent, intent_rank_key


NEUTRAL = ["No", "None", "No preference", "Not important", "Not required", "Not needed", "Not sure", "Unknown"]
CONTINUITY_PATHS = [
    "futureCarePreference",
    "humanIntelligenceV2.futureCareProfile.avoidFutureMovesPreference",
    "humanIntelligenceV2.futureCareProfile.continuumOfCarePreference",
]


def state_at(path, value):
    state = {}
    target = state
    parts = path.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value
    return state


def intent(state, query=""):
    return build_client_intent(state, query, {"signals": {}, "household": {}}, {}, care_delivery_signals={})


def keys(result):
    return {item["key"] for kind in ("must_haves", "nice_to_haves") for item in result[kind]}


@pytest.mark.parametrize("path", CONTINUITY_PATHS)
@pytest.mark.parametrize("value", NEUTRAL + ["Not preferred", "Continuum not requested", "Not very important"])
def test_neutral_or_unrecognized_continuity_answer_creates_no_preference(path, value):
    result = intent(state_at(path, value), f"Future continuum of care: {value}")
    assert keys(result) == {"LICENSE_CURRENTLY_VALID"}


@pytest.mark.parametrize("path", CONTINUITY_PATHS)
@pytest.mark.parametrize("value,key", [
    ("Required", "CONTINUUM_OF_CARE_REQUIRED"),
    ("Requirement", "CONTINUUM_OF_CARE_REQUIRED"),
    ("Preferred", "CONTINUUM_OF_CARE"),
    ("Important", "CONTINUUM_OF_CARE"),
    ("  preferred  ", "CONTINUUM_OF_CARE"),
])
def test_explicit_positive_continuity_controls_retain_their_meaning(path, value, key):
    assert keys(intent(state_at(path, value))) == {"LICENSE_CURRENTLY_VALID", key}


def test_absent_continuity_control_preserves_existing_narrative_fallback():
    assert "CONTINUUM_OF_CARE" in keys(intent({}, "We want a continuing care community"))


@pytest.mark.parametrize("value", NEUTRAL)
def test_neutral_language_value_is_not_a_required_language(value):
    state = {"humanIntelligenceV2": {"languageProfile": {"preferredSpokenLanguage": value, "languageNeedScope": "Requirement"}}}
    assert keys(intent(state)) == {"LICENSE_CURRENTLY_VALID"}


@pytest.mark.parametrize("value", NEUTRAL)
def test_neutral_activity_value_is_not_a_required_activity(value):
    state = {"humanIntelligenceV2": {"socialProfile": {"hobbyParticipation": [value, "A resident's custom activity"], "activityRequirementLevel": "Requirement"}}}
    result = intent(state)
    activity = next(item for item in result["must_haves"] if item["key"] == "REQUIRED_ACTIVITIES")
    assert activity["value"] == ["A resident's custom activity"]


@pytest.mark.parametrize("value", NEUTRAL)
def test_neutral_kosher_control_does_not_recreate_a_mention_as_preference(value):
    state = {"humanIntelligenceV2": {"foodProfile": {"dietaryPreferences": ["Kosher"]}, "culturalProfile": {"kosherRequirements": value}}}
    assert keys(intent(state, f"Kosher: {value}")) == {"LICENSE_CURRENTLY_VALID"}


def test_not_kosher_is_not_the_kosher_questionnaire_option():
    state = {"humanIntelligenceV2": {"foodProfile": {"dietaryPreferences": ["Not kosher"]}}}
    assert keys(intent(state)) == {"LICENSE_CURRENTLY_VALID"}


@pytest.mark.parametrize("value", NEUTRAL)
def test_neutral_environment_control_is_not_an_environment_preference(value):
    result = build_client_intent({}, "", {}, {"signals": {"community_size_preference": {"value": value}}}, care_delivery_signals={})
    assert keys(result) == {"LICENSE_CURRENTLY_VALID"}


def test_declining_continuity_does_not_penalize_independent_community():
    result = intent({"futureCarePreference": "Not important"}, "Continuum of care: Not important")
    common = {"city": "LAS VEGAS", "state": "NV", "canonical_type": "INDEPENDENT_LIVING", "license_status": "Active", "expiration_date": "12/31/2099", "synthetic_pilot": True}
    independent = {**deepcopy(common), "synthetic_archetype": "INDEPENDENT_LIVING"}
    continuing = {**deepcopy(common), "synthetic_archetype": "CONTINUING_CARE"}
    for row in (independent, continuing):
        row["client_intent_fit"] = evaluate_candidate_intent(row, result)
        assert not row["client_intent_fit"]["nice_mismatch"]
        assert not row["client_intent_fit"]["nice_match"]
    assert intent_rank_key(independent) == intent_rank_key(continuing)


def test_legacy_explicit_continuum_label_retains_preference():
    assert "CONTINUUM_OF_CARE" in keys(intent({"futureCarePreference": "Full continuum of care on one campus"}))


def test_unknown_positive_control_is_observable_without_inventing_intent():
    result = intent({"futureCarePreference": "Somewhat important"})
    assert "CONTINUUM_OF_CARE" not in keys(result)
    assert result["unrecognized_controls"] == [{"answer_path": "futureCarePreference",
        "answer": "Somewhat important", "status": "UNRECOGNIZED_CONTROL_VALUE"}]
