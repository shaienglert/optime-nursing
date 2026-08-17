from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIS_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
CMS_URL = "https://data.cms.gov/provider-data/dataset/4pq5-n9py"
LV_BUSINESS_URL = "https://mapdata.lasvegasnevada.gov/clvgis/rest/services/DevelopmentServices/Business_Licenses/MapServer/0"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(v: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(v or "").lower().replace("&", " and ")).strip()


def norm_addr(v: Any) -> str:
    text = f" {norm(v)} "
    replacements = {
        " st ": " street ", " rd ": " road ", " ave ": " avenue ", " blvd ": " boulevard ",
        " dr ": " drive ", " ln ": " lane ", " hwy ": " highway ", " pkwy ": " parkway ",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def zip5(v: Any) -> str:
    m = re.search(r"\b(\d{5})", str(v or ""))
    return m.group(1) if m else "UNKNOWN"


def present(v: Any) -> bool:
    return v not in (None, "", "UNKNOWN", "unknown", [], {})


def safe_json(v: Any, fallback: Any) -> Any:
    if not present(v):
        return fallback
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(str(v))
    except Exception:
        return fallback


def source_evidence(source: str, source_url: str, record_id: str, role: str, retrieved_at: str) -> dict[str, Any]:
    return {
        "source": source,
        "source_url": source_url,
        "source_record_id": record_id or "UNKNOWN",
        "source_role": role,
        "retrieved_at": retrieved_at,
    }


def set_field(record: dict[str, Any], field: str, value: Any, evidence: dict[str, Any], *, overwrite: bool = False) -> None:
    if not present(value):
        if field not in record:
            record[field] = "UNKNOWN"
        return
    if overwrite or not present(record.get(field)):
        record[field] = value
        record.setdefault("field_provenance", {})[field] = evidence


def canonical_type(license_type: str) -> str:
    if license_type == "AGC":
        return "ASSISTED_LIVING_RFG"
    if license_type in {"SNF", "SFD"}:
        return "SKILLED_NURSING"
    return "UNKNOWN"


def canonical_id_for_license(license_number: str) -> str:
    return "NV-LIC-" + re.sub(r"[^A-Za-z0-9]+", "-", license_number).strip("-").upper()


def canonical_id_for_cms(ccn: str) -> str:
    return f"CMS-{ccn}"


def campus_id(address: str, city: str, zipcode: str) -> str:
    material = "|".join((norm_addr(address), norm(city), zip5(zipcode)))
    digest = hashlib.sha256(material.encode()).hexdigest()[:16].upper()
    return f"NV-CAMPUS-{digest}"


def alis_record(row: dict[str, str], retrieved_at: str) -> dict[str, Any]:
    license_number = row.get("license_number") or "UNKNOWN"
    lic_type = row.get("license_type") or "UNKNOWN"
    evidence = source_evidence("Nevada HCQC / ALiS", ALIS_URL, license_number, "LICENSING_SOURCE_OF_TRUTH", retrieved_at)
    detail = safe_json(row.get("official_detail"), {})
    memory_evidence = safe_json(row.get("memory_care_evidence"), [])
    memory_class = row.get("memory_care_classification") or "UNKNOWN"
    memory_confirmed = memory_class == "CONFIRMED_OFFICIAL_DETAIL"
    status = row.get("status") or "UNKNOWN"
    address = row.get("address") or "UNKNOWN"
    city = row.get("city") or "UNKNOWN"
    zipcode = zip5(row.get("zip"))
    record = {
        "canonical_id": canonical_id_for_license(license_number),
        "facility_name": row.get("facility_name") or "UNKNOWN",
        "canonical_type": canonical_type(lic_type),
        "license_type": lic_type,
        "nevada_license_id": license_number,
        "license_status": status,
        "address": address,
        "city": city,
        "state": "NV",
        "zip": zipcode,
        "county": row.get("county") or "UNKNOWN",
        "phone": row.get("phone") or "UNKNOWN",
        "licensed_capacity": row.get("bed_count") or "UNKNOWN",
        "administrator": row.get("primary_contact_name") or "UNKNOWN",
        "administrator_role": row.get("primary_contact_role") or "UNKNOWN",
        "first_issue_date": row.get("first_issue_date") or "UNKNOWN",
        "expiration_date": row.get("expiration_date") or "UNKNOWN",
        "disciplinary_action": row.get("disciplinary_action") or "UNKNOWN",
        "cms_ccn": row.get("federal_provider_number") or "UNKNOWN",
        "memory_care_classification": "CONFIRMED" if memory_confirmed else "UNKNOWN",
        "memory_care_evidence": memory_evidence if memory_evidence else "UNKNOWN",
        "official_detail": detail if detail else "UNKNOWN",
        "detail_url": row.get("detail_url") or "UNKNOWN",
        "is_clark_county": str(row.get("is_clark_county") or "").lower() == "true",
        "is_las_vegas_valley": str(row.get("is_las_vegas_valley") or "").lower() == "true",
        "campus_group_id": campus_id(address, city, zipcode),
        "source_records": [evidence],
        "field_provenance": {},
        "identity_merge_evidence": [],
        "review_flags": [],
    }
    for f in (
        "facility_name", "canonical_type", "license_type", "nevada_license_id", "license_status", "address", "city",
        "state", "zip", "county", "phone", "licensed_capacity", "administrator", "administrator_role",
        "first_issue_date", "expiration_date", "disciplinary_action", "cms_ccn", "memory_care_classification",
        "memory_care_evidence", "official_detail", "detail_url", "is_clark_county", "is_las_vegas_valley",
    ):
        record["field_provenance"][f] = evidence
    if not memory_confirmed:
        record["review_flags"].append("MEMORY_CARE_UNKNOWN")
    return record


def cms_name(row: dict[str, str]) -> str:
    return row.get("Provider Name") or "UNKNOWN"


def cms_address(row: dict[str, str]) -> str:
    return row.get("Provider Address") or "UNKNOWN"


def merge_cms(record: dict[str, Any], row: dict[str, str], retrieved_at: str, method: str) -> None:
    ccn = row.get("Federal Provider Number") or "UNKNOWN"
    ev = source_evidence("CMS Care Compare Provider Information", CMS_URL, ccn, "FEDERAL_NURSING_SOURCE_OF_TRUTH", retrieved_at)
    record["source_records"].append(ev)
    record["identity_merge_evidence"].append({"method": method, "cms_ccn": ccn, "source": "CMS Care Compare"})
    set_field(record, "cms_ccn", ccn, ev, overwrite=not present(record.get("cms_ccn")))
    set_field(record, "cms_provider_name", cms_name(row), ev)
    set_field(record, "certified_beds", row.get("Number of Certified Beds"), ev)
    set_field(record, "cms_ownership_type", row.get("Ownership Type"), ev)
    set_field(record, "cms_overall_rating", row.get("Overall Rating"), ev)
    set_field(record, "cms_health_inspection_rating", row.get("Health Inspection Rating"), ev)
    set_field(record, "cms_staffing_rating", row.get("Staffing Rating"), ev)
    set_field(record, "cms_quality_measure_rating", row.get("QM Rating"), ev)
    set_field(record, "cms_processing_date", row.get("Processing Date"), ev)
    if record.get("canonical_type") == "UNKNOWN":
        set_field(record, "canonical_type", "SKILLED_NURSING", ev, overwrite=True)


def cms_only_record(row: dict[str, str], retrieved_at: str) -> dict[str, Any]:
    ccn = row.get("Federal Provider Number") or "UNKNOWN"
    ev = source_evidence("CMS Care Compare Provider Information", CMS_URL, ccn, "FEDERAL_NURSING_SOURCE_OF_TRUTH", retrieved_at)
    address = cms_address(row)
    city = row.get("City/Town") or "UNKNOWN"
    zipcode = zip5(row.get("ZIP Code"))
    county = row.get("County/Parish") or "UNKNOWN"
    record = {
        "canonical_id": canonical_id_for_cms(ccn),
        "facility_name": cms_name(row),
        "canonical_type": "SKILLED_NURSING",
        "license_type": "UNKNOWN",
        "nevada_license_id": "UNKNOWN",
        "license_status": "UNKNOWN",
        "address": address,
        "city": city,
        "state": "NV",
        "zip": zipcode,
        "county": county,
        "phone": row.get("Telephone Number") or "UNKNOWN",
        "licensed_capacity": "UNKNOWN",
        "administrator": "UNKNOWN",
        "administrator_role": "UNKNOWN",
        "first_issue_date": "UNKNOWN",
        "expiration_date": "UNKNOWN",
        "disciplinary_action": "UNKNOWN",
        "cms_ccn": ccn,
        "memory_care_classification": "UNKNOWN",
        "memory_care_evidence": "UNKNOWN",
        "official_detail": "UNKNOWN",
        "detail_url": "UNKNOWN",
        "is_clark_county": norm(county) == "clark",
        "is_las_vegas_valley": norm(county) == "clark" and norm(city) in {"las vegas", "north las vegas", "henderson"},
        "campus_group_id": campus_id(address, city, zipcode),
        "source_records": [ev],
        "field_provenance": {},
        "identity_merge_evidence": [],
        "review_flags": ["NEVADA_LICENSE_ID_UNKNOWN", "MEMORY_CARE_UNKNOWN"],
    }
    for f in ("facility_name", "canonical_type", "address", "city", "state", "zip", "county", "phone", "cms_ccn"):
        record["field_provenance"][f] = ev
    merge_cms(record, row, retrieved_at, "CMS_ONLY")
    return record


def strong_name_address_key(name: Any, address: Any, city: Any, zipcode: Any) -> tuple[str, str, str, str]:
    return norm(name), norm_addr(address), norm(city), zip5(zipcode)


def build(alis_rows: list[dict[str, str]], cms_rows: list[dict[str, str]], business_rows: list[dict[str, Any]]) -> dict[str, Any]:
    retrieved_at = now()
    records = [alis_record(row, retrieved_at) for row in alis_rows]
    by_ccn: dict[str, list[int]] = defaultdict(list)
    by_name_address: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    for i, record in enumerate(records):
        if present(record.get("cms_ccn")):
            by_ccn[str(record["cms_ccn"])].append(i)
        key = strong_name_address_key(record.get("facility_name"), record.get("address"), record.get("city"), record.get("zip"))
        if all(present(x) for x in key):
            by_name_address[key].append(i)

    matched_cms: set[int] = set()
    merge_methods: Counter[str] = Counter()
    unresolved_cms: list[dict[str, Any]] = []
    for cms_index, row in enumerate(cms_rows):
        ccn = row.get("Federal Provider Number") or ""
        match_index: int | None = None
        method = ""
        exact = by_ccn.get(ccn, []) if ccn else []
        if len(exact) == 1:
            match_index = exact[0]
            method = "EXACT_CCN"
        elif len(exact) > 1:
            unresolved_cms.append({"ccn": ccn, "reason": "AMBIGUOUS_CCN", "candidate_count": len(exact)})
            continue
        else:
            key = strong_name_address_key(cms_name(row), cms_address(row), row.get("City/Town"), row.get("ZIP Code"))
            candidates = by_name_address.get(key, [])
            if len(candidates) == 1:
                match_index = candidates[0]
                method = "EXACT_NORMALIZED_NAME_ADDRESS_CITY_ZIP"
            elif len(candidates) > 1:
                unresolved_cms.append({"ccn": ccn, "reason": "AMBIGUOUS_NAME_ADDRESS", "candidate_count": len(candidates)})
                continue
        if match_index is not None:
            merge_cms(records[match_index], row, retrieved_at, method)
            matched_cms.add(cms_index)
            merge_methods[method] += 1
        else:
            records.append(cms_only_record(row, retrieved_at))
            merge_methods["CMS_ONLY"] += 1

    # Campus grouping does not merge distinct Nevada licenses. It only exposes
    # physically co-located entities so mixed campuses are counted honestly.
    campus_members: dict[str, list[int]] = defaultdict(list)
    for i, record in enumerate(records):
        campus_members[record["campus_group_id"]].append(i)
    mixed_campuses = 0
    multi_entity_campuses = 0
    for cid, members in campus_members.items():
        if len(members) < 2:
            continue
        multi_entity_campuses += 1
        types = {records[i]["canonical_type"] for i in members}
        if len(types) > 1:
            mixed_campuses += 1
            for i in members:
                records[i]["campus_classification"] = "MIXED_CAMPUS"
        else:
            for i in members:
                records[i]["campus_classification"] = "MULTI_ENTITY_SAME_TYPE_CAMPUS"

    # Independent Living is not state-licensed as such. Business-license rows
    # are retained as discovery evidence and review candidates, never promoted
    # to confirmed Independent Living merely because the name contains senior.
    il_candidates = []
    for row in business_rows:
        if row.get("license_category") != "Apartment House":
            continue
        if row.get("independent_living_classification") == "CANDIDATE_NAME_SIGNAL":
            il_candidates.append({
                "business_license_number": row.get("license_number") or "UNKNOWN",
                "business_name": row.get("business_name") or "UNKNOWN",
                "address": row.get("address") or "UNKNOWN",
                "city": row.get("city") or "UNKNOWN",
                "state": row.get("state") or "NV",
                "zip": row.get("zip") or "UNKNOWN",
                "classification": "INDEPENDENT_LIVING_CANDIDATE_UNKNOWN",
                "evidence": "Name signal only; not proof of Independent Living.",
                "source": source_evidence("City of Las Vegas Business Licenses", LV_BUSINESS_URL, row.get("license_number") or "UNKNOWN", "DISCOVERY_ENRICHMENT_ONLY", retrieved_at),
            })

    type_counts = Counter(r["canonical_type"] for r in records)
    memory_confirmed = sum(r.get("memory_care_classification") == "CONFIRMED" for r in records)
    memory_unknown = sum(r.get("canonical_type") == "ASSISTED_LIVING_RFG" and r.get("memory_care_classification") != "CONFIRMED" for r in records)
    clark = [r for r in records if r.get("is_clark_county") is True]
    valley = [r for r in records if r.get("is_las_vegas_valley") is True]
    subsets = {
        "nevada_statewide": records,
        "clark_county": clark,
        "las_vegas": [r for r in records if norm(r.get("city")) == "las vegas"],
        "north_las_vegas": [r for r in records if norm(r.get("city")) == "north las vegas"],
        "henderson": [r for r in records if norm(r.get("city")) == "henderson"],
        "las_vegas_valley": valley,
    }

    review_flags = Counter(flag for r in records for flag in r.get("review_flags", []))
    report = {
        "generated_at": retrieved_at,
        "canonical_facilities_unique": len(records),
        "nevada_official_license_records": len(alis_rows),
        "cms_source_records": len(cms_rows),
        "business_license_discovery_records": len(business_rows),
        "source_identity_merges": sum(v for k, v in merge_methods.items() if k != "CMS_ONLY"),
        "merge_methods": dict(merge_methods),
        "unresolved_cms_identity_conflicts": unresolved_cms,
        "counts_by_type": dict(type_counts),
        "memory_care_confirmed": memory_confirmed,
        "memory_care_candidate_unknown": memory_unknown,
        "independent_living_confirmed": 0,
        "independent_living_candidates_unknown": len(il_candidates),
        "multi_entity_campuses": multi_entity_campuses,
        "mixed_campuses": mixed_campuses,
        "review_flags": dict(review_flags),
        "subsets": {key: len(value) for key, value in subsets.items()},
        "semantic_guardrails": [
            "Nevada HCQC/ALiS is licensing source of truth.",
            "CMS is federal nursing-facility evidence and is never used as Nevada assisted-living licensing truth.",
            "CMS merges require exact CCN or exact normalized name+address+city+ZIP.",
            "Distinct Nevada licenses are never collapsed merely because they share a campus.",
            "Memory Care requires explicit official ALiS detail evidence.",
            "Independent Living name signals remain candidates/UNKNOWN.",
            "Commercial directories are not sources of licensing truth.",
        ],
    }
    return {
        "schema_version": "nevada-canonical-facility-v2.0.0",
        "generated_at": retrieved_at,
        "record_count": len(records),
        "records": records,
        "independent_living_discovery_candidates": il_candidates,
        "report": report,
        "subsets": subsets,
    }


def write_outputs(payload: dict[str, Any], output: Path, report_json: Path, report_md: Path, subset_dir: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({k: v for k, v in payload.items() if k != "subsets"}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = payload["report"]
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subset_dir.mkdir(parents=True, exist_ok=True)
    for name, records in payload["subsets"].items():
        (subset_dir / f"{name}.json").write_text(json.dumps({"record_count": len(records), "records": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Nevada Canonical Facility Universe", "",
        f"Generated: `{report['generated_at']}`", "",
        f"- Unique canonical facilities: **{report['canonical_facilities_unique']}**",
        f"- Nevada ALiS license records: **{report['nevada_official_license_records']}**",
        f"- CMS Nevada records: **{report['cms_source_records']}**",
        f"- Cross-source identity merges: **{report['source_identity_merges']}**",
        f"- Memory Care confirmed from official ALiS detail: **{report['memory_care_confirmed']}**",
        f"- Independent Living confirmed: **{report['independent_living_confirmed']}**",
        f"- Independent Living discovery candidates / UNKNOWN: **{report['independent_living_candidates_unknown']}**", "",
        "## Geographic subsets", "",
    ]
    for key, value in report["subsets"].items():
        lines.append(f"- {key}: **{value}**")
    lines += ["", "## Merge methods", ""]
    for key, value in report["merge_methods"].items():
        lines.append(f"- {key}: **{value}**")
    lines += ["", "## Guardrails", ""] + [f"- {x}" for x in report["semantic_guardrails"]]
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alis", type=Path, default=ROOT / "data/nevada/clean/hcqc_alis_facilities.csv")
    ap.add_argument("--cms", type=Path, default=ROOT / "data/nevada/raw/cms_provider_information_nv.csv")
    ap.add_argument("--business", type=Path, default=ROOT / "data/nevada/raw/las_vegas_business_license_senior_candidates.json")
    ap.add_argument("--output", type=Path, default=ROOT / "database/nevada_facility_universe_canonical.json")
    ap.add_argument("--report-json", type=Path, default=ROOT / "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.json")
    ap.add_argument("--report-md", type=Path, default=ROOT / "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md")
    ap.add_argument("--subset-dir", type=Path, default=ROOT / "data/nevada/canonical")
    args = ap.parse_args()
    with args.alis.open(encoding="utf-8-sig", newline="") as h:
        alis_rows = list(csv.DictReader(h))
    with args.cms.open(encoding="utf-8-sig", newline="") as h:
        cms_rows = list(csv.DictReader(h))
    business_rows = json.loads(args.business.read_text(encoding="utf-8"))
    payload = build(alis_rows, cms_rows, business_rows)
    write_outputs(payload, args.output, args.report_json, args.report_md, args.subset_dir)
    print(json.dumps(payload["report"], indent=2, ensure_ascii=False))
    if not payload["records"]:
        raise SystemExit("Canonical Nevada universe is empty")
    if payload["report"]["nevada_official_license_records"] == 0:
        raise SystemExit("No Nevada official licensing records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
