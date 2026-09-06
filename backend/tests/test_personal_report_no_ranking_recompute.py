import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_has_no_ranking_function_calls():
    source = inspect.getsource(build_personal_report_payload).lower()
    assert "rank_candidates" not in source
    assert "score_candidates" not in source
    assert "rerank" not in source
