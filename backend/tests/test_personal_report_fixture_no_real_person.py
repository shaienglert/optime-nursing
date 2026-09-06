from pathlib import Path


def test_synthetic_artifact_does_not_name_a_real_person():
    text = (Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text()
    assert '"person_name"' not in text
    assert '"client_name"' not in text
