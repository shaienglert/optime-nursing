from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_no_source_means_no_material_sentence():
    report = render_personal_report(build_personal_report_payload(
        {"results": [], "decision_intelligence": {}},
        case_claims=[{"claim_id": "case:no", "text": "No source.", "provenance_ids": []}],
        research_claims=[{"claim_id": "research:no", "approved_text": "No source.", "provenance_ids": []}],
        facility_claims=[{"claim_id": "facility:no", "text": "No source.", "verified": True, "provenance_ids": []}],
    ))
    ids = {claim["claim_id"] for section in report["sections"] for claim in section["claims"]}
    assert not ids.intersection({"case:no", "research:no", "facility:no"})
