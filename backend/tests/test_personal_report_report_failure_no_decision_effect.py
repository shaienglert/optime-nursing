import copy
import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_failed_report_does_not_modify_result_or_decision_payload():
    result = {"results": [], "decision_intelligence": {"human_intelligence": {"decision_readiness": "UNKNOWN"}}}
    before = copy.deepcopy(result)
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload(result, case_claims=[{"claim_id": "dup", "text": "A", "provenance_ids": ["case:a"]}, {"claim_id": "dup", "text": "B", "provenance_ids": ["case:b"]}])
    assert result == before
