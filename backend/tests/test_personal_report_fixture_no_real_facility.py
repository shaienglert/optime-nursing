from pathlib import Path


def test_synthetic_artifact_does_not_name_a_real_facility():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text()
    assert '"facility_name"' not in text
