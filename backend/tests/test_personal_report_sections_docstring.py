from app.services import personal_decision_report_sections


def test_section_module_documents_strict_normalization():
    assert "Strict section normalization" in (personal_decision_report_sections.__doc__ or "")
