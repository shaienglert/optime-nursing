from app.services.living_strategy_runtime import build_living_strategy_context

CLIENT_TEXT = (
    "My mother is 82 and is looking for senior living in Las Vegas. "
    "She is fully independent with bathing, dressing, toileting, transfers, medications, decision-making and memory. "
    "She has no memory concerns, does not need cognitive support, has no mobility limitation, and has no special medical or nursing needs. "
    "Her total monthly budget is up to $8,000."
)


def test_fully_independent_client_has_independent_living_as_leading_strategy():
    strategy = build_living_strategy_context(
        {
            "relationship": "My mother",
            "ageGroup": "80-84",
            "assistanceLevel": "Fully independent",
            "memoryStatus": "No",
            "budget": 8000,
            "locationCity": "Las Vegas",
        },
        CLIENT_TEXT,
    )
    leading = {
        row["strategy_id"]
        for row in strategy.get("strategy_candidates") or []
        if int(row.get("rank_hint") or 99) <= 2
    }
    assert "INDEPENDENT_LIVING" in leading or "LIFE_PLAN_CCRC" in leading, strategy
    assert strategy["signals"]["adl_support_needed"] is False
    assert strategy["signals"]["medication_support_needed"] is False
    assert strategy["signals"]["no_dementia"] is True
