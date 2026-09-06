import json
from pathlib import Path


def test_expected_unknown_is_in_before_you_decide():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    section = next(s for s in data["sections"] if any(c["claim_id"] == "facility:night-staff" for c in s["claims"]))
    assert section["section"] == "BEFORE_YOU_DECIDE"
