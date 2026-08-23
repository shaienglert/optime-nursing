from app.services.patient_decision_engine_runtime import _strategy_universe_status


def _strategy(*rows):
    return {"strategy_candidates": list(rows)}


def _s(strategy_id, rank_hint=1):
    return {"strategy_id": strategy_id, "rank_hint": rank_hint}


def _row(canonical_type, *, modalities=(), care_status="POSSIBLE_FIT", hard_gate="PASS"):
    return {
        "canonical_type": canonical_type,
        "housing_modalities": list(modalities),
        "care_setting_fit": {"status": care_status},
        "client_intent_fit": {"hard_gate": hard_gate},
    }


def test_independent_living_rank_one_requires_il_in_survivor_universe():
    status = _strategy_universe_status(
        [_row("ASSISTED_LIVING_RFG", care_status="POSSIBLE_FIT")],
        _strategy(_s("INDEPENDENT_LIVING", 1), _s("LIFE_PLAN_CCRC", 2)),
    )
    assert status["status"] == "INCOMPLETE_FOR_LEADING_STRATEGIES"
    assert "INDEPENDENT_LIVING" in status["missing_classes"]


def test_independent_living_rank_one_is_sufficient_when_il_exists():
    status = _strategy_universe_status(
        [_row("INDEPENDENT_LIVING", care_status="PRIMARY_FIT")],
        _strategy(_s("INDEPENDENT_LIVING", 1), _s("LIFE_PLAN_CCRC", 2)),
    )
    assert status["status"] == "SUFFICIENT_FOR_LEADING_STRATEGIES"


def test_memory_care_requires_a_primary_fit_candidate():
    no_memory_fit = _strategy_universe_status(
        [_row("ASSISTED_LIVING_RFG", care_status="POSSIBLE_FIT")],
        _strategy(_s("MEMORY_CARE", 1)),
    )
    assert no_memory_fit["status"] == "INCOMPLETE_FOR_LEADING_STRATEGIES"

    with_memory_fit = _strategy_universe_status(
        [_row("ASSISTED_LIVING_RFG", care_status="PRIMARY_FIT")],
        _strategy(_s("MEMORY_CARE", 1)),
    )
    assert with_memory_fit["status"] == "SUFFICIENT_FOR_LEADING_STRATEGIES"


def test_rejected_candidate_must_not_make_universe_complete():
    survivors = [_row("ASSISTED_LIVING_RFG", care_status="POSSIBLE_FIT")]
    rejected_il = _row("INDEPENDENT_LIVING", care_status="PRIMARY_FIT", hard_gate="FAIL")
    status = _strategy_universe_status(survivors, _strategy(_s("INDEPENDENT_LIVING", 1)))
    assert status["status"] == "INCOMPLETE_FOR_LEADING_STRATEGIES"
    assert rejected_il["client_intent_fit"]["hard_gate"] == "FAIL"
