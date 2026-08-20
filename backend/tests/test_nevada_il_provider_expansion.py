from __future__ import annotations

import json
from pathlib import Path

from app.services.canonical_universe import _apply_verified_housing_overlays


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "data" / "nevada" / "verified" / "provider_housing_primary_evidence.json"

EXPECTED_PROVIDER_IL_IDS = {
    "NV-PROVIDER-IL-VISTA-PARK",
    "NV-PROVIDER-IL-COUNTRY-CLUB-MEADOWS",
    "NV-PROVIDER-IL-COUNTRY-CLUB-VALLEY-VIEW",
    "NV-PROVIDER-IL-DESTINATIONS-PEBBLE",
    "NV-PROVIDER-IL-DESTINATIONS-PUEBLO",
    "NV-PROVIDER-IL-CAREFREE-WILLOWS",
    "NV-PROVIDER-IL-ALBUM-UNION-VILLAGE",
}


def _provider_rows() -> list[dict]:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    return list(payload.get("records") or [])


def test_verified_provider_expansion_has_primary_identity_and_no_care_inference():
    rows = {row.get("canonical_id"): row for row in _provider_rows() if row.get("canonical_id") in EXPECTED_PROVIDER_IL_IDS}
    assert set(rows) == EXPECTED_PROVIDER_IL_IDS
    for canonical_id, row in rows.items():
        assert row["append_as_canonical"] is True
        assert row["canonical_type"] == "INDEPENDENT_LIVING"
        assert row["state"] == "NV"
        assert str(row["primary_source_url"]).startswith("https://")
        assert row["evidence"]["independent_living_verified"] is True
        if canonical_id != "NV-PROVIDER-IL-VISTA-PARK":
            assert row["evidence"].get("care_services_verified") == "UNKNOWN"


def test_vista_park_preserves_verified_il_plus_external_care_model():
    row = next(row for row in _provider_rows() if row.get("canonical_id") == "NV-PROVIDER-IL-VISTA-PARK")
    assert row["evidence"]["outside_care_allowed_verified"] is True
    assert row["evidence"]["independent_living_verified"] is True
    assert "ASSISTED_LIVING" not in row["housing_modalities"]
    assert "MEMORY_CARE" not in row["housing_modalities"]


def test_runtime_overlay_marks_provider_only_il_as_unregulated_senior_housing_not_hcqc():
    payload = _apply_verified_housing_overlays({"records": [], "record_count": 0})
    by_id = {row.get("canonical_id"): row for row in payload["records"]}
    for canonical_id in EXPECTED_PROVIDER_IL_IDS:
        row = by_id[canonical_id]
        assert row["canonical_type"] == "INDEPENDENT_LIVING"
        assert row["license_status"] == "UNREGULATED_SENIOR_HOUSING_PROVIDER_VERIFIED"
        assert row["source_truth_scope"] == "PRIMARY_PROVIDER_IDENTITY_NO_CARE_LICENSE_INFERRED"
        assert row["state"] == "NV"
        assert row["is_las_vegas_valley"] is True
        assert "INDEPENDENT_LIVING" in row.get("housing_modalities", [])
