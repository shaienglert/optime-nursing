from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_nevada_recommendation_source_coverage import listing_match, scope_records  # noqa: E402


def record(name="ALPHA CARE", address="100 W MAIN ST", zip_code="89101", typ="ASSISTED_LIVING_RFG"):
    return {
        "canonical_id": "X",
        "facility_name": name,
        "address": address,
        "city": "LAS VEGAS",
        "zip": zip_code,
        "canonical_type": typ,
        "is_las_vegas_valley": True,
        "nevada_license_id": "1-AGC-1",
    }


def test_directory_name_alone_never_matches():
    r = record()
    assert listing_match(r, "alpha care las vegas senior living") is False


def test_directory_exact_normalized_address_and_zip_matches():
    r = record(address="100 W. Main Street")
    page = "alpha care 100 west main st las vegas nv 89101"
    assert listing_match(r, page) is True


def test_scope_is_type_specific():
    rows = [record(), record(typ="SKILLED_NURSING"), record(typ="INDEPENDENT_LIVING")]
    assert len(scope_records(rows, "LAS_VEGAS_VALLEY")) == 3
    assert len(scope_records(rows, "LAS_VEGAS_VALLEY_ASSISTED_LIVING_RFG")) == 1
    assert len(scope_records(rows, "LAS_VEGAS_VALLEY_SKILLED_NURSING")) == 1


def test_non_valley_record_is_excluded():
    r = record()
    r["is_las_vegas_valley"] = False
    assert scope_records([r], "LAS_VEGAS_VALLEY") == []
