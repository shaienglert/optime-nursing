import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_derives_decision_once_from_canonical_adapter():
    source = inspect.getsource(build_personal_report_payload)
    assert source.count("derive_canonical_decision_state") == 1
