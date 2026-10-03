"""One fact, one authority: the budget sentence shown to the family follows the funding pathway.

Medicaid pathway -> the budget is compared with the household's Medicaid out-of-pocket cost, so
the private-price sentence ("lowest verified starting price $X") must not be shown, and the
pathway statement must be. Private pay is unchanged.
"""
import os
from unittest.mock import patch

import pytest

from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
from app.services.decision_pipeline import _reconcile_budget_notice

PRIVATE = (
    "No currently eligible pilot community in this result set fits the stated $3,000 monthly budget. "
    "The lowest verified starting price shown is $4,208; these are alternatives for review, not in-budget matches."
)


def _result(pathway):
    return {
        "market_coverage_notice": PRIVATE,
        "decision_intelligence": {"client_intent": {"funding_pathway": pathway}},
    }


def test_medicaid_pathway_replaces_the_private_price_sentence():
    result = _result("MEDICAID")
    _reconcile_budget_notice(result, {"budget": 3000})
    notice = result["market_coverage_notice"]
    assert "$4,208" not in notice and "lowest verified starting price" not in notice
    assert "$3,000" in notice and "out-of-pocket cost under Medicaid" in notice


def test_other_notice_text_is_kept_when_the_budget_sentence_is_replaced():
    result = _result("MEDICAID")
    result["market_coverage_notice"] = "This search covers the las-vegas market only. " + PRIVATE
    _reconcile_budget_notice(result, {"budget": 3000})
    assert result["market_coverage_notice"].startswith("This search covers the las-vegas market only.")


def test_private_pay_notice_is_unchanged():
    result = _result("PRIVATE_PAY")
    _reconcile_budget_notice(result, {"budget": 3000})
    assert result["market_coverage_notice"] == PRIVATE


@pytest.mark.parametrize("persona_id,expect_medicaid", [("pilot-006", True), ("pilot-001", False)])
def test_engine_notice_matches_the_pathway(persona_id, expect_medicaid):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    import test_golden_persona_decisions as golden

    env = {"OPTIME_CANONICAL_MARKET": "synthetic-pilot", "OOMNIK_PILOT_FACILITY_LIMIT": "500", "OPTIME_SEMANTIC_AI_ENABLED": "0"}
    with patch.dict(os.environ, env, clear=False):
        from app.services.facility_parameter_service import refresh_runtime_cache
        from app.services.patient_decision_engine import run_patient_decision_engine

        refresh_runtime_cache("budget-notice-pathway")
        persona = next(p for p in golden.PERSONAS if p["id"] == persona_id)
        questionnaire = materialize_questionnaire(build_structured_profile(persona["questionnaire_state"]))
        response = run_patient_decision_engine(questionnaire, "", limit=50)
    notice = response.get("market_coverage_notice") or ""
    pathway = response["decision_intelligence"]["client_intent"].get("funding_pathway")
    assert (pathway == "MEDICAID") is expect_medicaid
    if expect_medicaid:
        assert "lowest verified starting price" not in notice
        assert "out-of-pocket cost under Medicaid" in notice
    else:
        assert "out-of-pocket cost under Medicaid" not in notice
