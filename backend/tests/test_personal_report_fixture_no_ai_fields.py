from pathlib import Path


def test_synthetic_expected_report_has_no_ai_generation_channel():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text().lower()
    assert '"prompt"' not in text
    assert '"completion"' not in text
    assert '"ai_summary"' not in text
