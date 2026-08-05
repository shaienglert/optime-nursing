from __future__ import annotations

import csv
import importlib.util
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.canonical_universe import configured_canonical_market, resolve_canonical_universe_path


SCRIPT_PATH = REPO_ROOT / "scripts" / "build_nevada_canonical_universe.py"
SPEC = importlib.util.spec_from_file_location("build_nevada_canonical_universe", SCRIPT_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILDER
SPEC.loader.exec_module(BUILDER)

RETRIEVED_AT = "2026-08-04T00:00:00+00:00"
HEADERS = [
    "license_id", "cms_ccn", "npi", "facility_name", "legal_name", "dba",
    "operator_name", "owner_name", "facility type", "address", "address 2",
    "city", "county", "state", "zip", "phone", "website", "capacity",
    "status", "effective date", "expiration date", "source_record_id",
]


def license_row(**overrides: str) -> dict[str, str]:
    row = {
        "license_id": "RFG-100",
        "cms_ccn": "",
        "npi": "",
        "facility_name": "Desert View Senior Living",
        "legal_name": "Desert View Nevada LLC",
        "dba": "",
        "operator_name": "Desert Operator",
        "owner_name": "Desert View Nevada LLC",
        "facility type": "Residential Facility for Groups",
        "address": "100 Main Street",
        "address 2": "",
        "city": "Las Vegas",
        "county": "Clark",
        "state": "NV",
        "zip": "89101",
        "phone": "7025550100",
        "website": "",
        "capacity": "80",
        "status": "ACTIVE",
        "effective date": "2025-01-01",
        "expiration date": "2026-12-31",
        "source_record_id": "RFG-100",
    }
    row.update(overrides)
    return row


class NevadaCanonicalUniverseTests(unittest.TestCase):
    def build(self, rows: list[dict[str, str]]):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            cms_path = directory / "cms.csv"
            license_path = directory / "licenses.csv"
            with cms_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "CMS Certification Number (CCN)", "Provider Name", "Provider Address",
                    "City/Town", "State", "ZIP Code", "Telephone Number", "County/Parish",
                    "Provider Type", "Legal Business Name", "Chain Name", "Number of Certified Beds",
                    "Processing Date",
                ])
                writer.writeheader()
            with license_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerows(rows)
            return BUILDER.build_universe(cms_path, license_path, None, RETRIEVED_AT)

    def build_with_nppes(self, cms_rows: list[dict[str, str]], nppes_rows: list[dict[str, str]]):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            cms_path = directory / "cms.csv"
            nppes_zip_path = directory / "nppes.zip"
            taxonomy_lookup_path = directory / "taxonomy.csv"
            with cms_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "CMS Certification Number (CCN)", "Provider Name", "Provider Address",
                    "City/Town", "State", "ZIP Code", "Telephone Number", "County/Parish",
                    "Provider Type", "Legal Business Name", "Chain Name", "Number of Certified Beds",
                    "Processing Date",
                ])
                writer.writeheader()
                writer.writerows(cms_rows)
            with taxonomy_lookup_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["taxonomy_code", "taxonomy_desc"])
                writer.writeheader()
                writer.writerow({"taxonomy_code": "310400000X", "taxonomy_desc": "Assisted Living Facility"})
                writer.writerow({"taxonomy_code": "311500000X", "taxonomy_desc": "Alzheimer Center (Dementia Center)"})
                writer.writerow({"taxonomy_code": "314000000X", "taxonomy_desc": "Skilled Nursing Facility"})
            npi_headers = [
                "NPI", "Entity Type Code", "Provider Organization Name (Legal Business Name)", "Provider Other Organization Name",
                "Provider First Line Business Mailing Address", "Provider Second Line Business Mailing Address",
                "Provider Business Mailing Address City Name", "Provider Business Mailing Address State Name",
                "Provider Business Mailing Address Postal Code", "Provider Business Mailing Address Telephone Number",
                "Provider First Line Business Practice Location Address", "Provider Second Line Business Practice Location Address",
                "Provider Business Practice Location Address City Name", "Provider Business Practice Location Address State Name",
                "Provider Business Practice Location Address Postal Code", "Provider Business Practice Location Address Telephone Number",
                "Provider Enumeration Date", "Last Update Date", "NPI Deactivation Date",
                "Healthcare Provider Taxonomy Code_1", "Provider License Number_1", "Provider License Number State Code_1", "Healthcare Provider Primary Taxonomy Switch_1",
                "Healthcare Provider Taxonomy Code_2", "Provider License Number_2", "Provider License Number State Code_2", "Healthcare Provider Primary Taxonomy Switch_2",
            ]
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=npi_headers)
            writer.writeheader()
            for row in nppes_rows:
                writer.writerow(row)
            with zipfile.ZipFile(nppes_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("npidata_pfile_test.csv", buffer.getvalue())
            return BUILDER.build_universe(cms_path, None, nppes_zip_path, RETRIEVED_AT, taxonomy_lookup_path)

    def test_duplicate_records_sharing_exact_license_id_merge(self) -> None:
        payload, report = self.build([license_row(), license_row(source_record_id="RFG-100-REFRESH")])
        self.assertEqual(payload["record_count"], 1)
        self.assertEqual(report["duplicates_merged"], 1)
        self.assertEqual(len(payload["records"][0]["source_evidence"]), 2)
        self.assertIn("exact_nevada_license_id", payload["records"][0]["merge_evidence"])

    def test_same_name_different_addresses_stay_separate(self) -> None:
        payload, _ = self.build([
            license_row(license_id="RFG-101", source_record_id="RFG-101"),
            license_row(license_id="RFG-102", source_record_id="RFG-102", address="900 Other Road", zip="89109"),
        ])
        self.assertEqual(payload["record_count"], 2)
        self.assertTrue(all(record["duplicate_candidate"] for record in payload["records"]))

    def test_dba_change_same_license_and_address_preserves_alias(self) -> None:
        payload, _ = self.build([license_row(dba="Desert View"), license_row(dba="Desert Vista", source_record_id="RFG-100-NEW")])
        record = payload["records"][0]
        self.assertEqual(record["canonical_id"], "NV-LIC-RFG-100")
        self.assertIn("dba", record["identity_conflicts"])
        self.assertIn("Desert Vista", record["aliases"])

    def test_operator_change_is_retained_as_conflict(self) -> None:
        payload, _ = self.build([license_row(), license_row(operator_name="New Operator", source_record_id="RFG-100-NEW")])
        self.assertEqual(payload["record_count"], 1)
        self.assertEqual(payload["records"][0]["identity_conflicts"]["operator_name"], ["Desert Operator", "New Operator"])

    def test_facility_move_is_retained_as_address_conflict(self) -> None:
        payload, _ = self.build([license_row(), license_row(address="200 New Street", source_record_id="RFG-100-MOVED")])
        self.assertEqual(payload["record_count"], 1)
        self.assertIn("address", payload["records"][0]["identity_conflicts"])

    def test_closed_facility_is_preserved(self) -> None:
        payload, _ = self.build([license_row(status="CLOSED")])
        self.assertEqual(payload["records"][0]["license_status"], "CLOSED")

    def test_cms_and_nevada_address_conflict_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            cms_path = directory / "cms.csv"
            license_path = directory / "licenses.csv"
            cms_headers = ["CMS Certification Number (CCN)", "Provider Name", "Provider Address", "City/Town", "State", "ZIP Code", "Telephone Number", "County/Parish", "Provider Type", "Legal Business Name", "Chain Name", "Number of Certified Beds", "Processing Date"]
            with cms_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=cms_headers)
                writer.writeheader()
                writer.writerow({"CMS Certification Number (CCN)": "295999", "Provider Name": "Desert View Senior Living", "Provider Address": "300 CMS Avenue", "City/Town": "Las Vegas", "State": "NV", "ZIP Code": "89101", "Telephone Number": "7025550100", "County/Parish": "Clark", "Provider Type": "Medicare and Medicaid", "Legal Business Name": "Desert View Nevada LLC", "Chain Name": "", "Number of Certified Beds": "80", "Processing Date": "2026-07-01"})
            with license_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADERS)
                writer.writeheader()
                writer.writerow(license_row(cms_ccn="295999"))
            payload, _ = BUILDER.build_universe(cms_path, license_path, None, RETRIEVED_AT)
        self.assertEqual(payload["record_count"], 1)
        self.assertIn("address", payload["records"][0]["identity_conflicts"])

    def test_phone_conflict_is_visible(self) -> None:
        payload, _ = self.build([license_row(), license_row(phone="7025550199", source_record_id="RFG-100-PHONE")])
        self.assertIn("phone", payload["records"][0]["identity_conflicts"])

    def test_missing_phone_does_not_exclude_identity(self) -> None:
        payload, report = self.build([license_row(phone="")])
        self.assertEqual(payload["record_count"], 1)

    def test_nppes_only_assisted_living_record_is_added(self) -> None:
        payload, report = self.build_with_nppes(
            [],
            [
                {
                    "NPI": "1234567890",
                    "Entity Type Code": "2",
                    "Provider Organization Name (Legal Business Name)": "Sunrise Nevada LLC",
                    "Provider Other Organization Name": "Sunrise Assisted Living",
                    "Provider First Line Business Mailing Address": "100 Main Street",
                    "Provider Second Line Business Mailing Address": "",
                    "Provider Business Mailing Address City Name": "Las Vegas",
                    "Provider Business Mailing Address State Name": "NV",
                    "Provider Business Mailing Address Postal Code": "89101",
                    "Provider Business Mailing Address Telephone Number": "7025550100",
                    "Provider First Line Business Practice Location Address": "100 Main Street",
                    "Provider Second Line Business Practice Location Address": "",
                    "Provider Business Practice Location Address City Name": "Las Vegas",
                    "Provider Business Practice Location Address State Name": "NV",
                    "Provider Business Practice Location Address Postal Code": "89101",
                    "Provider Business Practice Location Address Telephone Number": "7025550100",
                    "Provider Enumeration Date": "01/01/2020",
                    "Last Update Date": "07/01/2026",
                    "NPI Deactivation Date": "",
                    "Healthcare Provider Taxonomy Code_1": "310400000X",
                    "Provider License Number_1": "AL-100",
                    "Provider License Number State Code_1": "NV",
                    "Healthcare Provider Primary Taxonomy Switch_1": "Y",
                    "Healthcare Provider Taxonomy Code_2": "",
                    "Provider License Number_2": "",
                    "Provider License Number State Code_2": "",
                    "Healthcare Provider Primary Taxonomy Switch_2": "",
                }
            ],
        )
        self.assertEqual(payload["record_count"], 1)
        self.assertEqual(payload["records"][0]["facility_type"], "Assisted Living")
        self.assertEqual(report["records_with_npi"], 1)

    def test_nppes_merges_with_cms_on_exact_address_and_phone(self) -> None:
        payload, report = self.build_with_nppes(
            [
                {
                    "CMS Certification Number (CCN)": "295006",
                    "Provider Name": "Las Vegas Post Acute & Rehabilitation",
                    "Provider Address": "100 Main Street",
                    "City/Town": "Las Vegas",
                    "State": "NV",
                    "ZIP Code": "89101",
                    "Telephone Number": "7025550100",
                    "County/Parish": "Clark",
                    "Provider Type": "Medicare and Medicaid",
                    "Legal Business Name": "Las Vegas Post Acute & Rehabilitation LLC",
                    "Chain Name": "",
                    "Number of Certified Beds": "80",
                    "Processing Date": "2026-07-01",
                }
            ],
            [
                {
                    "NPI": "1234567890",
                    "Entity Type Code": "2",
                    "Provider Organization Name (Legal Business Name)": "Las Vegas Post Acute & Rehabilitation LLC",
                    "Provider Other Organization Name": "Las Vegas Post Acute & Rehabilitation",
                    "Provider First Line Business Mailing Address": "100 Main Street",
                    "Provider Second Line Business Mailing Address": "",
                    "Provider Business Mailing Address City Name": "Las Vegas",
                    "Provider Business Mailing Address State Name": "NV",
                    "Provider Business Mailing Address Postal Code": "89101",
                    "Provider Business Mailing Address Telephone Number": "7025550100",
                    "Provider First Line Business Practice Location Address": "100 Main Street",
                    "Provider Second Line Business Practice Location Address": "",
                    "Provider Business Practice Location Address City Name": "Las Vegas",
                    "Provider Business Practice Location Address State Name": "NV",
                    "Provider Business Practice Location Address Postal Code": "89101",
                    "Provider Business Practice Location Address Telephone Number": "7025550100",
                    "Provider Enumeration Date": "01/01/2020",
                    "Last Update Date": "07/01/2026",
                    "NPI Deactivation Date": "",
                    "Healthcare Provider Taxonomy Code_1": "314000000X",
                    "Provider License Number_1": "",
                    "Provider License Number State Code_1": "",
                    "Healthcare Provider Primary Taxonomy Switch_1": "Y",
                    "Healthcare Provider Taxonomy Code_2": "",
                    "Provider License Number_2": "",
                    "Provider License Number State Code_2": "",
                    "Healthcare Provider Primary Taxonomy Switch_2": "",
                }
            ],
        )
        self.assertEqual(payload["record_count"], 1)
        self.assertEqual(payload["records"][0]["cms_certification_number"], "295006")
        self.assertEqual(payload["records"][0]["npi"], "1234567890")
        self.assertEqual(payload["records"][0]["phone"], "7025550100")
        self.assertEqual(report["complete_authoritative_identities"], 1)

    def test_las_vegas_valley_classifications(self) -> None:
        rows = [
            license_row(license_id="RFG-LV", source_record_id="RFG-LV", city="Las Vegas"),
            license_row(license_id="RFG-HEN", source_record_id="RFG-HEN", city="Henderson"),
            license_row(license_id="RFG-NLV", source_record_id="RFG-NLV", city="North Las Vegas"),
            license_row(license_id="RFG-RENO", source_record_id="RFG-RENO", city="Reno", county="Washoe", zip="89501"),
        ]
        payload, _ = self.build(rows)
        by_city = {record["city"]: record for record in payload["records"]}
        self.assertTrue(by_city["Las Vegas"]["is_las_vegas_valley"])
        self.assertTrue(by_city["Henderson"]["is_las_vegas_valley"])
        self.assertTrue(by_city["North Las Vegas"]["is_las_vegas_valley"])
        self.assertFalse(by_city["Reno"]["is_las_vegas_valley"])

    def test_canonical_id_is_stable_across_dba_and_operator_changes(self) -> None:
        first, _ = self.build([license_row(dba="Old Name")])
        second, _ = self.build([license_row(dba="New Name", operator_name="New Operator")])
        self.assertEqual(first["records"][0]["canonical_id"], second["records"][0]["canonical_id"])

    def test_rebuild_is_idempotent_for_fixed_retrieval_timestamp(self) -> None:
        first, first_report = self.build([license_row()])
        second, second_report = self.build([license_row()])
        self.assertEqual(first, second)
        first_report.pop("processing_time_seconds", None)
        second_report.pop("processing_time_seconds", None)
        self.assertEqual(first_report, second_report)

    def test_nevada_output_has_unique_ids_and_no_florida_records(self) -> None:
        payload, report = self.build([license_row(), license_row(license_id="RFG-RENO", source_record_id="RFG-RENO", city="Reno", county="Washoe", zip="89501")])
        ids = [record["canonical_id"] for record in payload["records"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(record["state"] == "NV" for record in payload["records"]))
        self.assertEqual(report["schema_validation_errors"], [])

    def test_missing_optional_fields_remain_unknown_or_null(self) -> None:
        payload, _ = self.build([license_row(website="", npi="", cms_ccn="")])
        record = payload["records"][0]
        self.assertIsNone(record["website"])
        self.assertIsNone(record["npi"])
        self.assertEqual(record["availability"], "UNKNOWN")

    def test_existing_canonical_consumers_receive_compatible_fields(self) -> None:
        payload, _ = self.build([license_row(cms_ccn="295999", npi="1234567890")])
        record = payload["records"][0]
        required_fields = {
            "canonical_id", "canonical_type", "facility_name", "source_identity_ids",
            "source_evidence", "address", "city", "county", "zip", "phone",
            "license_status", "licensed_beds_capacity", "facility_type", "availability",
            "source_retrieved_at", "source_record_id",
        }
        self.assertEqual(required_fields - record.keys(), set())


class CanonicalUniverseLoaderTests(unittest.TestCase):
    def test_florida_and_nevada_resolve_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            florida = directory / "florida_facility_universe_canonical.json"
            nevada = directory / "nevada_facility_universe_canonical.json"
            florida.write_text("{}", encoding="utf-8")
            nevada.write_text("{}", encoding="utf-8")
            self.assertEqual(resolve_canonical_universe_path("florida", database_dir=directory), florida)
            self.assertEqual(resolve_canonical_universe_path("las-vegas", database_dir=directory), nevada)

    def test_las_vegas_missing_universe_raises_instead_of_using_florida(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "florida_facility_universe_canonical.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                resolve_canonical_universe_path("las-vegas", database_dir=directory)

    def test_unsupported_market_is_explicit_error(self) -> None:
        with self.assertRaises(ValueError):
            resolve_canonical_universe_path("california", require_exists=False)

    def test_configuration_alias_resolves_las_vegas(self) -> None:
        with patch.dict("os.environ", {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=True):
            self.assertEqual(configured_canonical_market(), "las-vegas")


if __name__ == "__main__":
    unittest.main()