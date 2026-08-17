from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from enrich_nevada_alis_details import parse_official_detail, parse_inspection_rows  # noqa: E402
from finalize_nevada_canonical_universe import build  # noqa: E402


def alis(name="ALPHA CARE", address="100 MAIN ST", ccn="295001", memory="UNKNOWN"):
    evidence = "[]" if memory == "UNKNOWN" else '[{"field":"Endorsement","value":"ALZHEIMER DISEASE"}]'
    detail = '{"endorsements": [], "memory_bed_count": 0}' if memory == "UNKNOWN" else '{"endorsements":["ALZHEIMER DISEASE"],"memory_bed_count":9}'
    return {
        "facility_name": name,
        "license_type": "AGC",
        "license_number": "100-AGC-1",
        "status": "Active",
        "expiration_date": "12/31/2026",
        "disciplinary_action": "N",
        "address": address,
        "city": "LAS VEGAS",
        "state": "NV",
        "zip": "89101",
        "phone": "7025550000",
        "first_issue_date": "01/01/2020",
        "primary_contact_name": "ADMIN ONE",
        "primary_contact_role": "Administrator",
        "capacity": "9",
        "federal_provider_number": ccn,
        "detail_url": "https://example.invalid/detail",
        "official_detail": detail,
        "memory_care_evidence": evidence,
        "memory_care_classification": "CONFIRMED_OFFICIAL_DETAIL" if memory != "UNKNOWN" else "UNKNOWN",
        "county": "Clark",
        "is_clark_county": "true",
        "is_las_vegas_valley": "true",
    }


def cms(ccn="295001", name="ALPHA CARE", address="100 MAIN STREET"):
    return {
        "CMS Certification Number (CCN)": ccn,
        "Provider Name": name,
        "Provider Address": address,
        "City/Town": "LAS VEGAS",
        "State": "NV",
        "ZIP Code": "89101",
        "County/Parish": "Clark",
        "Telephone Number": "7025550000",
        "Number of Certified Beds": "9",
        "Ownership Type": "For profit",
        "Overall Rating": "4",
        "Health Inspection Rating": "4",
        "Staffing Rating": "3",
        "QM Rating": "5",
        "Processing Date": "2026-07-01",
    }


def test_exact_ccn_is_strongest_identity():
    payload = build([alis()], [cms()], [])
    assert payload["report"]["merge_methods"]["EXACT_CCN"] == 1
    assert payload["report"]["canonical_facilities_unique"] == 1


def test_live_cms_ccn_header_is_supported():
    payload = build([alis(ccn="295888")], [cms(ccn="295888")], [])
    assert payload["report"]["source_identity_merges"] == 1
    assert payload["records"][0]["cms_ccn"] == "295888"


def test_exact_normalized_name_address_fallback_is_allowed():
    payload = build([alis(ccn="")], [cms(ccn="295999")], [])
    assert payload["report"]["merge_methods"]["EXACT_NORMALIZED_NAME_ADDRESS_CITY_ZIP"] == 1
    assert payload["report"]["canonical_facilities_unique"] == 1


def test_truncated_cms_name_requires_exact_normalized_address():
    a = alis(name="CORONADO RIDGE SKILLED NURSING AND REHABILITATION CENTER", address="2855 W HORIZON RIDGE PKWY", ccn="")
    a["license_type"] = "SNF"
    row = cms(ccn="295012", name="CORONADO RIDGE SKILLED NURSING & REHABILITATION CE", address="2855 WEST HORIZON RIDGE PARKWAY")
    payload = build([a], [row], [])
    assert payload["report"]["merge_methods"]["EXACT_NORMALIZED_ADDRESS_COMPATIBLE_TRUNCATED_NAME"] == 1
    assert payload["report"]["canonical_facilities_unique"] == 1


def test_same_address_different_name_does_not_merge():
    payload = build([alis(ccn="")], [cms(ccn="295999", name="UNRELATED FACILITY")], [])
    assert payload["report"]["merge_methods"]["CMS_ONLY"] == 1
    assert payload["report"]["canonical_facilities_unique"] == 2


def test_same_name_different_address_does_not_merge():
    payload = build([alis(ccn="")], [cms(ccn="295999", address="999 OTHER ROAD")], [])
    assert payload["report"]["merge_methods"]["CMS_ONLY"] == 1
    assert payload["report"]["canonical_facilities_unique"] == 2


def test_memory_care_requires_official_detail_evidence():
    unknown = build([alis(memory="UNKNOWN")], [], [])
    confirmed = build([alis(memory="CONFIRMED")], [], [])
    assert unknown["report"]["memory_care_confirmed"] == 0
    assert confirmed["report"]["memory_care_confirmed"] == 1


def test_senior_name_business_license_remains_candidate_unknown():
    business = [{
        "license_number": "A01-1", "business_name": "SUNSET SENIOR APARTMENTS", "license_category": "Apartment House",
        "license_status": "Active", "address": "1 SUNSET ST", "city": "Las Vegas", "state": "NV", "zip": "89101",
        "independent_living_classification": "CANDIDATE_NAME_SIGNAL",
    }]
    payload = build([alis()], [], business)
    assert payload["report"]["independent_living_confirmed"] == 0
    assert payload["report"]["independent_living_candidates_unknown_active_unique"] == 1
    assert payload["independent_living_discovery_candidates"][0]["classification"] == "INDEPENDENT_LIVING_CANDIDATE_UNKNOWN"


def test_distinct_licenses_same_campus_are_grouped_not_merged():
    a = alis(ccn="")
    b = dict(a)
    b["license_number"] = "101-SNF-1"
    b["license_type"] = "SNF"
    b["facility_name"] = "ALPHA NURSING"
    payload = build([a, b], [], [])
    assert payload["report"]["canonical_facilities_unique"] == 2
    assert payload["report"]["mixed_campuses"] == 1


def test_inspection_grid_parser_extracts_sod_identity():
    html = '''<table id="ctl00_ContentPlaceHolder1_ucSODgrid_ResultsGrid"><tbody>
    <tr><td>01/01/2026</td><td>123</td><td>EV1</td><td>A</td><td>View SOD/POC <span id="x_lblCount">(2)</span>
    <input id="x_hdInspectionId" value="I1"/><input id="x_hdSODId" value="S1"/>
    <input id="x_hdSODStatusCode" value="C"/><input id="x_hdSODStatusReasonCode" value="R"/>
    <input id="x_hdInspectionSourceCode" value="SRC"/></td></tr></tbody></table>'''
    rows = parse_inspection_rows(html)
    assert len(rows) == 1
    assert rows[0]["inspection_id"] == "I1"
    assert rows[0]["sod_id"] == "S1"
    assert rows[0]["sod_poc_available"] is True
    assert rows[0]["document_count"] == 2


def test_detail_parser_does_not_confirm_zero_alzheimer_boilerplate():
    raw = b'''<html><body>Credential Category-II (Alzheimer's)
    <input id="x_txtCount" value="0" /> Total Count: Count = 9</body></html>'''
    detail = parse_official_detail(raw, "https://example.invalid")
    assert detail["memory_care_official_detail_evidence"] is False
