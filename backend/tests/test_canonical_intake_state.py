from app.services.canonical_intake_state import canonicalize_intake_state


def test_husband_and_wife_preserve_spouse_identity_and_gender() -> None:
    assert canonicalize_intake_state({"relationship": "my husband"}) == {
        "relationship": "Spouse",
        "gender": "Male",
    }
    assert canonicalize_intake_state({"relationship": "Wife"}) == {
        "relationship": "Spouse",
        "gender": "Female",
    }


def test_explicit_gender_is_never_overwritten_by_relationship_normalization() -> None:
    state = canonicalize_intake_state({"relationship": "Spouse", "gender": "Non-binary"})
    assert state == {"relationship": "Spouse", "gender": "Nonbinary"}


def test_relationship_identifies_one_beneficiary_not_a_couple() -> None:
    assert canonicalize_intake_state({"relationship": "husband"})["relationship"] == "Spouse"
    assert canonicalize_intake_state({"relationship": "couple"})["relationship"] == "Couple"


def test_canonicalization_is_idempotent_and_does_not_mutate_input() -> None:
    original = {"relationship": "Father", "medicalCareProfile": {"needs": []}}
    once = canonicalize_intake_state(original)
    twice = canonicalize_intake_state(once)
    assert once == twice
    assert original["relationship"] == "Father"


import pytest


@pytest.mark.parametrize(
    "written, expected",
    [
        ("7000", 7000),
        ("$7,000", 7000),
        ("7,000", 7000),
        ("$7000/mo", 7000),
        ("7000 per month", 7000),
        ("7k", 7000),
        ("6500.50", 6500.5),
    ],
)
def test_monthly_budget_written_as_text_is_one_number_for_every_layer(written, expected) -> None:
    assert canonicalize_intake_state({"budget": written})["budget"] == expected


@pytest.mark.parametrize("value", [7000, 7000.0, 0, None, True])
def test_numeric_budget_is_left_exactly_as_given(value) -> None:
    assert canonicalize_intake_state({"budget": value})["budget"] == value


@pytest.mark.parametrize("written", ["10 miles", "seven thousand", "", "about 7000 or 8000", "-5"])
def test_budget_text_that_is_not_one_unambiguous_amount_is_not_guessed(written) -> None:
    # Unknown stays unknown: no distance is read as money and no amount is invented.
    assert canonicalize_intake_state({"budget": written})["budget"] == written


def test_budget_normalization_is_idempotent() -> None:
    once = canonicalize_intake_state({"budget": "$7,000"})
    assert canonicalize_intake_state(once) == once
