import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_external_claim_cannot_shadow_canonical_reason():
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "decision:canonical-reason", "text": "Different reason.", "provenance_ids": ["case:x"]}])
