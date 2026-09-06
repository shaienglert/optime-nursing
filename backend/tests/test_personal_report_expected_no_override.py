import json
from pathlib import Path


def test_expected_report_has_no_override_fields():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    text = json.dumps(data).lower()
    assert '"override"' not in text
    assert '"writeback"' not in text
