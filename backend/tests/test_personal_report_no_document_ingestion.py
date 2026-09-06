import inspect

from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_signature_has_no_document_or_web_input():
    params = set(inspect.signature(build_personal_report_payload).parameters)
    assert not params.intersection({"documents", "web_results", "urls", "attachments", "sources"})
