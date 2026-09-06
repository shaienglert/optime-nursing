import json
from pathlib import Path


def test_expected_material_text_is_explicit_and_fixed():
    data = json.loads((Path(__file__).parent / "fixtures" / "personal_report_expected.json").read_text())
    texts = {c["claim_id"]: c["text"] for s in data["sections"] for c in s["claims"]}
    assert texts["facility:night-staff"] == "Night staffing has not been verified."
    assert texts["decision:canonical-reason"] == "validated MUST gate and AI ranking are complete"
