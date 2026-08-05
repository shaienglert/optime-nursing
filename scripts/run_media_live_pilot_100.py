#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.pilot_facility_media_discovery import FacilitySeed  # noqa: E402
from scripts.run_statewide_facility_media_discovery import discover_with_retries  # noqa: E402


CANONICAL_PATH = REPO_ROOT / "database" / "nevada_facility_universe_canonical.json"
REGISTRY_PATH = REPO_ROOT / "database" / "facility_media_registry.json"
ACTIVE_REGION_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "assessment-region.ts"
RECOMMENDATION_SNAPSHOT_PATH = REPO_ROOT / "reports" / "ACTIVE_SNAPSHOT_INCREMENTAL_REFRESH_SIMULATION.json"

OUTPUT_JSON = REPO_ROOT / "reports" / "MEDIA_LIVE_PILOT_100.json"
OUTPUT_MD = REPO_ROOT / "reports" / "MEDIA_LIVE_PILOT_100.md"

TARGET_FACILITY_COUNT = 100
MAX_CANDIDATES = 8
MAX_RETRIES = 2
CONCURRENCY = 2

LAS_VEGAS_CITY_ALLOWLIST = {
    "las vegas",
    "north las vegas",
    "henderson",
    "paradise",
    "spring valley",
    "enterprise",
    "summerlin",
    "centennial hills",
}

DISPLAYABLE_RIGHTS = {"OFFICIAL_DISPLAY_ALLOWED", "OWNER_AUTHORIZED", "LICENSED_EXTERNAL"}
DIRECTORY_DOMAIN_BLOCKLIST = {
    "aplaceformom.com",
    "caring.com",
    "seniorly.com",
    "seniorhousingnet.com",
    "assistedliving.org",
    "nursinghomes.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "bing.com",
    "duckduckgo.com",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def domain_of(url: str) -> str:
    text = str(url or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"^https?://", "", text)
    host = text.split("/", 1)[0].strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_directory_domain(url: str) -> bool:
    host = domain_of(url)
    if not host:
        return False
    return any(host == blocked or host.endswith(f".{blocked}") for blocked in DIRECTORY_DOMAIN_BLOCKLIST)


def parse_active_market() -> Dict[str, str]:
    content = ACTIVE_REGION_PATH.read_text(encoding="utf-8")
    configured_match = re.search(r'NEXT_PUBLIC_ASSESSMENT_REGION\s*\|\|\s*"([^"]+)"', content)
    configured_region = configured_match.group(1) if configured_match else "las-vegas"
    region_block = re.search(r'"las-vegas"\s*:\s*\{(.*?)\n\s*\},', content, flags=re.S)
    market_name = "Las Vegas, Nevada"
    region_name = "Las Vegas Valley"
    if region_block:
        block = region_block.group(1)
        market_match = re.search(r'marketName:\s*"([^"]+)"', block)
        region_name_match = re.search(r'regionName:\s*"([^"]+)"', block)
        if market_match:
            market_name = market_match.group(1)
        if region_name_match:
            region_name = region_name_match.group(1)
    return {
        "configured_region": configured_region,
        "market_name": market_name,
        "region_name": region_name,
    }


def recommendation_ids_from_snapshot() -> List[str]:
    if not RECOMMENDATION_SNAPSHOT_PATH.exists():
        return []
    payload = load_json(RECOMMENDATION_SNAPSHOT_PATH)
    ids: List[str] = []
    for item in payload.get("recommendations") or []:
        canonical_id = str(item.get("canonical_facility_id") or "").strip()
        if canonical_id:
            ids.append(canonical_id)
    deduped: List[str] = []
    seen: set[str] = set()
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def source_name(row: Dict[str, Any]) -> str:
    evidence = row.get("source_evidence") or {}
    for value in evidence.values():
        if isinstance(value, dict):
            name = str(value.get("source_name") or "").strip()
            if name:
                return name
    return "UNKNOWN"


def record_has_verified_image(registry_row: Optional[Dict[str, Any]]) -> bool:
    if not registry_row:
        return False
    if registry_row.get("verified_facility_specific") is not True:
        return False
    if str(registry_row.get("image_status") or "").upper() != "VERIFIED":
        return False
    if not str(registry_row.get("primary_image_url") or "").strip():
        return False
    rights = str(registry_row.get("display_rights_status") or "").upper().strip()
    return rights in DISPLAYABLE_RIGHTS


def is_complete_identity(row: Dict[str, Any]) -> bool:
    required = ("canonical_id", "facility_name", "address", "city", "state")
    return all(str(row.get(field) or "").strip() for field in required)


def build_seed(row: Dict[str, Any]) -> FacilitySeed:
    source_ids = row.get("source_identity_ids") or {}
    return FacilitySeed(
        canonical_facility_id=str(row.get("canonical_id") or "").strip(),
        facility_name=str(row.get("facility_name") or "").strip(),
        city=str(row.get("city") or "").strip(),
        state=str(row.get("state") or "").strip() or "NV",
        address=str(row.get("address") or "").strip(),
        phone=str(row.get("phone") or "").strip(),
        cms_ccn=str(source_ids.get("cms_ccn") or row.get("ccn") or "").strip(),
    )


@dataclass
class SelectedFacility:
    seed: FacilitySeed
    canonical_row: Dict[str, Any]
    authoritative_identity_source: str
    selection_priority: int


def is_las_vegas_market_row(row: Dict[str, Any]) -> bool:
    state = str(row.get("state") or "").strip().upper()
    city = str(row.get("city") or "").strip().lower()
    if state and state != "NV":
        return False
    if bool(row.get("is_las_vegas_valley")):
        return True
    return city in LAS_VEGAS_CITY_ALLOWLIST


def select_facilities(
    canonical_rows: List[Dict[str, Any]],
    registry_by_id: Dict[str, Dict[str, Any]],
    recommendation_ids: Iterable[str],
) -> Tuple[List[SelectedFacility], Dict[str, int]]:
    recommendation_set = set(recommendation_ids)

    market_rows = [row for row in canonical_rows if is_las_vegas_market_row(row)]

    rows_by_id = {
        str(row.get("canonical_id") or "").strip(): row
        for row in market_rows
        if isinstance(row, dict) and str(row.get("canonical_id") or "").strip()
    }

    selected: List[SelectedFacility] = []
    used: set[str] = set()

    def append_if_possible(canonical_id: str, priority: int) -> None:
        if canonical_id in used:
            return
        row = rows_by_id.get(canonical_id)
        if not row:
            return
        if not is_complete_identity(row):
            return
        selected.append(
            SelectedFacility(
                seed=build_seed(row),
                canonical_row=row,
                authoritative_identity_source=source_name(row),
                selection_priority=priority,
            )
        )
        used.add(canonical_id)

    for canonical_id in recommendation_set:
        append_if_possible(canonical_id, 1)

    for row in market_rows:
        canonical_id = str(row.get("canonical_id") or "").strip()
        if not canonical_id:
            continue
        if bool(row.get("is_las_vegas_valley")):
            append_if_possible(canonical_id, 2)

    for row in market_rows:
        canonical_id = str(row.get("canonical_id") or "").strip()
        if not canonical_id or canonical_id in used:
            continue
        registry_row = registry_by_id.get(canonical_id)
        if not record_has_verified_image(registry_row):
            append_if_possible(canonical_id, 3)

    selected = selected[:TARGET_FACILITY_COUNT]
    counts = Counter(item.selection_priority for item in selected)
    return selected, {
        "priority_1_recommendation": counts.get(1, 0),
        "priority_2_launch_market": counts.get(2, 0),
        "priority_3_complete_identity_missing_verified_image": counts.get(3, 0),
    }


def run_discovery(selected: List[SelectedFacility]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {
            pool.submit(
                discover_with_retries,
                item.seed,
                None,
                item.canonical_row,
                max_candidates=MAX_CANDIDATES,
                max_retries=MAX_RETRIES,
            ): item
            for item in selected
        }
        completed = 0
        total = len(futures)
        for future in as_completed(futures):
            item = futures[future]
            result = future.result()
            result["selection_priority"] = item.selection_priority
            result["authoritative_identity_source"] = item.authoritative_identity_source
            records.append(result)
            completed += 1
            print(f"DISCOVERY {completed}/{total}: {item.seed.canonical_facility_id}")
    records.sort(key=lambda row: str(row.get("canonical_facility_id") or ""))
    return records


def top_failure_reasons(records: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in records:
        if row.get("identity_verified") is not True:
            counts[f"IDENTITY:{str(row.get('identity_status') or 'UNKNOWN').upper()}"] += 1
        rejection = str(row.get("rejection_reason") or "").strip().upper()
        if rejection:
            counts[f"IMAGE_REJECTION:{rejection}"] += 1
        probe = str(row.get("image_probe_status") or "").strip().upper()
        if probe and probe not in {"", "OK", "NOT_CHECKED"}:
            counts[f"IMAGE_PROBE:{probe}"] += 1
        search_fail = str(row.get("search_failure_reason") or "").strip().upper()
        if search_fail:
            counts[f"SEARCH:{search_fail}"] += 1
        if not str(row.get("primary_image_url") or "").strip():
            counts["MISSING_PRIMARY_IMAGE"] += 1
    return [{"reason": reason, "count": count} for reason, count in counts.most_common(limit)]


def compute_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    processed = len(records)
    official_domains = sum(1 for row in records if str(row.get("official_domain") or row.get("official_website_url") or "").strip())
    exact_pages = sum(1 for row in records if str(row.get("official_facility_page_url") or "").strip())
    operator_only = sum(1 for row in records if str(row.get("identity_status") or "") == "OFFICIAL_OPERATOR_FOUND_LOCATION_UNVERIFIED")
    candidate_images = sum(1 for row in records if int(row.get("evaluated_image_count") or 0) > 0)
    accepted_images = sum(
        1
        for row in records
        if row.get("verified_facility_specific") is True
        and str(row.get("image_status") or "").upper() == "VERIFIED"
        and str(row.get("display_rights_status") or "").upper() in DISPLAYABLE_RIGHTS
    )
    rejected_images = sum(1 for row in records if str(row.get("image_status") or "").upper() in {"REJECTED", "AMBIGUOUS"})
    rights_uncertain = sum(
        1
        for row in records
        if str(row.get("display_rights_status") or "").upper() in {"", "UNKNOWN", "OFFICIAL_SOURCE_TERMS_UNCLEAR"}
        and str(row.get("primary_image_url") or "").strip()
    )
    missing_images = sum(
        1
        for row in records
        if not str(row.get("primary_image_url") or "").strip() or str(row.get("image_status") or "").upper() in {"MISSING", "UNKNOWN", "NOT_VERIFIED"}
    )
    processing_times = [float(row.get("processing_time_seconds")) for row in records if isinstance(row.get("processing_time_seconds"), (int, float))]
    average_seconds = round(sum(processing_times) / len(processing_times), 3) if processing_times else 0.0

    return {
        "facilities_processed": processed,
        "official_domains_found": official_domains,
        "exact_facility_pages_verified": exact_pages,
        "operator_only_pages_found": operator_only,
        "candidate_images_found": candidate_images,
        "images_accepted_facility_specific": accepted_images,
        "images_rejected_or_ambiguous": rejected_images,
        "images_blocked_by_rights_uncertainty": rights_uncertain,
        "images_missing": missing_images,
        "top_20_failure_reasons": top_failure_reasons(records, limit=20),
        "average_processing_time_seconds": average_seconds,
    }


def evaluate_owner_gate(records: List[Dict[str, Any]], metrics: Dict[str, Any], baseline_displayable: int) -> Dict[str, Any]:
    official_urls = [str(row.get("official_website_url") or row.get("official_domain") or "").strip() for row in records]
    directory_official = [url for url in official_urls if url and is_directory_domain(url)]

    operator_as_facility = sum(
        1
        for row in records
        if row.get("verified_facility_specific") is True
        and str((row.get("image_match_evidence") or {}).get("reason") or "").upper() in {"CORPORATE_OR_STOCK_IMAGE", "STOCK_LIKE_ASSET"}
    )

    displayable_unclear = sum(
        1
        for row in records
        if row.get("verified_facility_specific") is True
        and str(row.get("display_rights_status") or "").upper() not in DISPLAYABLE_RIGHTS
    )

    processed = max(1, int(metrics["facilities_processed"]))
    exact_pages = int(metrics["exact_facility_pages_verified"])
    accepted_images = int(metrics["images_accepted_facility_specific"])

    conditions = {
        "no_directory_source_became_official": len(directory_official) == 0,
        "no_operator_wide_image_became_facility_specific": operator_as_facility == 0,
        "no_unclear_rights_image_became_displayable": displayable_unclear == 0,
        "at_least_20pct_exact_facility_pages": (exact_pages / processed) >= 0.20,
        "at_least_10_newly_displayable_images": accepted_images - baseline_displayable >= 10,
    }

    passed = all(conditions.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "conditions": conditions,
        "directory_official_urls": directory_official,
        "operator_wide_false_positive_count": operator_as_facility,
        "displayable_unclear_rights_count": displayable_unclear,
        "baseline_displayable_images": baseline_displayable,
        "final_displayable_images": accepted_images,
        "new_displayable_images": accepted_images - baseline_displayable,
    }


def processing_time_table(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    table: List[Dict[str, Any]] = []
    for row in records:
        table.append(
            {
                "canonical_facility_id": str(row.get("canonical_facility_id") or ""),
                "facility_name": str(row.get("facility_name") or ""),
                "processing_time_seconds": float(row.get("processing_time_seconds") or 0.0),
            }
        )
    table.sort(key=lambda item: item["processing_time_seconds"], reverse=True)
    return table


def write_markdown_report(
    *,
    active_market: Dict[str, str],
    selection: List[SelectedFacility],
    selection_counts: Dict[str, int],
    metrics: Dict[str, Any],
    owner_gate: Dict[str, Any],
    records: List[Dict[str, Any]],
    started_at: float,
) -> None:
    elapsed = round(time.monotonic() - started_at, 3)
    lines: List[str] = []
    lines.append("# MEDIA LIVE PILOT 100")
    lines.append("")
    lines.append(f"Generated at: `{utc_now_iso()}`")
    lines.append(f"Active market: **{active_market['market_name']}** ({active_market['region_name']})")
    lines.append(f"Configured region key: `{active_market['configured_region']}`")
    lines.append("")
    lines.append("## Step 1 - Selection")
    lines.append("")
    lines.append(f"- Target facilities: **{TARGET_FACILITY_COUNT}**")
    lines.append(f"- Selected facilities: **{len(selection)}**")
    lines.append(f"- Priority 1 (current recommendation result): **{selection_counts['priority_1_recommendation']}**")
    lines.append(f"- Priority 2 (active launch market): **{selection_counts['priority_2_launch_market']}**")
    lines.append(f"- Priority 3 (complete identity + missing verified image): **{selection_counts['priority_3_complete_identity_missing_verified_image']}**")
    if len(selection) < TARGET_FACILITY_COUNT:
        lines.append(f"- Data limitation: **only {len(selection)} eligible facilities available** under governed selection constraints.")
    lines.append("")
    lines.append("| canonical facility ID | facility name | city | state | authoritative identity source | selection priority |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for item in selection:
        lines.append(
            f"| {item.seed.canonical_facility_id} | {item.seed.facility_name} | {item.seed.city} | {item.seed.state} | {item.authoritative_identity_source} | {item.selection_priority} |"
        )

    lines.append("")
    lines.append("## Step 2/3 - Live Dry-Run Discovery Summary")
    lines.append("")
    lines.append(f"- Facilities processed: **{metrics['facilities_processed']}**")
    lines.append(f"- Official domains found: **{metrics['official_domains_found']}**")
    lines.append(f"- Exact facility pages verified: **{metrics['exact_facility_pages_verified']}**")
    lines.append(f"- Operator-only pages found: **{metrics['operator_only_pages_found']}**")
    lines.append(f"- Candidate images found: **{metrics['candidate_images_found']}**")
    lines.append(f"- Images accepted as facility-specific: **{metrics['images_accepted_facility_specific']}**")
    lines.append(f"- Images rejected as stock/corporate/logo/staff/unrelated: **{metrics['images_rejected_or_ambiguous']}**")
    lines.append(f"- Images blocked by rights uncertainty: **{metrics['images_blocked_by_rights_uncertainty']}**")
    lines.append(f"- Images missing: **{metrics['images_missing']}**")
    lines.append(f"- Average processing time per facility (seconds): **{metrics['average_processing_time_seconds']}**")
    lines.append("")
    lines.append("### Top 20 failure reasons")
    for row in metrics["top_20_failure_reasons"]:
        lines.append(f"- {row['reason']}: {row['count']}")

    lines.append("")
    lines.append("## Step 4 - Owner Gate")
    lines.append("")
    lines.append(f"Owner gate status: **{owner_gate['status']}**")
    for key, value in owner_gate["conditions"].items():
        lines.append(f"- {key}: {'PASS' if value else 'FAIL'}")
    lines.append(f"- Baseline displayable image count (selected set): **{owner_gate['baseline_displayable_images']}**")
    lines.append(f"- Final displayable image count (dry-run result): **{owner_gate['final_displayable_images']}**")
    lines.append(f"- Exact increase: **{owner_gate['new_displayable_images']}**")

    if owner_gate["status"] == "FAIL":
        lines.append("")
        lines.append("Gate failed. Per governed instructions, registry write rerun and end-to-end publish validation were not executed.")

    lines.append("")
    lines.append("## Processing time per facility")
    lines.append("")
    lines.append("| canonical facility ID | facility name | seconds |")
    lines.append("| --- | --- | --- |")
    for row in processing_time_table(records):
        lines.append(f"| {row['canonical_facility_id']} | {row['facility_name']} | {row['processing_time_seconds']:.3f} |")

    lines.append("")
    lines.append(f"Total dry-run wall time (seconds): **{elapsed}**")

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    started_at = time.monotonic()
    canonical_payload = load_json(CANONICAL_PATH)
    canonical_rows = [row for row in canonical_payload.get("records") or [] if isinstance(row, dict)]

    registry_payload = load_json(REGISTRY_PATH) if REGISTRY_PATH.exists() else {"records": []}
    registry_by_id = {
        str(row.get("canonical_facility_id") or "").strip(): row
        for row in registry_payload.get("records") or []
        if isinstance(row, dict) and str(row.get("canonical_facility_id") or "").strip()
    }

    active_market = parse_active_market()
    recommendation_ids = recommendation_ids_from_snapshot()

    selection, selection_counts = select_facilities(canonical_rows, registry_by_id, recommendation_ids)
    baseline_displayable = sum(
        1 for item in selection if record_has_verified_image(registry_by_id.get(item.seed.canonical_facility_id))
    )

    print("RUN MODE: network-enabled / read-only / non-persisting / no-registry-writes")
    print("ACTIVE MARKET:", active_market["market_name"])
    if active_market["market_name"].strip() != "Las Vegas, Nevada":
        print("STOP: active market is not Las Vegas, Nevada")
        return 2

    contains_florida = any(item.seed.state.strip().upper() == "FL" for item in selection)
    print("NO FLORIDA FACILITIES INCLUDED:", "PASS" if not contains_florida else "FAIL")
    if contains_florida:
        print("STOP: selection includes Florida facilities")
        return 3

    print("TARGET FACILITIES:", TARGET_FACILITY_COUNT)
    print("SELECTED FACILITIES:", len(selection))
    print("PRIORITY COUNTS:", selection_counts)
    print("SELECTED FACILITY LIST (pre-network):")
    for item in selection:
        print(
            " - "
            + item.seed.canonical_facility_id
            + " | "
            + item.seed.facility_name
            + " | "
            + item.seed.city
            + ", "
            + item.seed.state
            + " | source="
            + item.authoritative_identity_source
            + " | priority="
            + str(item.selection_priority)
        )
    if len(selection) < TARGET_FACILITY_COUNT:
        print(f"DATA LIMITATION: only {len(selection)} eligible Las Vegas facilities; running pilot on {len(selection)}.")

    records = run_discovery(selection)
    metrics = compute_metrics(records)
    owner_gate = evaluate_owner_gate(records, metrics, baseline_displayable)

    report_json = {
        "generated_at_utc": utc_now_iso(),
        "pipeline": "government-identity-first-live-pilot",
        "mode": "network-enabled-dry-run",
        "active_market": active_market,
        "target_facilities": TARGET_FACILITY_COUNT,
        "selected_facilities": len(selection),
        "selection_priority_counts": selection_counts,
        "selection": [
            {
                "canonical_facility_id": item.seed.canonical_facility_id,
                "facility_name": item.seed.facility_name,
                "city": item.seed.city,
                "state": item.seed.state,
                "authoritative_identity_source": item.authoritative_identity_source,
                "selection_priority": item.selection_priority,
            }
            for item in selection
        ],
        "baseline_verified_image_count": baseline_displayable,
        "summary": metrics,
        "owner_gate": owner_gate,
        "records": records,
    }

    save_json(OUTPUT_JSON, report_json)
    write_markdown_report(
        active_market=active_market,
        selection=selection,
        selection_counts=selection_counts,
        metrics=metrics,
        owner_gate=owner_gate,
        records=records,
        started_at=started_at,
    )

    print("REPORT JSON:", OUTPUT_JSON)
    print("REPORT MD:", OUTPUT_MD)
    print("OWNER GATE:", owner_gate["status"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
