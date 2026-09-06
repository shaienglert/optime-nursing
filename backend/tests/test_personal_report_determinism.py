from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_same_input_yields_same_report():
    result = {"results": [], "decision_intelligence": {}}
    kwargs = {"case_claims": [{"claim_id": "case:x", "text": "Exact user fact.", "provenance_ids": ["case:x"]}]}
    first = render_personal_report(build_personal_report_payload(result, **kwargs))
    second = render_personal_report(build_personal_report_payload(result, **kwargs))
    assert first == second
