import pytest

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_research_cannot_expand_report_section_scope():
    with pytest.raises(ValueError):
        build_personal_report_payload(
            {"results": [], "decision_intelligence": {}},
            research_claims=[{"claim_id": "research:x", "approved_text": "Finding.", "provenance_ids": ["research:RI-X"], "allowed_sections": ["NEW_TOPIC_AI_CREATED"]}],
        )
