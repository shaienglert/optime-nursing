from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_nevada_snf_directories_and_fines import (  # noqa: E402
    audit_fines,
    directory_content_is_auditable,
    directory_match,
    is_block_page,
    snf_valley,
)


def record(name="ADVANCED HEALTH CARE OF LAS VEGAS", address="5840 W SUNSET RD", city="LAS VEGAS", zip_code="89118", ccn="295090"):
    return {
        "canonical_id": f"CMS-{ccn}",
        "facility_name": name,
        "address": address,
        "city": city,
        "zip": zip_code,
        "canonical_type": "SKILLED_NURSING",
        "is_las_vegas_valley": True,
        "cms_ccn": ccn,
    }


def test_incapsula_challenge_is_blocked_not_live_zero():
    assert is_block_page("Request unsuccessful. Incapsula incident ID: 123") is True


def test_nursinghomes_http_200_without_identity_is_unknown_not_zero():
    assert directory_content_is_auditable("NursingHomes.com", "generic shell returned with status 200", 0) is False
    assert directory_content_is_auditable("NursingHomes.com", "usable facility content", 1) is True


def test_statewide_directory_address_matches_strongly():
    r = record()
    page = "Advanced Health Care of Las Vegas 5840 W Sunset Road Las Vegas NV 89118"
    assert directory_match(r, page) is True


def test_name_city_ranked_page_can_match_when_address_omitted():
    r = record()
    page = "Advanced Health Care of Las Vegas (LAS VEGAS, NV) 11 5"
    assert directory_match(r, page) is True


def test_fines_join_only_by_exact_ccn():
    rows = [
        {"CMS Certification Number (CCN)": "295090", "Penalty Type": "Fine", "Fine Amount": "1500", "Penalty Date": "2026-01-01"},
        {"CMS Certification Number (CCN)": "295090", "Penalty Type": "Payment Denial", "Fine Amount": "", "Penalty Date": "2026-01-02"},
        {"CMS Certification Number (CCN)": "999999", "Penalty Type": "Fine", "Fine Amount": "999999", "Penalty Date": "2026-01-03"},
    ]
    result = audit_fines([record()], rows)
    assert result["covered_facilities_with_any_penalty"] == 1
    assert result["fine_rows"] == 1
    assert result["payment_denial_rows"] == 1
    assert result["fine_amount_total_last_3_years"] == 1500.0


def test_snf_scope_excludes_non_snf_and_non_valley():
    good = record()
    not_snf = {**record(ccn="1"), "canonical_type": "ASSISTED_LIVING_RFG"}
    not_valley = {**record(ccn="2"), "is_las_vegas_valley": False}
    assert snf_valley([good, not_snf, not_valley]) == [good]
