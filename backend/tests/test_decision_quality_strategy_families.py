from app.services.living_strategy_runtime import build_living_strategy_context


def _strategy(text: str, **state):
    base = {
        "budget": 8000,
        "locationCity": "Las Vegas",
        "memoryStatus": state.pop("memoryStatus", "No"),
    }
    base.update(state)
    return build_living_strategy_context(base, text)


def _ranked_ids(result):
    return [row["strategy_id"] for row in result["strategy_candidates"]]


def _leading_ids(result):
    return {
        row["strategy_id"]
        for row in result["strategy_candidates"]
        if int(row.get("rank_hint") or 99) == 1
    }


def test_golden_independent_resident_leads_with_independent_living():
    result = _strategy(
        "My mother is fully independent with bathing, dressing, toileting, transfers and medications. "
        "She has no memory concerns, no mobility limitation, and no medical or nursing needs.",
        assistanceLevel="Fully independent",
    )
    assert "INDEPENDENT_LIVING" in _leading_ids(result)
    assert "MEMORY_CARE" not in _ranked_ids(result)
    assert result["signals"]["adl_support_needed"] is False


def test_golden_persistent_adl_need_leads_with_assisted_living():
    result = _strategy(
        "My father needs ongoing help with bathing, dressing and toileting. He has no dementia and this is not temporary.",
        assistanceLevel="Needs assistance",
    )
    assert "ASSISTED_LIVING" in _leading_ids(result)
    assert "INDEPENDENT_LIVING" not in _leading_ids(result)


def test_golden_medication_support_only_does_not_fall_into_unresolved_bucket():
    result = _strategy(
        "My mother is cognitively intact and independent with personal care, but she needs medication management every day."
    )
    assert "ASSISTED_LIVING" in _leading_ids(result)
    assert "ASSISTED_OR_INDEPENDENT_LIVING_UNRESOLVED" not in _ranked_ids(result)


def test_golden_memory_need_leads_with_memory_care():
    result = _strategy(
        "My mother has Alzheimer disease, cognitive impairment and wandering risk. She needs memory care.",
        memoryStatus="Yes",
        assistanceLevel="Needs assistance",
    )
    assert "MEMORY_CARE" in _leading_ids(result)
    assert result["signals"]["memory_care_needed"] is True
    assert "INDEPENDENT_LIVING" not in _leading_ids(result)


def test_golden_temporary_adl_recovery_preserves_lower_intensity_option():
    result = _strategy(
        "My father is recovering after surgery and temporarily needs help with bathing and dressing for 3 months. "
        "He has no dementia and is expected to recover."
    )
    assert "INDEPENDENT_LIVING_PLUS_TEMPORARY_CARE" in _leading_ids(result)
    assisted = next(row for row in result["strategy_candidates"] if row["strategy_id"] == "ASSISTED_LIVING")
    assert assisted["rank_hint"] > 1


def test_golden_skilled_rehab_is_separated_from_long_term_residence():
    result = _strategy(
        "My father had back surgery and requires skilled rehabilitation with physical therapy and occupational therapy before returning to independent living."
    )
    assert "POST_ACUTE_REHAB_THEN_INDEPENDENT_LIVING" in _leading_ids(result)
    assert "SHORT_STAY_SKILLED_NURSING_REHAB" in _ranked_ids(result)


def test_golden_mixed_need_couple_has_memory_continuum_option():
    result = _strategy(
        "My parents want to remain near each other. My mother is independent, while my father has dementia and needs memory care."
        , memoryStatus="Yes"
    )
    assert result["household"]["type"] == "COUPLE"
    assert "MEMORY_CARE" in _leading_ids(result)
    assert "LIFE_PLAN_CCRC_WITH_MEMORY_CONTINUUM" in _ranked_ids(result)
