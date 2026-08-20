from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


RESEARCH_FIELDS = [
    "primary_source_url",
    "serves_las_vegas_valley",
    "bathing_assistance",
    "dressing_assistance",
    "transfer_assistance",
    "minimum_visit_minutes",
    "minimum_billable_hours",
    "hourly_rate_for_requested_schedule",
    "employment_model",
    "liability_insurance_verified",
    "workers_comp_verified",
    "background_check_verified",
    "fixed_caregiver_possible",
    "supervision_frequency",
    "languages",
    "availability_status",
]

RELATIONSHIP_FIELDS = [
    "on_site_il_relationships",
    "preferred_il_relationships",
    "required_il_relationships",
    "outside_agency_accepted_by_il",
]


def _load_verified(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(row.get("license_number") or "").strip()
        for row in payload.get("records") or []
        if row.get("identity_verified") is True
    }


def _live_valley_license_set(rows: list[dict[str, str]]) -> set[str]:
    return {
        str(row.get("license_number") or "").strip()
        for row in rows
        if str(row.get("license_status") or "").upper() == "ACTIVE"
        and str(row.get("is_las_vegas_valley") or "").lower() == "true"
        and str(row.get("license_number") or "").strip()
    }


def build(rows: list[dict[str, str]], verified_licenses: set[str]) -> dict:
    live_valley_licenses = _live_valley_license_set(rows)
    governed_verified_licenses = verified_licenses & live_valley_licenses
    stale_or_out_of_scope_verified = sorted(verified_licenses - live_valley_licenses)

    tasks = []
    for row in rows:
        if str(row.get("license_status") or "").upper() != "ACTIVE":
            continue
        if str(row.get("is_las_vegas_valley") or "").lower() != "true":
            continue
        license_number = str(row.get("license_number") or "").strip()
        if not license_number or license_number in governed_verified_licenses:
            continue
        agency_name = str(row.get("agency_name") or "UNKNOWN").strip()
        city = str(row.get("city") or "UNKNOWN").strip()
        tasks.append({
            "queue_type": "PCA_OPERATIONAL_RESEARCH",
            "priority": "P0_UNVERIFIED_OPERATIONAL_FIT",
            "agency_id": row.get("agency_id") or f"NV-PCA-{license_number}",
            "agency_name": agency_name,
            "license_number": license_number,
            "license_status": "ACTIVE",
            "address": row.get("address") or "UNKNOWN",
            "city": city,
            "state": "NV",
            "zip": row.get("zip") or "UNKNOWN",
            "phone": row.get("phone") or "UNKNOWN",
            "hcqc_detail_url": row.get("detail_url") or "UNKNOWN",
            "official_source_discovery_query": f'"{agency_name}" {city} NV official personal care home care',
            "required_operational_fields": RESEARCH_FIELDS,
            "facility_relationship_fields": RELATIONSHIP_FIELDS,
            "identity_rule": "Primary/operator evidence must match the HCQC agency by strong identity such as exact license root, exact address, exact phone, or exact agency identity plus city. Directory-only identity is insufficient.",
            "unknown_rule": "If a field is not directly evidenced by HCQC or the agency/provider primary source, keep UNKNOWN. Do not infer insurance, background checks, employment model, minimum hours, short-visit pricing, caregiver continuity, languages, availability, or facility relationships from licensure alone.",
            "pricing_rule": "Published example rates for other schedules do not establish the rate for a one-hour daily visit. Store the schedule context with every price claim.",
        })
    tasks.sort(key=lambda row: (row["city"], row["agency_name"], row["license_number"]))
    return {
        "schema_version": "nevada-pca-operational-research-queue-v1.1.0",
        "queue_type": "PCA_OPERATIONAL_RESEARCH",
        "licensed_valley_input_count": len(live_valley_licenses),
        "already_operationally_verified_count": len(governed_verified_licenses),
        "stale_or_out_of_scope_verified_count": len(stale_or_out_of_scope_verified),
        "stale_or_out_of_scope_verified_licenses": stale_or_out_of_scope_verified,
        "research_task_count": len(tasks),
        "tasks": tasks,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/nevada/raw/hcqc_personal_care_agencies.csv")
    ap.add_argument("--verified", default="data/nevada/verified/personal_care_agency_operational_evidence.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_OPERATIONAL_RESEARCH_QUEUE.json")
    args = ap.parse_args()

    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    verified = _load_verified(Path(args.verified))
    payload = build(rows, verified)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in (
        "licensed_valley_input_count",
        "already_operationally_verified_count",
        "stale_or_out_of_scope_verified_count",
        "research_task_count",
    )}, indent=2))
    if payload["licensed_valley_input_count"] <= 0:
        raise SystemExit("No live Las Vegas Valley PCA input records")
    if payload["research_task_count"] + payload["already_operationally_verified_count"] != payload["licensed_valley_input_count"]:
        raise SystemExit("PCA research queue accounting mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
