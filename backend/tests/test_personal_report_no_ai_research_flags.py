import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_contract_flags_are_hardcoded_safe():
    source = inspect.getsource(build_personal_report_payload)
    assert '"ranking_recalculated": False' in source
    assert '"research_performed": False' in source
    assert '"resolved_unknowns": []' in source
