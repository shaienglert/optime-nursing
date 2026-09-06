from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_user_fact_does_not_generate_additional_interpretation():
    payload = build_personal_report_payload({"results": [], "decision_intelligence": {}}, case_claims=[{"claim_id": "case:independence", "text": "Independence is important to the family.", "provenance_ids": ["case:user:independence"]}])
    report = render_personal_report(payload)
    case_claims = [c for s in report["sections"] for c in s["claims"] if c["claim_id"].startswith("case:")]
    assert [(c["claim_id"], c["text"]) for c in case_claims] == [("case:independence", "Independence is important to the family.")]
