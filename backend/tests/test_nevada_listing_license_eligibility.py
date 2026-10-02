from datetime import datetime, timedelta, timezone

from app.services.facility_parameter_service import _canonical_records_for_market


def _licensed_care(**overrides):
    row = {
        "canonical_id": "NV-LIC-1",
        "canonical_type": "ASSISTED_LIVING_RFG",
        "is_las_vegas_valley": True,
        "nevada_license_id": "123-AGC",
        "detail_url": "https://nvdpbh.aithent.com/Protected/INS/example",
        "license_status": "Active",
        "expiration_date": (datetime.now(timezone.utc).date() + timedelta(days=90)).strftime("%m/%d/%Y"),
    }
    return {**row, **overrides}


def test_care_without_current_official_license_is_not_in_available_nevada_catalog():
    expired = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime("%m/%d/%Y")
    records = [
        _licensed_care(),
        _licensed_care(canonical_id="NO_ID", nevada_license_id="UNKNOWN"),
        _licensed_care(canonical_id="NO_SOURCE", detail_url="UNKNOWN"),
        _licensed_care(canonical_id="NO_DATE", expiration_date="UNKNOWN"),
        _licensed_care(canonical_id="EXPIRED", expiration_date=expired),
        _licensed_care(canonical_id="SUSPENDED", license_status="Suspended"),
        _licensed_care(canonical_id="UNVERIFIED_SNF", canonical_type="SKILLED_NURSING", nevada_license_id="UNKNOWN"),
        {"canonical_id": "IL", "canonical_type": "INDEPENDENT_LIVING", "is_las_vegas_valley": True},
    ]
    visible = _canonical_records_for_market({"records": records}, "las-vegas")
    assert {row["canonical_id"] for row in visible} == {"NV-LIC-1", "IL"}


def test_synthetic_pilot_is_kept_separate_from_live_licensing_claims(monkeypatch):
    monkeypatch.setenv("OOMNIK_PILOT_CATALOG_SIZE", "500")
    pilot = {"canonical_id": "PILOT", "pilot_exposure_order": 1, "canonical_type": "ASSISTED_LIVING_RFG"}
    assert _canonical_records_for_market({"records": [pilot]}, "synthetic-pilot") == [pilot]
