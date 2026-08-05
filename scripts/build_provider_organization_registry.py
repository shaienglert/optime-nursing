#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.provider_organization_registry import build_provider_organization_registry, utc_now_iso

CANONICAL_PATH = REPO_ROOT / "database" / "nevada_facility_universe_canonical.json"
PILOT_PATH = REPO_ROOT / "reports" / "MEDIA_LIVE_PILOT_100.json"
REGISTRY_PATH = REPO_ROOT / "database" / "provider_organization_registry.json"
REPORT_MD_PATH = REPO_ROOT / "reports" / "PROVIDER_ORGANIZATION_REGISTRY_REPORT.md"
REPORT_JSON_PATH = REPO_ROOT / "reports" / "PROVIDER_ORGANIZATION_REGISTRY_REPORT.json"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def main() -> int:
    canonical_payload = load_json(CANONICAL_PATH)
    pilot_payload = load_json(PILOT_PATH)

    facilities: List[Dict[str, Any]] = [
        row
        for row in (canonical_payload.get("records") or [])
        if isinstance(row, dict) and bool(row.get("is_las_vegas_valley"))
    ]

    pilot_records = {
        str(row.get("canonical_facility_id") or "").strip(): row
        for row in (pilot_payload.get("records") or [])
        if isinstance(row, dict) and str(row.get("canonical_facility_id") or "").strip()
    }

    registry_payload = build_provider_organization_registry(facilities=facilities, pilot_records=pilot_records)
    save_json(REGISTRY_PATH, registry_payload)

    metrics = registry_payload.get("metrics") or {}
    relationships = registry_payload.get("facility_relationships") or []
    unresolved = registry_payload.get("unresolved_duplicate_candidates") or []

    report_json = {
        "generated_at_utc": utc_now_iso(),
        "source": "provider_organization_registry",
        "total_canonical_facilities_evaluated": len(facilities),
        "organizations_identified": metrics.get("organizations_identified") or 0,
        "independent_facilities": registry_payload.get("independent_facility_count") or 0,
        "facility_to_operator_links": metrics.get("facility_to_operator_links") or 0,
        "facility_to_owner_links": metrics.get("facility_to_owner_links") or 0,
        "parent_company_links": metrics.get("parent_company_links") or 0,
        "verified_official_domains": metrics.get("verified_official_domains") or 0,
        "exact_location_directories_found": sum(
            1
            for row in registry_payload.get("records") or []
            if str(row.get("official_locations_directory_url") or "").strip()
        ),
        "exact_facility_location_pages_resolved": sum(
            1
            for row in pilot_records.values()
            if str(row.get("official_facility_page_url") or "").strip()
        ),
        "unresolved_organization_identities": len(unresolved),
        "duplicate_candidates": len(unresolved),
        "ownership_conflicts": sum(1 for row in relationships if str(row.get("relationship_type") or "") == "parent_company" and str((row.get("source_evidence") or {}).get("note") or "").strip()),
        "organization_changes_acquisitions": 0,
        "top_organizations_by_facility_count": metrics.get("top_organizations_by_facility_count") or [],
        "percent_facilities_covered_by_verified_org_domains": round(
            ((metrics.get("facilities_covered_by_verified_domains") or 0) / len(facilities) * 100.0) if facilities else 0.0,
            3,
        ),
    }
    save_json(REPORT_JSON_PATH, report_json)

    lines: List[str] = []
    lines.append("# Provider Organization Registry Report")
    lines.append("")
    lines.append(f"Generated at: `{report_json['generated_at_utc']}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total canonical facilities evaluated: **{report_json['total_canonical_facilities_evaluated']}**")
    lines.append(f"- Organizations identified: **{report_json['organizations_identified']}**")
    lines.append(f"- Independent facilities: **{report_json['independent_facilities']}**")
    lines.append(f"- Facility-to-operator links: **{report_json['facility_to_operator_links']}**")
    lines.append(f"- Facility-to-owner links: **{report_json['facility_to_owner_links']}**")
    lines.append(f"- Parent-company links: **{report_json['parent_company_links']}**")
    lines.append(f"- Verified official domains: **{report_json['verified_official_domains']}**")
    lines.append(f"- Exact location directories found: **{report_json['exact_location_directories_found']}**")
    lines.append(f"- Exact facility location pages resolved: **{report_json['exact_facility_location_pages_resolved']}**")
    lines.append(f"- Unresolved organization identities: **{report_json['unresolved_organization_identities']}**")
    lines.append(f"- Duplicate candidates: **{report_json['duplicate_candidates']}**")
    lines.append(f"- Ownership conflicts: **{report_json['ownership_conflicts']}**")
    lines.append(f"- Organization changes/acquisitions: **{report_json['organization_changes_acquisitions']}**")
    lines.append(f"- Percentage of facilities covered by verified organization domains: **{report_json['percent_facilities_covered_by_verified_org_domains']}%**")
    lines.append("")
    lines.append("## Top Organizations By Facility Count")
    lines.append("")
    lines.append("| organization_id | legal_name | facility_count |")
    lines.append("| --- | --- | ---: |")
    for item in report_json["top_organizations_by_facility_count"]:
        lines.append(f"| {item.get('organization_id') or ''} | {item.get('legal_name') or ''} | {int(item.get('facility_count') or 0)} |")

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print("REGISTRY:", REGISTRY_PATH)
    print("REPORT JSON:", REPORT_JSON_PATH)
    print("REPORT MD:", REPORT_MD_PATH)
    print("ORGANIZATIONS IDENTIFIED:", report_json["organizations_identified"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
