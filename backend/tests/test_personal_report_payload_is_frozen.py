import pytest
from dataclasses import FrozenInstanceError
from app.services.personal_decision_report_builder import build_personal_report_payload


def test_payload_object_is_frozen():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}})
    with pytest.raises(FrozenInstanceError):
        payload.approved_claims = ()
