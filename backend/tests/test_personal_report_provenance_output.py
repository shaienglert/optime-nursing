from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_every_rendered_claim_exposes_provenance():
    report = render_personal_report(build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        case_claims=[{"claim_id": "case:x", "text": "User fact.", "provenance_ids": ["case:user:x"]}],
    ))
    assert all(claim["provenance_ids"] for section in report["sections"] for claim in section["claims"])
