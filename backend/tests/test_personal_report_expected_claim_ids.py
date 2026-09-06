import json
from pathlib import Path


def test_synthetic_expected_report_claim_set_is_fixed():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    ids = [c["claim_id"] for s in data["sections"] for c in s["claims"]]
    assert set(ids) == {"decision:canonical-reason", "case:role", "case:priority", "research:transition-autonomy", "facility:night-staff"}
