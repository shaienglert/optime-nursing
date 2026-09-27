from app.services.decision_engine_core import build_patient_needs_profile


def _need_ids(story: str) -> set[str]:
    return {item["parameter_id"] for item in build_patient_needs_profile({}, story)["needs"]}


def test_care_acronym_inside_unrelated_word_does_not_create_adl_need():
    assert "adl_support" not in _need_ids("Sadly, she wants a place near family.")


def test_plural_care_word_still_creates_medication_need():
    assert "medication_support" in _need_ids("She needs help with medications.")


def test_nursing_inside_unrelated_word_does_not_create_nursing_need():
    assert "nursing_24_7" not in _need_ids("She was unnursing an old habit.")


def test_independent_partner_does_not_erase_other_persons_care_needs():
    ids = _need_ids(
        "Mother is fully independent. Father needs help bathing and needs medication support."
    )
    assert {"adl_support", "medication_support"} <= ids


def test_independence_and_denied_care_do_not_invent_need():
    ids = _need_ids(
        "Mother is fully independent and does not need help bathing or medications."
    )
    assert "adl_support" not in ids
    assert "medication_support" not in ids


def test_independent_partner_does_not_erase_bed_transfer_need():
    assert "transfer_assistance" in _need_ids(
        "Mother is fully independent. Father needs help getting out of bed."
    )


def test_denied_bed_transfer_does_not_create_transfer_need():
    assert "transfer_assistance" not in _need_ids(
        "Mother is fully independent and does not need help getting out of bed."
    )


def test_a_lift_can_be_an_elevator():
    # "lift" alone is the British word for an elevator, so it must not ask for hoist transfers.
    assert "transfer_assistance" not in _need_ids(
        "The building must have a lift, she cannot use stairs."
    )


def test_a_hoist_always_names_itself():
    for story in (
        "She needs a mechanical lift to get out of bed.",
        "Staff use a hoyer lift for her.",
        "She needs lift assist for every transfer.",
    ):
        assert "transfer_assistance" in _need_ids(story), story
