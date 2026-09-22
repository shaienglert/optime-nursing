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


def _decision_for_budget(budget: int) -> dict:
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
        refresh_runtime_cache(f"budget-coverage-{budget}")
        return run_patient_decision_engine(questionnaire, "Las Vegas", limit=10)


def _rank_for_size(preference: str) -> list[dict]:
    questionnaire = {
        "assistanceLevel": "Help with bathing, Help with dressing, Help with medications",
        "budget": 9900,
        "moveTiming": "Planning ahead",
        "humanIntelligenceV2": {
            "personalityProfile": {"communitySizePreference": preference},
        },
    }
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200"},
        clear=False,
    ):
        refresh_runtime_cache(f"size-ranking-{preference}")
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


def test_no_in_budget_result_is_disclosed_instead_of_presented_as_a_fit() -> None:
    decision = _decision_for_budget(1000)

    assert not decision["results"]
    assert decision["must_pending_verification_count"] > 0
    assert decision["decision_intelligence"]["canonical_decision_state"]["can_show_recommendations"] is False
    assert "No currently eligible pilot community" in decision["market_coverage_notice"]
    assert "not in-budget matches" in decision["market_coverage_notice"]


def test_explicit_community_size_changes_full_engine_ranking() -> None:
    small = _rank_for_size("Small and familiar")
    large = _rank_for_size("Large and active")

    assert [row["canonical_facility_id"] for row in small] != [
        row["canonical_facility_id"] for row in large
    ]
    assert small[0]["human_person_fit"]["community_size"]["preference"] == "SMALL"
    assert small[0]["human_person_fit"]["community_size"]["fit_score"] == 100.0
    assert large[0]["human_person_fit"]["community_size"]["preference"] == "LARGE"
    assert large[0]["human_person_fit"]["community_size"]["fit_score"] == 100.0


def test_required_dialysis_need_reaches_full_engine_candidate_discovery() -> None:
    questionnaire = {
        "assistanceLevel": "Help with bathing and medications",
        "budget": 7500,
        "moveTiming": "Within 30 days",
        "medicalCareProfile": {"needs": ["Dialysis", "Wound care"]},
    }
    with patch.dict(
        "os.environ",
        {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "200"},
        clear=False,
    ):
        refresh_runtime_cache("required-dialysis-full-engine")
        decision = run_patient_decision_engine(
            questionnaire,
            "My father needs dialysis three times a week and wound care.",
            limit=10,
        )

    assert "dialysis_arrangements" in decision["candidate_discovery"]["required_parameter_ids"]
