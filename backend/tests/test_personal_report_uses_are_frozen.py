import pytest
from dataclasses import FrozenInstanceError
from app.services.personal_decision_report_builder import build_personal_report_payload


def test_claim_use_objects_are_frozen():
    use = build_personal_report_payload({"results": [], "decision_intelligence": {}}).claim_uses[0]
    with pytest.raises(FrozenInstanceError):
        use.rendered_text = "changed"
