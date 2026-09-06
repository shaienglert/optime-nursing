import copy

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_report_generation_does_not_mutate_source_result():
    result = {"results": [], "decision_intelligence": {"human_intelligence": {"decision_readiness": "UNKNOWN"}}}
    before = copy.deepcopy(result)
    build_personal_report_payload(result)
    assert result == before
