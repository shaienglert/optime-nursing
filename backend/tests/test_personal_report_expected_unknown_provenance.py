import json
from pathlib import Path


def test_synthetic_unknown_provenance_is_explicitly_unknown():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    claim = next(c for s in data["sections"] for c in s["claims"] if c["claim_id"] == "facility:night-staff")
    assert claim["provenance_ids"] == ["facility:night_staffing:UNKNOWN"]
