from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_every_runtime_material_claim_has_source():
    report = render_personal_report(build_personal_report_payload({"results": [], "decision_intelligence": {}}))
    assert all(c["provenance_ids"] for s in report["sections"] for c in s["claims"])
