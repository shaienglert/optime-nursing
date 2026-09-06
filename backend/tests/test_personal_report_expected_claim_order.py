import json
from pathlib import Path


def test_synthetic_expected_claim_order_by_section_is_fixed():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    ids = [c["claim_id"] for s in data["sections"] for c in s["claims"]]
    assert ids == ["case:role", "case:priority", "decision:canonical-reason", "research:transition-autonomy", "facility:night-staff"]
