#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.government_identity_media import coverage_summary  # noqa: E402

CANONICAL_PATH = REPO_ROOT / "database" / "florida_facility_universe_canonical.json"
REGISTRY_PATH = REPO_ROOT / "database" / "facility_media_registry.json"
JSON_REPORT_PATH = REPO_ROOT / "reports" / "GOVERNMENT_IDENTITY_MEDIA_COVERAGE.json"
MARKDOWN_REPORT_PATH = REPO_ROOT / "reports" / "GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def main() -> int:
    canonical = load_json(CANONICAL_PATH)
    registry = load_json(REGISTRY_PATH)
    canonical_rows = [row for row in canonical.get("records") or [] if isinstance(row, dict)]
    canonical_by_id = {str(row.get("canonical_id") or ""): row for row in canonical_rows}
    registry_by_id = {
        str(record.get("canonical_facility_id") or ""): record
        for record in registry.get("records") or []
        if isinstance(record, dict) and str(record.get("canonical_facility_id") or "")
    }
    records = []
    for canonical_id, canonical_row in canonical_by_id.items():
        record = registry_by_id.get(canonical_id, {})
        records.append(
            {
                "market": canonical_row.get("county") or canonical_row.get("city") or "UNKNOWN",
                "operator_name": record.get("operator_name") or "UNKNOWN",
                "canonical_facility_id": canonical_id,
                "facility_name": canonical_row.get("facility_name") or "",
                **record,
            }
        )

    baseline = coverage_summary(records, total_facilities=len(canonical_rows))
    payload = {
        "report_status": "BASELINE_COMPLETE_PILOT_WRITE_NOT_AUTHORIZED",
        "baseline": baseline,
        "post_pilot": baseline,
        "delta": {
            "newly_verified_facility_images": 0,
            "newly_rejected_images": 0,
            "registry_records_written": 0,
        },
        "notes": [
            "No production registry write was authorized; the network pilot remained dry-run only.",
            "Legacy VERIFIED labels without explicit acceptable display rights are counted as PROVISIONAL.",
            "Photography is presentation-only and is not consumed by ranking or recommendation logic.",
        ],
    }
    write_json(JSON_REPORT_PATH, payload)

    rejection_lines = baseline["top_image_rejection_reasons"] or [{"reason": "None recorded", "count": 0}]
    markdown = [
        "# Government Identity Media Coverage",
        "",
        f"Generated: {baseline['generated_at_utc']}",
        "",
        "## Run Status",
        "",
        "Baseline complete. Production registry writes were not authorized, so the pilot remained a dry run and post-pilot coverage equals baseline.",
        "",
        "## Coverage",
        "",
        "| Metric | Baseline | Post-pilot |",
        "| --- | ---: | ---: |",
    ]
    metrics = [
        ("Total facilities", "total_facilities"),
        ("Facilities with authoritative identity", "facilities_with_authoritative_identity"),
        ("Facilities searched", "facilities_searched"),
        ("Official domains found", "official_domains_found"),
        ("Exact facility pages verified", "exact_facility_pages_verified"),
        ("Operator-only pages found", "operator_only_pages_found"),
        ("Verified images", "verified_images"),
        ("Provisional images", "provisional_images"),
        ("Ambiguous images", "ambiguous_images"),
        ("Rejected images", "rejected_images"),
        ("Missing images", "missing_images"),
        ("Display-rights-uncertain images", "display_rights_uncertain_images"),
        ("Broken images", "broken_images"),
        ("Percentage verified", "percentage_verified"),
        ("Average processing time (seconds)", "average_processing_time_seconds"),
        ("Records due for recheck", "records_due_for_recheck"),
    ]
    markdown.extend(f"| {label} | {baseline[key]} | {baseline[key]} |" for label, key in metrics)
    markdown.extend(["", "## Image Rejection Reasons", "", "| Reason | Count |", "| --- | ---: |"])
    markdown.extend(f"| {item['reason']} | {item['count']} |" for item in rejection_lines)
    markdown.extend(
        [
            "",
            "## Governance",
            "",
            "Only records with image status `VERIFIED`, exact facility identity, an eligible primary category, a reachable image, and acceptable display rights may be displayed normally. Legacy records are not upgraded automatically.",
            "",
            "Coverage by market, coverage by operator, search failures, identity conflicts, and full rejection distributions are retained in the JSON report.",
            "",
        ]
    )
    MARKDOWN_REPORT_PATH.write_text("\n".join(markdown), encoding="utf-8", newline="\n")
    print(json.dumps(payload["delta"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())