from pathlib import Path


def test_synthetic_expected_report_contains_no_ranked_options():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text()
    assert '"ranked_options"' not in text
    assert '"ranking"' not in text
