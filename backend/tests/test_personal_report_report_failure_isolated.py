import copy
import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_report_failure_does_not_mutate_underlying_decision_result():
    result = {"results": [], "decision_intelligence": {}}
    before = copy.deepcopy(result)
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload(result, case_claims=[
            {"claim_id": "dup", "text": "A", "provenance_ids": ["case:a"]},
            {"claim_id": "dup", "text": "B", "provenance_ids": ["case:b"]},
        ])
    assert result == before
