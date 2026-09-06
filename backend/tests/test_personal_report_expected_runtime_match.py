# The full generator-vs-artifact equality assertion lives in
# test_personal_report_expected_artifact.py. This sentinel makes that contract
# discoverable in targeted report test selections.
from pathlib import Path


def test_generator_lock_test_exists():
    assert (Path(__file__).parent / "test_personal_report_expected_artifact.py").exists()
