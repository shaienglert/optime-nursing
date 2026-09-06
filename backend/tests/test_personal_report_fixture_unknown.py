import json
from pathlib import Path


def test_expected_unknown_is_not_silently_resolved():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_id"] == "facility:night-staff")
    assert claim["claim_type"] == "UNKNOWN"
    assert "not been verified" in claim["text"]
