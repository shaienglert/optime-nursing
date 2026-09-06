import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_contract import ReportContractViolation


def test_facility_cannot_override_canonical_decision_claim_id():
    with pytest.raises(ReportContractViolation):
        build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "decision:canonical-reason", "text": "Override.", "verified": True, "provenance_ids": ["facility:x"]}])
