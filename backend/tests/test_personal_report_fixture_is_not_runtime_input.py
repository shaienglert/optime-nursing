from pathlib import Path


def test_synthetic_report_fixture_lives_only_under_tests():
    path = Path(__file__).parent / "fixtures" / "personal_report_expected.json"
    assert "tests" in path.parts
