"""Owner decision 6: quiet/social-pace preferences are checked against relevant evidence;
missing evidence is shown as uncertainty, never as a match or a mismatch."""
import pytest

from app.services.client_intent_runtime import build_client_intent, evaluate_candidate_intent
from app.services.living_strategy_runtime import build_living_strategy_context


def _intent(state):
    return build_client_intent(state, "", build_living_strategy_context(state, ""), {})


def _social(value):
    return {"humanIntelligenceV2": {"socialProfile": {"socialInteractionFrequency": value}}}


@pytest.mark.parametrize("value", ["Daily", "Several times weekly", "Weekly", "Occasionally", "Very little"])
def test_stated_social_pace_is_unknown_without_evidence(value):
    intent = _intent(_social(value))
    assert "SOCIAL_FREQUENCY_MATCH" in {row["key"] for row in intent["nice_to_haves"]}
    fit = evaluate_candidate_intent({"canonical_type": "ASSISTED_LIVING"}, intent)
    assert "SOCIAL_FREQUENCY_MATCH" in fit["nice_unknown"]
    assert "SOCIAL_FREQUENCY_MATCH" not in fit["nice_match"] + fit["nice_mismatch"]


@pytest.mark.parametrize("value", ["", "No preference", "Not sure"])
def test_neutral_social_pace_creates_no_preference(value):
    assert "SOCIAL_FREQUENCY_MATCH" not in {row["key"] for row in _intent(_social(value))["nice_to_haves"]}


def test_quiet_community_style_stays_unknown_not_scored_as_a_size():
    state = {"humanIntelligenceV2": {"personalityProfile": {"communitySizePreference": "Quiet"}}}
    from app.services.human_intelligence_runtime import _community_size_preference
    assert _community_size_preference(state)["value"] == "UNKNOWN"
