from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import tracemalloc
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from io import TextIOWrapper


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CMS_SOURCE = REPO_ROOT / "backend" / "app" / "data" / "provider_information.csv"
DEFAULT_OUTPUT = REPO_ROOT / "database" / "nevada_facility_universe_canonical.json"
DEFAULT_REPORT_JSON = REPO_ROOT / "reports" / "NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.json"
DEFAULT_REPORT_MD = REPO_ROOT / "reports" / "NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md"
DEFAULT_TAXONOMY_LOOKUP = REPO_ROOT / "data" / "nppes" / "raw" / "fl_facilities_nppes.csv"

SCHEMA_VERSION = "nevada-canonical-facility-v1.0.0"
CMS_DATASET_ID = "4pq5-n9py"
CMS_DATASET_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py"
NEVADA_HCQC_URL = "https://nvdpbh.aithent.com/login.aspx"
NPPES_URL = "https://download.cms.gov/nppes/NPI_Files.html"
LAS_VEGAS_VALLEY_CITIES = {
    "las vegas",
    "north las vegas",
    "henderson",
    "paradise",
    "spring valley",
    "enterprise",
    "summerlin",
    "centennial hills",
    "boulder city",
    "mesquite",
    "laughlin",
}

NPPES_RESIDENTIAL_KEYWORDS = (
    "assisted living facility",
    "skilled nursing facility",
    "nursing care",
    "nursing facility",
    "alzheimer center",
    "dementia center",
    "continuing care retirement community",
    "community based residential treatment facility",
    "adult care home",
)

FIELD_ALIASES = {
    "license_id": ("license_id", "license number", "license_number", "facility license number"),
    "cms_ccn": ("cms_ccn", "ccn", "cms certification number"),
    "npi": ("npi", "national provider identifier"),
    "facility_name": ("facility_name", "facility name", "name", "provider name"),
    "legal_name": ("legal_name", "legal name", "licensee", "entity name"),
    "dba": ("dba", "doing business as", "trade name"),
    "operator_name": ("operator_name", "operator name", "administrator"),
    "owner_name": ("owner_name", "owner name", "licensee"),
    "source_facility_type": ("source_facility_type", "facility type", "type", "category"),
    "address": ("address", "street address", "address 1", "provider address"),
    "address_line_2": ("address_line_2", "address 2", "suite"),
    "city": ("city", "city/town"),
    "county": ("county", "county/parish"),
    "state": ("state",),
    "zip": ("zip", "zip code", "postal code"),
    "phone": ("phone", "telephone", "telephone number", "public phone"),
    "website": ("website", "website url"),
    "capacity": ("capacity", "licensed capacity", "licensed beds", "number of certified beds"),
    "status": ("status", "license status"),
    "effective_date": ("effective_date", "effective date", "license effective date"),
    "expiration_date": ("expiration_date", "expiration date", "license expiration date"),
    "source_record_id": ("source_record_id", "record id", "license number"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def normalize_phone(value: Any) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def normalize_zip(value: Any) -> str:
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", str(value or ""))
    return match.group(1) if match else ""


def normalize_address(value: Any) -> str:
    text = f" {normalize_text(value)} "
    replacements = {" st ": " street ", " rd ": " road ", " ave ": " avenue ", " blvd ": " boulevard ", " dr ": " drive ", " hwy ": " highway "}
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def row_value(row: dict[str, Any], field: str) -> str:
    normalized = {normalize_text(key): value for key, value in row.items()}
    for alias in FIELD_ALIASES[field]:
        value = normalized.get(normalize_text(alias))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_facility_type(source_type: str) -> str:
    value = normalize_text(source_type)
    if "residential facility for groups" in value or "assisted living" in value:
        return "Assisted Living"
    if "alzheimer center" in value or "dementia center" in value or "memory care" in value:
        return "Memory Care"
    if "skilled nursing" in value:
        return "Skilled Nursing Facility"
    if "nursing facility" in value or "nursing home" in value:
        return "Nursing Facility"
    if "continuing care" in value or "life plan" in value:
        return "Continuing Care / Life Plan"
    return "Other Governed Senior-Care Residential" if value else "UNKNOWN"


def classify_nppes_role(source_type: str) -> str:
    value = normalize_text(source_type)
    if any(keyword in value for keyword in NPPES_RESIDENTIAL_KEYWORDS):
        return "RESIDENTIAL_CANDIDATE"
    return "OUT_OF_SCOPE"


def load_taxonomy_lookup(path: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if not path.is_file():
        return lookup
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            code = str(row.get("taxonomy_code") or "").strip()
            desc = str(row.get("taxonomy_desc") or "").strip()
            if code and desc and code not in lookup:
                lookup[code] = desc
    return lookup


def is_las_vegas_valley(city: str, county: str) -> bool:
    normalized_city = normalize_text(city)
    normalized_county = normalize_text(county)
    return normalized_city in LAS_VEGAS_VALLEY_CITIES and normalized_county == "clark"


def stable_composite_id(row: dict[str, Any]) -> str:
    material = "|".join((normalize_text(row.get("facility_name")), normalize_address(row.get("address")), normalize_zip(row.get("zip"))))
    return f"NV-COMPOSITE-{hashlib.sha256(material.encode('utf-8')).hexdigest()[:16].upper()}"


def canonical_id_for(row: dict[str, Any]) -> str:
    if row.get("nevada_license_id"):
        return f"NV-LIC-{re.sub(r'[^A-Za-z0-9]+', '-', str(row['nevada_license_id']).strip()).strip('-').upper()}"
    if row.get("cms_ccn"):
        return f"CMS-{row['cms_ccn']}"
    if row.get("npi"):
        return f"NPI-{row['npi']}"
    return stable_composite_id(row)


def cms_rows(path: Path, retrieved_at: str) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("State") or "").strip().upper() != "NV":
                continue
            yield {
                "source": "CMS Provider Information",
                "source_authority": "Federal government",
                "source_url": CMS_DATASET_URL,
                "dataset_identifier": CMS_DATASET_ID,
                "source_update_date": str(row.get("Processing Date") or "").strip() or None,
                "retrieved_at": retrieved_at,
                "source_record_id": str(row.get("CMS Certification Number (CCN)") or "").strip(),
                "facility_name": str(row.get("Provider Name") or "").strip(),
                "legal_name": str(row.get("Legal Business Name") or "").strip() or None,
                "dba": None,
                "operator_name": str(row.get("Chain Name") or "").strip() or None,
                "owner_name": str(row.get("Legal Business Name") or "").strip() or None,
                "source_facility_type": "Skilled Nursing Facility",
                "address": str(row.get("Provider Address") or "").strip(),
                "address_line_2": None,
                "city": str(row.get("City/Town") or "").strip(),
                "county": str(row.get("County/Parish") or "").strip(),
                "state": "NV",
                "zip": normalize_zip(row.get("ZIP Code")),
                "phone": normalize_phone(row.get("Telephone Number")) or None,
                "website": None,
                "nevada_license_id": None,
                "cms_ccn": str(row.get("CMS Certification Number (CCN)") or "").strip() or None,
                "npi": None,
                "licensed_capacity": None,
                "certified_beds": str(row.get("Number of Certified Beds") or "").strip() or None,
                "status": "ACTIVE",
                "license_effective_date": None,
                "license_expiration_date": None,
            }


def nppes_rows(path: Path, retrieved_at: str, taxonomy_lookup: dict[str, str]) -> Iterable[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        data_entry = next((name for name in archive.namelist() if name.lower().startswith("npidata_pfile_") and name.lower().endswith(".csv")), "")
        if not data_entry:
            return
        with archive.open(data_entry) as raw_handle:
            reader = csv.DictReader(TextIOWrapper(raw_handle, encoding="utf-8", errors="replace", newline=""))
            for row in reader:
                entity_type = str(row.get("Entity Type Code") or "").strip()
                if entity_type != "2":
                    continue

                state = str(row.get("Provider Business Practice Location Address State Name") or row.get("Provider Business Mailing Address State Name") or "").strip().upper()
                if state != "NV":
                    continue

                facility_name = str(row.get("Provider Other Organization Name") or row.get("Provider Organization Name (Legal Business Name)") or "").strip()
                legal_name = str(row.get("Provider Organization Name (Legal Business Name)") or "").strip() or None
                dba = str(row.get("Provider Other Organization Name") or "").strip() or None
                address = str(row.get("Provider First Line Business Practice Location Address") or row.get("Provider First Line Business Mailing Address") or "").strip()
                city = str(row.get("Provider Business Practice Location Address City Name") or row.get("Provider Business Mailing Address City Name") or "").strip()
                postal_code = normalize_zip(row.get("Provider Business Practice Location Address Postal Code") or row.get("Provider Business Mailing Address Postal Code"))
                phone = normalize_phone(row.get("Provider Business Practice Location Address Telephone Number") or row.get("Provider Business Mailing Address Telephone Number")) or None
                npi = str(row.get("NPI") or "").strip() or None
                active = not str(row.get("NPI Deactivation Date") or "").strip()

                for index in range(1, 16):
                    taxonomy_code = str(row.get(f"Healthcare Provider Taxonomy Code_{index}") or "").strip()
                    if not taxonomy_code:
                        continue
                    taxonomy_desc = taxonomy_lookup.get(taxonomy_code, taxonomy_code)
                    if classify_nppes_role(taxonomy_desc) != "RESIDENTIAL_CANDIDATE":
                        continue
                    license_number = str(row.get(f"Provider License Number_{index}") or "").strip() or None
                    license_state = str(row.get(f"Provider License Number State Code_{index}") or "").strip().upper()
                    if license_number and license_state != "NV":
                        license_number = None
                    yield {
                        "source": "NPPES NPI Registry",
                        "source_authority": "Federal government",
                        "source_url": NPPES_URL,
                        "dataset_identifier": path.name,
                        "source_update_date": str(row.get("Last Update Date") or "").strip() or None,
                        "retrieved_at": retrieved_at,
                        "source_record_id": f"{npi or 'UNKNOWN'}:{taxonomy_code}:{index}",
                        "facility_name": facility_name,
                        "legal_name": legal_name,
                        "dba": dba,
                        "operator_name": legal_name,
                        "owner_name": legal_name,
                        "source_facility_type": taxonomy_desc,
                        "address": address,
                        "address_line_2": str(row.get("Provider Second Line Business Practice Location Address") or row.get("Provider Second Line Business Mailing Address") or "").strip() or None,
                        "city": city,
                        "county": "Clark" if is_las_vegas_valley(city, "Clark") else "UNKNOWN",
                        "state": "NV",
                        "zip": postal_code,
                        "phone": phone,
                        "website": None,
                        "nevada_license_id": None,
                        "cms_ccn": None,
                        "npi": npi,
                        "licensed_capacity": None,
                        "certified_beds": None,
                        "status": "ACTIVE" if active else "INACTIVE",
                        "license_effective_date": str(row.get("Provider Enumeration Date") or "").strip() or None,
                        "license_expiration_date": None,
                        "taxonomy_code": taxonomy_code,
                    }


def nevada_license_rows(path: Path, retrieved_at: str) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for source_row in csv.DictReader(handle):
            state = row_value(source_row, "state").upper() or "NV"
            if state not in {"NV", "NEVADA"}:
                continue
            yield {
                "source": "Nevada HCQC Health Facility Licensing",
                "source_authority": "Nevada state licensing authority",
                "source_url": NEVADA_HCQC_URL,
                "dataset_identifier": path.name,
                "source_update_date": None,
                "retrieved_at": retrieved_at,
                "source_record_id": row_value(source_row, "source_record_id") or row_value(source_row, "license_id"),
                "facility_name": row_value(source_row, "facility_name"),
                "legal_name": row_value(source_row, "legal_name") or None,
                "dba": row_value(source_row, "dba") or None,
                "operator_name": row_value(source_row, "operator_name") or None,
                "owner_name": row_value(source_row, "owner_name") or None,
                "source_facility_type": row_value(source_row, "source_facility_type"),
                "address": row_value(source_row, "address"),
                "address_line_2": row_value(source_row, "address_line_2") or None,
                "city": row_value(source_row, "city"),
                "county": row_value(source_row, "county"),
                "state": "NV",
                "zip": normalize_zip(row_value(source_row, "zip")),
                "phone": normalize_phone(row_value(source_row, "phone")) or None,
                "website": row_value(source_row, "website") or None,
                "nevada_license_id": row_value(source_row, "license_id") or None,
                "cms_ccn": row_value(source_row, "cms_ccn") or None,
                "npi": row_value(source_row, "npi") or None,
                "licensed_capacity": row_value(source_row, "capacity") or None,
                "certified_beds": None,
                "status": row_value(source_row, "status").upper() or "UNKNOWN",
                "license_effective_date": row_value(source_row, "effective_date") or None,
                "license_expiration_date": row_value(source_row, "expiration_date") or None,
            }


def merge_sources(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    strong_indexes: dict[str, dict[str, int]] = {"license": {}, "ccn": {}, "npi": {}, "address_phone": {}}
    conflicts: list[dict[str, Any]] = []
    duplicates_merged = 0

    for row in rows:
        keys = {
            "license": str(row.get("nevada_license_id") or ""),
            "ccn": str(row.get("cms_ccn") or ""),
            "npi": str(row.get("npi") or ""),
            "address_phone": "|".join((
                normalize_address(row.get("address")),
                normalize_text(row.get("city")),
                normalize_zip(row.get("zip")),
                normalize_phone(row.get("phone")),
            )) if row.get("address") and row.get("city") and row.get("zip") and row.get("phone") else "",
        }
        matched = {strong_indexes[k][v] for k, v in keys.items() if v and v in strong_indexes[k]}
        if matched:
            index = min(matched)
            groups[index].append(row)
            duplicates_merged += 1
        else:
            index = len(groups)
            groups.append([row])
        for key, value in keys.items():
            if value:
                strong_indexes[key][value] = index

    records: list[dict[str, Any]] = []
    for source_rows in groups:
        state_rows = [row for row in source_rows if row["source"].startswith("Nevada HCQC")]
        cms_source_rows = [row for row in source_rows if row["source"].startswith("CMS")]
        primary = state_rows[0] if state_rows else source_rows[0]
        all_values: dict[str, list[str]] = defaultdict(list)
        for row in source_rows:
            for field in ("facility_name", "legal_name", "dba", "operator_name", "owner_name", "address", "city", "county", "zip", "phone", "status"):
                value = str(row.get(field) or "").strip()
                if value and value not in all_values[field]:
                    all_values[field].append(value)
        identity_conflicts = {field: values for field, values in all_values.items() if len({normalize_text(value) for value in values}) > 1}
        if identity_conflicts:
            conflicts.append({"source_record_ids": [row["source_record_id"] for row in source_rows], "fields": identity_conflicts})
        license_id = next((row.get("nevada_license_id") for row in state_rows if row.get("nevada_license_id")), None)
        ccn = next((row.get("cms_ccn") for row in cms_source_rows if row.get("cms_ccn")), None)
        npi = next((row.get("npi") for row in source_rows if row.get("npi")), None)
        merged = {**primary, "nevada_license_id": license_id, "cms_ccn": ccn, "npi": npi}
        canonical_id = canonical_id_for(merged)
        aliases = sorted({value for field in ("facility_name", "legal_name", "dba") for value in all_values[field] if normalize_text(value) != normalize_text(primary.get("facility_name"))})
        source_evidence = {
            f"{normalize_text(row['source']).replace(' ', '_')}:{row['source_record_id'] or index}": {
                "source_name": row["source"],
                "source_authority": row["source_authority"],
                "source_url": row["source_url"],
                "dataset_identifier": row["dataset_identifier"],
                "source_record_id": row["source_record_id"],
                "source_update_date": row["source_update_date"],
                "source_retrieved_at": row["retrieved_at"],
                "source_facility_type": row["source_facility_type"],
                "scope": "FACILITY",
            }
            for index, row in enumerate(source_rows, start=1)
        }
        merge_evidence = []
        if license_id and sum(row.get("nevada_license_id") == license_id for row in source_rows) > 1:
            merge_evidence.append("exact_nevada_license_id")
        if ccn and sum(row.get("cms_ccn") == ccn for row in source_rows) > 1:
            merge_evidence.append("exact_cms_ccn")
        if npi and sum(row.get("npi") == npi for row in source_rows) > 1:
            merge_evidence.append("exact_facility_npi")
        address_phone_keys = {
            "|".join((normalize_address(row.get("address")), normalize_text(row.get("city")), normalize_zip(row.get("zip")), normalize_phone(row.get("phone"))))
            for row in source_rows
            if row.get("address") and row.get("city") and row.get("zip") and row.get("phone")
        }
        if len(source_rows) > 1 and len(address_phone_keys) == 1:
            merge_evidence.append("exact_normalized_address_and_phone")
        records.append({
            "canonical_id": canonical_id,
            "canonical_type": "NEVADA_LICENSE" if license_id else "CMS_ONLY" if ccn else "NPI_ONLY" if npi else "COMPOSITE",
            "canonical_schema_version": SCHEMA_VERSION,
            "facility_name": primary["facility_name"],
            "legal_name": primary.get("legal_name"),
            "dba_trade_names": [primary["dba"]] if primary.get("dba") else [],
            "former_names": [],
            "operator_name": primary.get("operator_name"),
            "owner_name": primary.get("owner_name"),
            "facility_type": normalize_facility_type(primary.get("source_facility_type") or ""),
            "source_facility_type": primary.get("source_facility_type") or "UNKNOWN",
            "address": primary["address"],
            "address_line_2": primary.get("address_line_2"),
            "city": primary["city"],
            "county": primary.get("county") or "UNKNOWN",
            "state": "NV",
            "zip": primary["zip"],
            "phone": primary.get("phone"),
            "website": primary.get("website"),
            "nevada_license_id": license_id,
            "cms_certification_number": ccn,
            "ccn": ccn,
            "npi": npi,
            "licensed_beds_capacity": primary.get("licensed_capacity"),
            "certified_beds": next((row.get("certified_beds") for row in cms_source_rows if row.get("certified_beds")), None),
            "license_status": primary.get("status") or "UNKNOWN",
            "license_effective_date": primary.get("license_effective_date"),
            "license_expiration_date": primary.get("license_expiration_date"),
            "availability": "UNKNOWN",
            "availability_evidence_state": "UNKNOWN",
            "source_identity_ids": {key: value for key, value in {"nevada_license_id": license_id, "cms_ccn": ccn, "npi": npi}.items() if value},
            "source_evidence": source_evidence,
            "source_retrieved_at": max(row["retrieved_at"] for row in source_rows),
            "source_record_id": primary["source_record_id"],
            "identity_confidence": "HIGH" if license_id or ccn else "MEDIUM",
            "identity_conflicts": identity_conflicts,
            "aliases": aliases,
            "ownership_history": [
                {"owner_name": value, "effective_date": None, "source_record_ids": [row["source_record_id"] for row in source_rows if row.get("owner_name") == value]}
                for value in all_values["owner_name"]
            ],
            "name_change_history": [
                {"name": value, "effective_date": None, "source_record_ids": [row["source_record_id"] for row in source_rows if value in {row.get("facility_name"), row.get("legal_name"), row.get("dba")} ]}
                for value in sorted({value for field in ("facility_name", "legal_name", "dba") for value in all_values[field]})
            ],
            "merge_evidence": merge_evidence,
            "merge_confidence": "HIGH" if len(source_rows) > 1 else "NOT_MERGED",
            "source_precedence": "Nevada licensing > CMS > NPPES",
            "duplicate_candidate": False,
            "duplicate_candidate_reason": None,
            "is_las_vegas_valley": is_las_vegas_valley(primary["city"], primary.get("county") or ""),
            "market_name": "Las Vegas, Nevada" if is_las_vegas_valley(primary["city"], primary.get("county") or "") else "Other Nevada",
            "market_city_normalized": normalize_text(primary["city"]).title(),
        })
    records_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_name[normalize_text(record["facility_name"])].append(record)
    for same_name_records in records_by_name.values():
        if len(same_name_records) < 2:
            continue
        addresses = {normalize_address(record["address"]) for record in same_name_records}
        if len(addresses) < 2:
            continue
        for record in same_name_records:
            record["duplicate_candidate"] = True
            record["duplicate_candidate_reason"] = "Same normalized facility name appears at a different address; weak name-only evidence is insufficient to merge."
    records.sort(key=lambda row: row["canonical_id"])
    return records, {"duplicates_merged": duplicates_merged, "conflicts": conflicts}


def complete_identity(record: dict[str, Any]) -> bool:
    return all(record.get(field) for field in ("canonical_id", "facility_name", "address", "city", "state", "zip", "source_evidence"))


def validate_records(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if record.get("state") != "NV":
            errors.append(f"{prefix}.state must equal NV")
        canonical_id = str(record.get("canonical_id") or "")
        if not canonical_id:
            errors.append(f"{prefix}.canonical_id is required")
        elif canonical_id in ids:
            errors.append(f"duplicate canonical_id: {canonical_id}")
        ids.add(canonical_id)
        if record.get("zip") and not re.fullmatch(r"\d{5}", str(record["zip"])):
            errors.append(f"{prefix}.zip is invalid")
        if record.get("phone") and not re.fullmatch(r"\d{10}", str(record["phone"])):
            errors.append(f"{prefix}.phone is invalid")
    return errors


def build_universe(cms_source: Path, nevada_license_source: Path | None, nppes_source: Path | None, retrieved_at: str, taxonomy_lookup_path: Path = DEFAULT_TAXONOMY_LOOKUP) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_counts: Counter[str] = Counter()
    taxonomy_lookup = load_taxonomy_lookup(taxonomy_lookup_path)

    def all_rows() -> Iterable[dict[str, Any]]:
        for row in cms_rows(cms_source, retrieved_at):
            raw_counts["CMS Provider Information"] += 1
            yield row
        if nevada_license_source:
            for row in nevada_license_rows(nevada_license_source, retrieved_at):
                raw_counts["Nevada HCQC Health Facility Licensing"] += 1
                yield row
        if nppes_source:
            for row in nppes_rows(nppes_source, retrieved_at, taxonomy_lookup):
                raw_counts["NPPES NPI Registry"] += 1
                yield row

    records, resolution = merge_sources(all_rows())
    errors = validate_records(records)
    type_counts = Counter(record["facility_type"] for record in records)
    missing = Counter()
    for record in records:
        for field in ("facility_name", "address", "city", "zip", "phone", "nevada_license_id", "cms_certification_number", "npi"):
            if not record.get(field):
                missing[field] += 1
    cms_update_dates = {
        str(evidence.get("source_update_date") or "")
        for record in records
        for evidence in record.get("source_evidence", {}).values()
        if evidence.get("source_name") == "CMS Provider Information" and evidence.get("source_update_date")
    }
    nppes_update_dates = {
        str(evidence.get("source_update_date") or "")
        for record in records
        for evidence in record.get("source_evidence", {}).values()
        if evidence.get("source_name") == "NPPES NPI Registry" and evidence.get("source_update_date")
    }
    source_datasets = [{
        "source_name": "CMS Provider Information",
        "source_url": CMS_DATASET_URL,
        "dataset_identifier": CMS_DATASET_ID,
        "source_authority": "Federal government",
        "retrieval_date": retrieved_at,
        "source_update_date": max(cms_update_dates, default="") or None,
        "applicable_facility_types": ["Skilled Nursing Facility", "Nursing Facility"],
        "used": True,
    }, {
        "source_name": "Nevada HCQC Health Facility Licensing",
        "source_url": NEVADA_HCQC_URL,
        "dataset_identifier": nevada_license_source.name if nevada_license_source else None,
        "source_authority": "Nevada state licensing authority",
        "retrieval_date": retrieved_at if nevada_license_source else None,
        "source_update_date": None,
        "applicable_facility_types": ["Assisted Living", "Residential Facility for Groups", "Skilled Nursing Facility", "Nursing Facility", "Continuing Care / Life Plan"],
        "used": bool(nevada_license_source),
        "limitation": None if nevada_license_source else "No machine-readable Nevada HCQC export was available locally. The official licensing vendor endpoint was reachable but redirected in a loop and exposed no verified public export during this run.",
    }, {
        "source_name": "NPPES NPI Registry",
        "source_url": NPPES_URL,
        "dataset_identifier": nppes_source.name if nppes_source else "NPPES monthly dissemination",
        "source_authority": "Federal government",
        "retrieval_date": retrieved_at if nppes_source else None,
        "source_update_date": max(nppes_update_dates, default="") or None,
        "applicable_facility_types": ["Facility-specific organizational providers", "Assisted Living", "Memory Care", "Skilled Nursing Facility", "Nursing Facility", "Continuing Care / Life Plan"],
        "used": bool(nppes_source),
        "limitation": None if nppes_source else "No Nevada-filtered NPPES source extract was available locally; the existing repository extract is Florida-only and was not reused.",
    }]
    report = {
        "generated_at_utc": retrieved_at,
        "canonical_schema_version": SCHEMA_VERSION,
        "source_datasets_used": [source for source in source_datasets if source["used"]],
        "source_datasets_reviewed": source_datasets,
        "source_retrieval_dates": {source["source_name"]: source["retrieval_date"] for source in source_datasets if source["used"]},
        "raw_records_by_source": dict(raw_counts),
        "canonical_nevada_records": len(records),
        "las_vegas_valley_records": sum(bool(record["is_las_vegas_valley"]) for record in records),
        "complete_authoritative_identities": sum(complete_identity(record) for record in records),
        "complete_las_vegas_valley_identities": sum(record["is_las_vegas_valley"] and complete_identity(record) for record in records),
        "records_with_phone": sum(bool(record.get("phone")) for record in records),
        "records_with_full_address": sum(bool(record.get("address") and record.get("city") and record.get("state") and record.get("zip")) for record in records),
        "records_with_nevada_license_id": sum(bool(record.get("nevada_license_id")) for record in records),
        "records_with_cms_ccn": sum(bool(record.get("cms_certification_number")) for record in records),
        "records_with_npi": sum(bool(record.get("npi")) for record in records),
        "records_by_facility_type": dict(sorted(type_counts.items())),
        "active_facilities": sum(str(record.get("license_status")) == "ACTIVE" for record in records),
        "inactive_closed_facilities": sum(str(record.get("license_status")) in {"INACTIVE", "CLOSED"} for record in records),
        "duplicates_merged": resolution["duplicates_merged"],
        "unresolved_duplicate_candidates": sum(bool(record.get("duplicate_candidate")) for record in records),
        "field_conflicts": resolution["conflicts"],
        "field_conflict_count": len(resolution["conflicts"]),
        "records_missing_critical_identity_fields": sum(not complete_identity(record) for record in records),
        "missing_field_distribution": dict(missing),
        "schema_validation_errors": errors,
        "invalid_zip_codes": sum(bool(record.get("zip")) and not re.fullmatch(r"\d{5}", str(record["zip"])) for record in records),
        "invalid_or_malformed_phone_numbers": sum(bool(record.get("phone")) and not re.fullmatch(r"\d{10}", str(record["phone"])) for record in records),
        "media_pilot_gate": {
            "required_complete_las_vegas_valley_identities": 100,
            "actual_complete_las_vegas_valley_identities": sum(record["is_las_vegas_valley"] and complete_identity(record) for record in records),
            "status": "PASS" if sum(record["is_las_vegas_valley"] and complete_identity(record) for record in records) >= 100 else "FAIL",
        },
    }
    payload = {"generated_at_utc": retrieved_at, "record_count": len(records), "canonical_schema_version": SCHEMA_VERSION, "records": records}
    return payload, report


def render_report(report: dict[str, Any]) -> str:
    processing_time_seconds = report.get("processing_time_seconds")
    peak_memory_mib = report.get("peak_memory_mib")
    lines = [
        "# Nevada Canonical Facility Universe Report",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        "",
        "## Sources",
        "",
        "| Source | Authority | Dataset | Retrieval | Used |",
        "| --- | --- | --- | --- | --- |",
    ]
    for source in report["source_datasets_reviewed"]:
        lines.append(f"| {source['source_name']} | {source['source_authority']} | {source['dataset_identifier'] or 'Unavailable'} | {source['retrieval_date'] or 'Unavailable'} | {'Yes' if source['used'] else 'No'} |")
    lines.extend([
        "",
        "## Results",
        "",
        f"- Raw records by source: `{json.dumps(report['raw_records_by_source'], sort_keys=True)}`",
        f"- Canonical Nevada records: **{report['canonical_nevada_records']}**",
        f"- Las Vegas Valley records: **{report['las_vegas_valley_records']}**",
        f"- Complete authoritative identities: **{report['complete_authoritative_identities']}**",
        f"- Complete Las Vegas Valley identities: **{report['complete_las_vegas_valley_identities']}**",
        f"- Records with phone: **{report['records_with_phone']}**",
        f"- Records with full address: **{report['records_with_full_address']}**",
        f"- Records with Nevada license ID: **{report['records_with_nevada_license_id']}**",
        f"- Records with CMS/CCN: **{report['records_with_cms_ccn']}**",
        f"- Records with NPI: **{report['records_with_npi']}**",
        f"- Active facilities: **{report['active_facilities']}**",
        f"- Inactive/closed facilities: **{report['inactive_closed_facilities']}**",
        f"- Duplicates merged: **{report['duplicates_merged']}**",
        f"- Unresolved duplicate candidates: **{report['unresolved_duplicate_candidates']}**",
        f"- Field conflicts: **{report['field_conflict_count']}**",
        f"- Records missing critical identity fields: **{report['records_missing_critical_identity_fields']}**",
        f"- Schema-validation errors: **{len(report['schema_validation_errors'])}**",
        f"- Invalid ZIP codes: **{report['invalid_zip_codes']}**",
        f"- Invalid or malformed phones: **{report['invalid_or_malformed_phone_numbers']}**",
        f"- Processing time: **{processing_time_seconds if processing_time_seconds is not None else 'Unavailable'}{' seconds' if processing_time_seconds is not None else ''}**",
        f"- Peak memory: **{peak_memory_mib if peak_memory_mib is not None else 'Unavailable'}{' MiB' if peak_memory_mib is not None else ''}**",
        "",
        "## Facility Types",
        "",
    ])
    lines.extend(f"- {name}: **{count}**" for name, count in report["records_by_facility_type"].items())
    lines.extend([
        "",
        "## Missing Fields",
        "",
    ])
    lines.extend(f"- {name}: **{count}**" for name, count in sorted(report["missing_field_distribution"].items()))
    lines.extend([
        "",
        "## Media Pilot Gate",
        "",
        f"**{report['media_pilot_gate']['status']}**: {report['media_pilot_gate']['actual_complete_las_vegas_valley_identities']} complete Las Vegas Valley identities; 100 required.",
        "",
        "No media pilot was run.",
    ])
    unavailable = [source for source in report["source_datasets_reviewed"] if not source["used"]]
    if unavailable:
        lines.extend(["", "## Source Limitations", ""])
        lines.extend(f"- {source['source_name']}: {source['limitation']}" for source in unavailable)
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the governed Nevada canonical facility universe.")
    parser.add_argument("--cms-source", type=Path, default=DEFAULT_CMS_SOURCE)
    parser.add_argument("--nevada-license-source", type=Path)
    parser.add_argument("--nppes-source", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--retrieved-at", default=utc_now())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.cms_source.is_file():
        raise SystemExit(f"Missing CMS source: {args.cms_source}")
    if args.nevada_license_source and not args.nevada_license_source.is_file():
        raise SystemExit(f"Missing Nevada licensing source: {args.nevada_license_source}")
    if args.nppes_source and not args.nppes_source.is_file():
        raise SystemExit(f"Missing NPPES source: {args.nppes_source}")
    started = time.perf_counter()
    tracemalloc.start()
    payload, report = build_universe(args.cms_source, args.nevada_license_source, args.nppes_source, args.retrieved_at)
    report["processing_time_seconds"] = round(time.perf_counter() - started, 3)
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    try:
        import psutil

        peak_memory_mib = psutil.Process().memory_info().peak_wset / (1024 * 1024) if sys.platform == "win32" else psutil.Process().memory_info().rss / (1024 * 1024)
        memory_measurement = "process_peak_working_set" if sys.platform == "win32" else "process_rss_at_completion"
    except (ImportError, AttributeError):
        peak_memory_mib = traced_peak / (1024 * 1024)
        memory_measurement = "python_tracemalloc_peak"
    report["peak_memory_mib"] = round(peak_memory_mib, 2)
    report["peak_memory_measurement"] = memory_measurement
    for path in (args.output, args.report_json, args.report_md):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report_md.write_text(render_report(report), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "record_count": payload["record_count"], "gate": report["media_pilot_gate"], "peak_memory_mib": report["peak_memory_mib"]}, indent=2))
    return 0 if not report["schema_validation_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())