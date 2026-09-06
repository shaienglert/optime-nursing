import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_builder_uses_contract_and_fails_closed_on_duplicate_authority():
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload(
            {"results": [], "decision_intelligence": {}},
            case_claims=[
                {"claim_id": "same", "text": "A", "provenance_ids": ["case:a"]},
                {"claim_id": "same", "text": "B", "provenance_ids": ["case:b"]},
            ],
        )
