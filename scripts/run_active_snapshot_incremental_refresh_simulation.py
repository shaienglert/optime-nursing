from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.facility_snapshot_simulation import ActiveFacilitySnapshotStore


REPORT_JSON = REPO_ROOT / "reports" / "ACTIVE_SNAPSHOT_INCREMENTAL_REFRESH_SIMULATION.json"
REPORT_MD = REPO_ROOT / "reports" / "ACTIVE_SNAPSHOT_INCREMENTAL_REFRESH_SIMULATION.md"

FACILITY_IDS = [
    "CMS-105460",
    "NPI-1073336319",
    "NPI-1083043830",
]
PARAMETER_IDS = ["pt", "nursing_24_7", "speech_therapy"]
FAMILY_NEEDS = [
    {
        "parameter_id": "pt",
        "requirement_level": "REQUIRED",
        "desired_value": "YES",
        "acceptable_values": ["YES"],
    },
    {
        "parameter_id": "nursing_24_7",
        "requirement_level": "HIGH",
        "desired_value": "YES",
        "acceptable_values": ["YES"],
    },
]


def _facility_rows(results: List[Dict[str, Any]]) -> List[List[str]]:
    rows = []
    for item in results:
        rows.append(
            [
                str(item["canonical_facility_id"]),
                str(item["snapshot_version"]),
                str(item["last_successful_refresh"]),
                ", ".join(item["changed_parameters_since_previous_snapshot"]) or "None",
                str(item["unchanged_parameters_reused"]),
                ", ".join(item["stale_parameters"]) or "None",
                ", ".join(item["missing_parameters"]) or "None",
                str(item["eligibility_status"]),
                f"{float(item['match_score']):.2f}",
                f"{float(item['recommendation_response_time_ms']):.3f}",
            ]
        )
    return rows


def _markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(output)


def _write_reports(payload: Dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checks = payload["proof"]
    markdown = [
        "# Active Snapshot Incremental Refresh Simulation",
        "",
        "## Contract",
        "",
        "- Recommendation input: currently active, precomputed OPTIME facility snapshot only.",
        "- Internet crawling during recommendation: **NO**.",
        "- Facility profile rebuild during recommendation/simulation: **NO**.",
        f"- Initial active snapshot: `{payload['before']['active_snapshot_version']}`.",
        f"- Updated active snapshot: `{payload['after']['active_snapshot_version']}`.",
        f"- One-time local snapshot hydration: **{payload['snapshot_hydration_time_ms']:.3f} ms** (outside family response timing).",
        "",
        "## Before Source Update",
        "",
        _markdown_table(
            [
                "Facility",
                "Facility snapshot",
                "Last refresh",
                "Changed",
                "Reused",
                "Stale",
                "Missing",
                "Eligibility",
                "Score",
                "Response ms",
            ],
            _facility_rows(payload["before"]["results"]),
        ),
        "",
        "## Simulated Source Update",
        "",
        f"- Facility: `{payload['source_update']['affected_facilities'][0]}`",
        f"- Changed parameter: `{payload['source_update']['changed_parameters'][0]}` from UNKNOWN to YES.",
        f"- Incremental activation time: **{payload['source_update_time_ms']:.3f} ms**.",
        f"- Unchanged facilities reused: {', '.join(payload['source_update']['unchanged_facilities_reused'])}.",
        "",
        "## After Source Update",
        "",
        _markdown_table(
            [
                "Facility",
                "Facility snapshot",
                "Last refresh",
                "Changed",
                "Reused",
                "Stale",
                "Missing",
                "Eligibility",
                "Score",
                "Response ms",
            ],
            _facility_rows(payload["after"]["results"]),
        ),
        "",
        "## Proof",
        "",
    ]
    for name, value in checks.items():
        markdown.append(f"- {'PASS' if value else 'FAIL'}: `{name}`")
    markdown.extend(
        [
            "",
            "The numeric match score is recalculated under existing engine semantics. UNKNOWN is neutral; therefore the proof requires a changed recommendation result and improved eligibility, not a presumption that every confirmation increases a score.",
            "",
        ]
    )
    REPORT_MD.write_text("\n".join(markdown), encoding="utf-8")


def main() -> None:
    hydration_start = time.perf_counter()
    store = ActiveFacilitySnapshotStore.from_active_runtime(
        facility_ids=FACILITY_IDS,
        parameter_ids=PARAMETER_IDS,
        stale_after_days=180,
    )
    hydration_time_ms = round((time.perf_counter() - hydration_start) * 1000, 3)

    unaffected_identities = {
        facility_id: store.facility_object_identity(facility_id)
        for facility_id in FACILITY_IDS
        if facility_id != "CMS-105460"
    }
    before = store.recommend(needs=FAMILY_NEEDS, limit=len(FACILITY_IDS))
    before_by_id = {item["canonical_facility_id"]: item for item in before["results"]}

    update_start = time.perf_counter()
    source_update = store.apply_source_update(
        canonical_facility_id="CMS-105460",
        parameter_updates={
            "pt": {
                "raw_value": "YES",
                "status_value": "YES",
                "source": "Simulated prepared source release",
                "evidence_confidence": "HIGH",
                "evidence_strength": "HIGH",
                "provenance": {
                    "source_family": "SIMULATED_PREPARED_SOURCE",
                    "network_access_during_recommendation": False,
                },
            }
        },
        source_update_id="simulation-source-release-pt-001",
    )
    source_update_time_ms = round((time.perf_counter() - update_start) * 1000, 3)
    after = store.recommend(needs=FAMILY_NEEDS, limit=len(FACILITY_IDS))
    after_by_id = {item["canonical_facility_id"]: item for item in after["results"]}
    diagnostics = store.diagnostics()

    unaffected_reused = all(
        store.facility_object_identity(facility_id) == identity
        for facility_id, identity in unaffected_identities.items()
    )
    target_before = before_by_id["CMS-105460"]
    target_after = after_by_id["CMS-105460"]
    proof = {
        "recommendation_used_active_snapshot_only": before["snapshot_only"] and after["snapshot_only"],
        "no_internet_crawl_during_recommendation": diagnostics["network_request_count"] == 0,
        "no_facility_profile_rebuild": diagnostics["profile_rebuild_count"] == 0,
        "only_affected_facility_refreshed": diagnostics["facility_refresh_counts"]
        == {"CMS-105460": 1, "NPI-1073336319": 0, "NPI-1083043830": 0},
        "only_affected_parameter_refreshed": diagnostics["parameter_refresh_counts"]["CMS-105460"] == {"pt": 1},
        "active_snapshot_version_updated": before["active_snapshot_version"] != after["active_snapshot_version"],
        "recommendation_recalculated": (
            target_before["match_score"] != target_after["match_score"]
            and target_before["eligibility_status"] != target_after["eligibility_status"]
        ),
        "unchanged_facility_objects_reused": unaffected_reused,
        "family_response_fast_before": before["recommendation_response_time_ms"] < 250,
        "family_response_fast_after": after["recommendation_response_time_ms"] < 250,
    }
    payload = {
        "simulation": "active_snapshot_incremental_refresh",
        "snapshot_hydration_time_ms": hydration_time_ms,
        "source_update_time_ms": source_update_time_ms,
        "family_response_target_ms": 250,
        "before": before,
        "source_update": source_update,
        "after": after,
        "diagnostics": diagnostics,
        "proof": proof,
        "all_checks_passed": all(proof.values()),
    }
    _write_reports(payload)
    print(json.dumps(payload, indent=2))
    if not payload["all_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()