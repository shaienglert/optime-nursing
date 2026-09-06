from __future__ import annotations

from app.services.living_strategy_runtime import build_living_strategy_context


def _household_type(query: str, relationship: str = "") -> str:
    context = build_living_strategy_context({"relationship": relationship}, query)
    return context["household"]["type"]


def test_idiomatic_couple_of_things_is_not_a_relationship_signal():
    # Reproduced in production: this idiomatic phrasing spuriously triggered
    # COUPLE_CORESIDENCE and a CCRC entrance-fee guardian question for a
    # single-person search.
    assert _household_type("I have a couple of specific things to ask about amenities") == "SINGLE_OR_UNKNOWN"


def test_negated_spouse_is_not_a_relationship_signal():
    # A naive substring match on "spouse" fires even when the sentence explicitly
    # says there isn't one.
    assert _household_type("She is widowed and has no spouse living with her") == "SINGLE_OR_UNKNOWN"
    assert _household_type("He lives without a wife or family nearby") == "SINGLE_OR_UNKNOWN"


def test_genuine_couple_mention_is_still_detected():
    assert _household_type("My husband and I are looking together for a community") == "COUPLE"
    assert _household_type("We are a couple searching for assisted living") == "COUPLE"
    assert _household_type("Looking for both parents to live in the same community") == "COUPLE"


def test_relationship_field_still_forces_couple():
    assert _household_type("Looking for senior housing", relationship="spouse") == "COUPLE"
