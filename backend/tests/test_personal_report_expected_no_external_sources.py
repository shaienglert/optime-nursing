from pathlib import Path


def test_expected_report_has_no_web_or_document_research_provenance():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text()
    assert '"web:' not in text
    assert '"document:' not in text
