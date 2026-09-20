from __future__ import annotations

from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.patient_decision_engine import run_patient_decision_engine


def _rank_for_budget(budget: int) -> list[dict]:
    questionnaire = {
        "assistanceLevel": "Help with bathing, Help with dressing, Help with medications",
        "budget": budget,
        "moveTiming": "Planning ahead",
    }
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200"},
        clear=False,
    ):
        refresh_runtime_cache(f"personalized-ranking-{budget}")
        return run_patient_decision_engine(questionnaire, "Las Vegas", limit=10)["results"]


def test_budget_changes_ranking_and_top_results_fit_budget() -> None:
    lower = _rank_for_budget(5000)
    higher = _rank_for_budget(9900)

    assert len(lower) == 10
    assert len(higher) == 10
    assert [row["canonical_facility_id"] for row in lower] != [
        row["canonical_facility_id"] for row in higher
    ]
    assert all(float(row["starting_monthly_price"]) <= 5000 for row in lower)
    assert all(row["quality_safety_score"] is not None for row in lower + higher)
    assert all(row["staffing_score"] is not None for row in lower + higher)

