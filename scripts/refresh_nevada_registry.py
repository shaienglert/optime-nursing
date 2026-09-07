#!/usr/bin/env python3
"""Refresh the Nevada licence registry from ALiS, and apply it.

Why this exists rather than a periodic manual export: a registry that is only refreshed by
hand decays silently, and the failure is invisible until someone looks. The sibling product
learned that expensively -- a pool of 3,923 postings fell to 389 because rows aged out of a
freshness window and nothing was re-collecting them. Licence data moves far more slowly than
job postings, but it moves: communities open, close, change hands and lose endorsements.

Two properties matter more than freshness itself.

**It fails loudly, not quietly.** The characteristic scraper failure is not an exception, it
is a 200 response containing a login page, which parses cleanly into zero rows and then
overwrites a good registry with nothing. Every write here is gated on the new pull being
credible against what is already on disk, and the job exits non-zero rather than writing a
collapse.

**The database does not wait for a pull request.** The repo copy of the registry is data
under review, and proposing it as a PR is right. But if the database could only be updated
by merging that PR, an unmerged PR would stall the data -- which is exactly how the sibling
product's discovery pipeline stranded four consecutive runs. So --apply writes to the
database from the live pull directly, and the PR that follows is bookkeeping.

Coverage note: ALiS is queried for the licence types that carry senior housing -- AGC
(residential facilities for groups, which is where assisted living and memory care live) and
SNF/SFD (skilled nursing). Nevada also licenses community-based living, individual
residential care and adult day under separate types that this search does not return; those
rows survive from the previous registry rather than being dropped, because absence from a
narrower query is not evidence a licence ended.

    python scripts/refresh_nevada_registry.py --dry-run
    python scripts/refresh_nevada_registry.py                 # rewrite the registry file
    python scripts/refresh_nevada_registry.py --apply         # ... and load it into the database
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "data" / "nevada" / "verified" / "nv_hcqc_clark_registry.json"
REPORT_PATH = REPO_ROOT / "reports" / "NEVADA_REGISTRY_REFRESH.json"
SCHEMA_VERSION = "nevada-hcqc-clark-registry-v1.0.0"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# A pull that loses more than this share of the known records is treated as a broken
# session rather than a real contraction. Licences do lapse, but not a fifth of a county's
# in one week, and the cost of pausing on a true contraction is one manual look.
MIN_RETAINED_SHARE = 0.80

LICENSE_TYPES = ("AGC", "SNF", "SFD")

# ALiS answers statewide. The registry declares Clark County, and a refresh that quietly
# returned Reno and Carson City would be a scope change wearing a refresh's clothes -- the
# record count would rise, look healthy, and mean something different from what the file
# says it means. Scope stays where it was declared unless --statewide says otherwise.
#
# Both bounds are read off the 611 rows already known to be Clark: every one of them falls
# in ZIP 890xx or 891xx, across five incorporated places.
CLARK_ZIP_PREFIXES = ("890", "891")
CLARK_CITIES = {
    "LAS VEGAS", "NORTH LAS VEGAS", "HENDERSON", "BOULDER CITY", "MESQUITE",
    # Unincorporated Clark communities that can appear on a licence address.
    "LAUGHLIN", "OVERTON", "LOGANDALE", "MOAPA", "SEARCHLIGHT", "INDIAN SPRINGS",
    "BLUE DIAMOND", "BUNKERVILLE", "SANDY VALLEY", "GOODSPRINGS", "JEAN", "PRIMM",
    "CAL NEV ARI", "CAL-NEV-ARI", "NELLIS AFB",
}


def in_clark_county(row: Dict[str, Any]) -> bool:
    """ZIP decides; the city name is the fallback when a ZIP is missing or malformed."""
    zip_code = str(row.get("zip") or "").strip()
    if zip_code[:3] in CLARK_ZIP_PREFIXES:
        return True
    if zip_code[:3].isdigit():
        return False
    return str(row.get("city") or "").strip().upper() in CLARK_CITIES

# ALiS field names -> the registry's. The registry is the contract the importer reads, so
# the mapping lives here and the importer never learns about the scraper's shape.
FIELD_MAP = {
    "credential_type_code": "license_type",
    "name": "facility_name",
    "credential_number": "license_number",
    "status": "status",
    "expiration_date": "expiration_date",
    "address": "address",
    "city": "city",
    "state": "state",
    "zip": "zip",
    "phone": "phone",
    "bed_count": "capacity",
    "federal_provider_no": "federal_provider_number",
    "detail_url": "detail_url",
}

REGISTRY_FIELDS = [
    "credential_type_code", "name", "credential_number", "status", "expiration_date",
    "address", "city", "state", "zip", "phone", "bed_count", "federal_provider_no",
    "derived_care_type", "endorsement", "serves_elderly", "beds_alzheimer", "detail_url",
]


# ALiS writes "UNKNOWN" into columns it has no value for. Carried into the registry it
# stops being absence and becomes a string that downstream code can mistake for a value.
NULL_SENTINELS = {"", "UNKNOWN", "N/A", "NA", "NONE", "NULL", "-"}


def _scrub(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.upper() in NULL_SENTINELS else text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_existing() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"records": []}
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _derive_care_type(row: Dict[str, Any], previous: Dict[str, str] | None) -> str:
    """Keep the care type the registry already carries; it is richer than ALiS returns.

    The stored derived_care_type distinguishes ASSISTED_LIVING_WITH_MEMORY_CARE from
    MEMORY_CARE_DEDICATED_LARGE and so on, which the licence type alone cannot. Recomputing
    it from a coarser signal would be a downgrade dressed as a refresh, so a known row keeps
    its classification and only a genuinely new licence is classified from what we have.
    """
    if previous and previous.get("derived_care_type"):
        return previous["derived_care_type"]

    code = str(row.get("license_type") or "").upper()
    if code in {"SNF", "SFD"}:
        return "SKILLED_NURSING"

    classification = str(row.get("memory_care_classification") or "").upper()
    capacity = row.get("capacity")
    try:
        beds = int(float(str(capacity))) if str(capacity).strip() else 0
    except ValueError:
        beds = 0

    if classification.startswith("CONFIRMED"):
        return "MEMORY_CARE_DEDICATED_LARGE" if beds >= 40 else "MEMORY_CARE_DEDICATED_HOME"
    if beds >= 40:
        return "ASSISTED_LIVING_COMMUNITY"
    return "RESIDENTIAL_GROUP_HOME"


def normalize(rows: List[Dict[str, Any]], existing_records: List[Dict[str, str]]) -> List[Dict[str, str]]:
    by_credential = {str(r.get("credential_number", "")): r for r in existing_records}
    out: List[Dict[str, str]] = []
    for row in rows:
        credential = str(row.get("license_number") or "").strip()
        if not credential:
            continue
        previous = by_credential.get(credential)
        record = {key: _scrub(row.get(source)) for key, source in FIELD_MAP.items()}
        record["derived_care_type"] = _derive_care_type(row, previous)
        # Endorsements and the Alzheimer bed split are not in the ALiS results grid. They
        # are real, previously captured facts, and a refresh that blanked them would delete
        # the evidence every memory care derivation depends on.
        record["endorsement"] = (previous or {}).get("endorsement", "")
        record["serves_elderly"] = (previous or {}).get("serves_elderly", "")
        record["beds_alzheimer"] = (previous or {}).get("beds_alzheimer", "")
        out.append({field: record.get(field, "") for field in REGISTRY_FIELDS})
    return out


def merge_with_untouched(
    refreshed: List[Dict[str, str]], existing_records: List[Dict[str, str]]
) -> tuple[List[Dict[str, str]], int]:
    """Carry forward rows whose licence type this search does not cover.

    CBL, HIC, ADC and the rest are licensed under types the AGC/SNF query never returns.
    Treating their absence as closure would silently delete them.
    """
    refreshed_credentials = {r["credential_number"] for r in refreshed}
    covered_types = {"AGC", "SNF", "SFD"}
    carried = [
        record
        for record in existing_records
        if record.get("credential_number") not in refreshed_credentials
        and str(record.get("credential_type_code", "")).upper() not in covered_types
    ]
    merged = sorted(refreshed + carried, key=lambda r: (r.get("name", ""), r.get("credential_number", "")))
    return merged, len(carried)


def credibility_check(new_count: int, previous_count: int) -> tuple[bool, str]:
    if previous_count == 0:
        return True, "no previous registry to compare against"
    if new_count == 0:
        return False, "the refresh returned zero records"
    retained = new_count / previous_count
    if retained < MIN_RETAINED_SHARE:
        return False, (
            f"the refresh holds {new_count} records against {previous_count} on file "
            f"({retained:.0%}); below the {MIN_RETAINED_SHARE:.0%} floor this is treated as a "
            "broken session, not a contraction"
        )
    return True, f"{new_count} records against {previous_count} on file ({retained:.0%})"


def fetch_live(
    throttle: float, skip_details: bool, statewide: bool = False
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    from extract_nevada_hcqc_alis import collect_type  # noqa: PLC0415 -- optional at import time

    rows: List[Dict[str, Any]] = []
    reports: List[Dict[str, Any]] = []
    for code in LICENSE_TYPES:
        collected, report = collect_type(code, include_details=not skip_details, throttle=throttle)
        if statewide:
            kept = collected
        else:
            kept = [row for row in collected if in_clark_county(row)]
        report["records_statewide"] = report["records"]
        report["records"] = len(kept)
        rows.extend(kept)
        reports.append(report)
        print(f"  {code}: {len(kept)} of {report['records_statewide']} statewide", flush=True)
    return rows, reports


def apply_to_database() -> Dict[str, Any]:
    from app.database import SessionLocal, engine  # noqa: PLC0415
    from app.ingestion.nevada_hcqc import import_nevada_registry  # noqa: PLC0415
    from app.services.capability_derivation import backfill_derived_capabilities  # noqa: PLC0415
    from app.services.schema_migrations import ensure_state_license_schema  # noqa: PLC0415

    ensure_state_license_schema(engine)
    db = SessionLocal()
    try:
        ingest = import_nevada_registry(db)
        derived = backfill_derived_capabilities(db)
    finally:
        db.close()
    return {"ingest": ingest, "derivation": derived}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="fetch and report; write nothing")
    parser.add_argument("--apply", action="store_true", help="also load the registry into the database")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="skip ALiS and apply the registry already on disk")
    parser.add_argument("--skip-details", action="store_true",
                        help="skip per-licence detail pages (much faster, no memory-care evidence)")
    parser.add_argument("--throttle", type=float, default=0.05)
    parser.add_argument("--statewide", action="store_true",
                        help="keep every Nevada county, not only Clark; changes the registry's scope")
    args = parser.parse_args()

    existing = load_existing()
    existing_records: List[Dict[str, str]] = existing.get("records", [])
    summary: Dict[str, Any] = {
        "ran_at": _now(),
        "records_before": len(existing_records),
        "scope": "STATEWIDE" if args.statewide else "CLARK_COUNTY",
        "fetched": False,
        "written": False,
        "applied": False,
    }

    if not args.skip_fetch:
        print(f"Fetching Nevada ALiS ({', '.join(LICENSE_TYPES)})...", flush=True)
        try:
            live_rows, reports = fetch_live(args.throttle, args.skip_details, args.statewide)
        except Exception as error:  # noqa: BLE001 -- the reason belongs in the report, not a traceback
            summary["error"] = f"{type(error).__name__}: {error}"
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(summary, indent=2))
            print("\nALiS fetch failed; the registry on disk was left untouched.", file=sys.stderr)
            return 1

        summary["fetched"] = True
        summary["fetch_reports"] = reports

        refreshed = normalize(live_rows, existing_records)
        merged, carried = merge_with_untouched(refreshed, existing_records)
        summary["records_refreshed"] = len(refreshed)
        summary["records_carried_forward"] = carried
        summary["records_after"] = len(merged)

        credible, reason = credibility_check(len(merged), len(existing_records))
        summary["credibility"] = reason
        if not credible:
            summary["error"] = reason
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(summary, indent=2))
            print(f"\nRefusing to write: {reason}", file=sys.stderr)
            return 1

        previous_credentials = {r.get("credential_number") for r in existing_records}
        new_credentials = {r.get("credential_number") for r in merged}
        summary["licences_added"] = sorted(new_credentials - previous_credentials)[:50]
        summary["licences_removed"] = sorted(previous_credentials - new_credentials)[:50]
        summary["licences_added_count"] = len(new_credentials - previous_credentials)
        summary["licences_removed_count"] = len(previous_credentials - new_credentials)

        if not args.dry_run:
            document = {
                "schema_version": SCHEMA_VERSION,
                "source": {
                    "authority": "Nevada Division of Public and Behavioral Health, "
                                 "Health Care Quality and Compliance (HCQC) / ALiS",
                    "scope": "Nevada statewide; active credentials only"
                             if args.statewide
                             else "Clark County; active credentials only",
                    "license_types_refreshed": list(LICENSE_TYPES),
                    "record_count": len(merged),
                    "refreshed_at": summary["ran_at"],
                },
                "policy": existing.get("policy", {}),
                "records": merged,
            }
            REGISTRY_PATH.write_text(
                json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
            summary["written"] = True
            print(f"Wrote {REGISTRY_PATH.relative_to(REPO_ROOT)} — {len(merged)} records", flush=True)

    if args.apply and not args.dry_run:
        print("Applying to the database...", flush=True)
        summary["database"] = apply_to_database()
        summary["applied"] = True

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
