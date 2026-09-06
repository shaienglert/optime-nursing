import pytest
from app.services.personal_decision_report_builder import build_personal_report_payload


def test_case_input_cannot_invent_section():
    with pytest.raises(ValueError):
        build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:x", "text": "X.", "provenance_ids": ["case:x"], "allowed_sections": ["NEW_DOMAIN"]}])
