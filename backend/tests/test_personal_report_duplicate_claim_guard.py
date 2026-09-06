import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_duplicate_claim_ids_fail_closed():
    result = {
        "results": [{"client_intent_fit": {"hard_gate": "MUST_ELIGIBLE"}}],
        "must_eligible_count": 1,
        "decision_intelligence": {
            "human_intelligence": {"decision_readiness": "READY"},
            "facility_selection_pipeline": {"ai_ranking": {"status": "AI_RANKED"}, "dynamic_preferences": {"preference_count": 0}},
        },
    }
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload(result, case_claims=[
            {"claim_id": "case:same", "text": "First.", "provenance_ids": ["case:1"]},
            {"claim_id": "case:same", "text": "Second.", "provenance_ids": ["case:2"]},
        ])
