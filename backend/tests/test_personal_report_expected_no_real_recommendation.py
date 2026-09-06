from pathlib import Path


def test_synthetic_expected_report_does_not_name_recommended_facility():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text()
    assert '"recommended_facility"' not in text
    assert '"ranked_options"' not in text
