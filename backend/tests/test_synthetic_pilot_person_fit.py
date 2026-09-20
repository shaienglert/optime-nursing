from app.services import human_intelligence_runtime_verified as runtime


def _context(preference: str) -> dict:
    return {"signals": {"community_size_preference": {"value": preference}}}


def test_synthetic_pilot_uses_governed_catalog_size_for_person_fit(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "_verified_person_fit_index", lambda: {})
    rows = [{
        "canonical_facility_id": "PILOT-NV-001",
        "synthetic_pilot": True,
        "community_size": "SMALL",
        "licensed_capacity": 28,
    }]

    runtime.attach_human_person_fit(rows, _context("SMALL"))

    size = rows[0]["human_person_fit"]["community_size"]
    assert size["community_size_band"] == "SMALL_COMMUNITY"
    assert size["fit_score"] == 100.0
    assert size["official_bed_count"] == 28
    assert size["source"] == "Governed synthetic pilot catalog"
    assert size["evidence_class"] == "SYNTHETIC_PILOT_VERIFIED"


def test_synthetic_pilot_size_preference_changes_fit_order(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "_verified_person_fit_index", lambda: {})
    rows = [
        {"canonical_facility_id": "PILOT-NV-S", "synthetic_pilot": True, "community_size": "SMALL", "licensed_capacity": 20},
        {"canonical_facility_id": "PILOT-NV-L", "synthetic_pilot": True, "community_size": "LARGE", "licensed_capacity": 140},
    ]

    runtime.attach_human_person_fit(rows, _context("LARGE"))

    ordered = sorted(rows, key=runtime.person_fit_sort_key)
    assert [row["canonical_facility_id"] for row in ordered] == ["PILOT-NV-L", "PILOT-NV-S"]


def test_non_pilot_row_cannot_self_assert_person_fit(monkeypatch) -> None:
    monkeypatch.setattr(runtime, "_verified_person_fit_index", lambda: {})
    rows = [{
        "canonical_facility_id": "REAL-NV-001",
        "synthetic_pilot": False,
        "community_size": "SMALL",
        "licensed_capacity": 20,
    }]

    runtime.attach_human_person_fit(rows, _context("SMALL"))

    size = rows[0]["human_person_fit"]["community_size"]
    assert size["community_size_band"] == "UNKNOWN"
    assert size["fit_score"] == "UNKNOWN"
    assert size["source"] == "UNKNOWN"
