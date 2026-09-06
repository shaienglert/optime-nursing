import pytest
from app.services.personal_decision_report_builder import build_personal_report_payload


def test_facility_input_cannot_invent_section():
    with pytest.raises(ValueError):
        build_personal_report_payload({"results": [], "decision_intelligence": {}}, facility_claims=[{"claim_id": "facility:x", "text": "X.", "verified": True, "provenance_ids": ["facility:x"], "allowed_sections": ["NEW_DOMAIN"]}])
