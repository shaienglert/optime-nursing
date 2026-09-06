import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_case_cannot_override_canonical_decision_claim_id():
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "decision:canonical-reason", "text": "Override.", "provenance_ids": ["case:attack"]}])
