from scripts.promote_nevada_pca_full_sweep_safe import UNKNOWN, _safe_row


def test_safe_promotion_keeps_absent_negative_signals_unknown():
    row = {
        "agency_id": "NV-PCA-X",
        "agency_name": "Example",
        "license_number": "1-PCS-0",
        "identity_verified": True,
        "primary_source_url": "https://example.test/",
        "bathing_assistance": True,
        "dressing_assistance": False,
        "transfer_assistance": False,
        "minimum_billable_hours": 4,
        "employment_model": "W2_EMPLOYEES",
        "background_check_verified": True,
        "workers_comp_verified": False,
        "languages": ["Spanish"],
    }
    promoted = _safe_row(row)
    assert promoted["bathing_assistance"] is True
    assert promoted["dressing_assistance"] == UNKNOWN
    assert promoted["transfer_assistance"] == UNKNOWN
    assert promoted["workers_comp_verified"] == UNKNOWN
    assert promoted["minimum_billable_hours"] == 4
    assert promoted["employment_model"] == "W2_EMPLOYEES"
    assert promoted["background_check_verified"] is True
    assert promoted["hourly_rate"] == UNKNOWN
    assert promoted["languages"] == ["Spanish"]
