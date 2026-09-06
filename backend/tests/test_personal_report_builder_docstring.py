from app.services.personal_decision_report_builder import build_personal_report_payload


def test_builder_documents_explicit_upstream_authority():
    assert "only explicit upstream authority" in (build_personal_report_payload.__doc__ or "")
