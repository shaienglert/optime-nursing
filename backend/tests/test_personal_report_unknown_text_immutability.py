from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_unknown_is_rendered_exactly_as_unknown():
    text = "Medication management availability has not been verified."
    report = render_personal_report(build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        facility_claims=[{"claim_id": "facility:meds", "approved_text": text, "unknown": True, "provenance_ids": ["facility:meds:UNKNOWN"]}],
    ))
    claim = next(c for s in report["sections"] for c in s["claims"] if c["claim_id"] == "facility:meds")
    assert claim["claim_type"] == "UNKNOWN"
    assert claim["text"] == text
