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
