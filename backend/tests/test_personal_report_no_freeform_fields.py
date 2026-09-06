from dataclasses import fields

from app.services.personal_decision_report_builder import PersonalReportPayload


def test_payload_has_no_freeform_narrative_field():
    names = {field.name for field in fields(PersonalReportPayload)}
    assert names == {"canonical_decision", "approved_claims", "claim_uses"}
    assert not names.intersection({"narrative", "summary", "ai_text", "freeform", "recommendation_text"})
