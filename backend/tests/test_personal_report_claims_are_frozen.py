import pytest
from dataclasses import FrozenInstanceError
from app.services.personal_decision_report_builder import build_personal_report_payload


def test_approved_claim_objects_are_frozen():
    claim = build_personal_report_payload({"results": [], "decision_intelligence": {}}).approved_claims[0]
    with pytest.raises(FrozenInstanceError):
        claim.approved_text = "changed"
