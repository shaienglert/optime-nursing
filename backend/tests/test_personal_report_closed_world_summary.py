from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_no_material_sentence_exists_outside_approved_claim_set():
    payload = build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        case_claims=[{"claim_id": "case:a", "text": "A.", "provenance_ids": ["case:a"]}],
        research_claims=[{"claim_id": "research:b", "approved_text": "B.", "provenance_ids": ["research:b"]}],
    )
    report = render_personal_report(payload)
    rendered = {(c["claim_id"], c["text"]) for s in report["sections"] for c in s["claims"]}
    approved = {(c.claim_id, c.approved_text) for c in payload.approved_claims}
    assert rendered == approved
