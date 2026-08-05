#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pilot_facility_media_discovery import (  # noqa: E402
    CANONICAL_PATH,
    INVENTORY_PATH,
    REGISTRY_PATH,
    FacilitySeed,
    discover_media_for_facility,
    load_json,
    merge_registry,
    summarize,
    utc_now_iso,
)
from backend.app.services.government_identity_media import (  # noqa: E402
    PIPELINE_VERSION,
    build_authoritative_identity,
    classify_image_content,
    generate_search_queries,
    prioritize_facilities,
)

REPORT_PATH = REPO_ROOT / "reports" / "facility_media_statewide_progress.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume governed official-site and facility-image discovery across Florida.")
    parser.add_argument("--mode", choices=("pilot", "incremental"), default="pilot")
    parser.add_argument("--limit", type=int, default=20, help="Maximum facilities to process; 0 is allowed only in incremental mode.")
    parser.add_argument("--max-candidates", type=int, default=8, help="Maximum identity candidates evaluated per facility.")
    parser.add_argument("--checkpoint-every", type=int, default=5, help="Persist registry and progress after this many facilities.")
    parser.add_argument("--concurrency", type=int, default=2, help="Bounded worker count (1-8).")
    parser.add_argument("--max-retries", type=int, default=2, help="Safe retry attempts per facility (0-3).")
    parser.add_argument("--start-after", default="", help="Skip canonical records through this canonical facility ID.")
    parser.add_argument("--canonical-id", action="append", default=[], help="Process only this canonical facility ID; may be repeated.")
    parser.add_argument("--recommendation-id", action="append", default=[], help="Prioritize this canonical ID; may be repeated.")
    parser.add_argument("--launch-market", action="append", default=[], help="Configured launch market name; may be repeated.")
    parser.add_argument("--retry-unverified", action="store_true", help="Retry existing records that do not have a verified image.")
    parser.add_argument("--force", action="store_true", help="Reprocess selected records even when they already have a verified image.")
    parser.add_argument("--dry-run", action="store_true", help="Deprecated compatibility flag; dry run is already the default.")
    parser.add_argument("--write-registry", action="store_true", help="Explicitly authorize production registry and checkpoint writes.")
    return parser.parse_args()


def next_check_at() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def enrich_record(
    record: Dict[str, Any],
    *,
    canonical_row: Dict[str, Any],
    inventory_row: Optional[Dict[str, Any]],
    processing_time_seconds: float,
) -> Dict[str, Any]:
    identity = build_authoritative_identity(canonical_row, inventory_row)
    image_status = str(record.get("image_status") or "MISSING").upper()
    display_rights_status = "OFFICIAL_SOURCE_TERMS_UNCLEAR" if record.get("primary_image_url") else "UNKNOWN"
    if image_status == "VERIFIED" and display_rights_status not in {"OFFICIAL_DISPLAY_ALLOWED", "OWNER_AUTHORIZED", "LICENSED_EXTERNAL"}:
        image_status = "PROVISIONAL"
    checked_sources = record.get("checked_sources") or []
    now = utc_now_iso()
    return {
        **record,
        "facility_profile_id": identity.get("facility_profile_id") or "",
        "legal_name": identity.get("legal_name") or record.get("facility_name") or "",
        "DBA": identity.get("dba") or "",
        "authoritative_identity_sources": identity.get("authoritative_identity_sources") or {},
        "official_domain": str(record.get("official_website_url") or ""),
        "candidate_domains_reviewed": checked_sources,
        "search_queries_executed": generate_search_queries(identity),
        "identity_matches": list((record.get("identity_match_evidence") or {}).keys()),
        "identity_conflicts": identity.get("identity_conflicts") or [],
        "website_confidence": float(record.get("match_confidence") or 0.0),
        "primary_image_category": classify_image_content({"url": record.get("primary_image_url"), "alt_text": (record.get("image_match_evidence") or {}).get("alt_text")}),
        "image_source_page_url": str(record.get("image_source_url") or ""),
        "image_status": image_status if image_status in {"VERIFIED", "PROVISIONAL", "AMBIGUOUS", "REJECTED", "MISSING"} else "MISSING",
        "identity_confidence": float(record.get("match_confidence") or 0.0),
        "content_confidence": float((record.get("image_match_evidence") or {}).get("score") or 0.0),
        "display_rights_status": display_rights_status,
        "freshness_status": "CURRENT",
        "verified_facility_specific": bool(record.get("verified_facility_specific")) and image_status == "VERIFIED",
        "rejection_reason": "DISPLAY_RIGHTS_UNCLEAR" if image_status == "PROVISIONAL" else str((record.get("image_match_evidence") or {}).get("reason") or ""),
        "conflict_notes": "; ".join(str(item.get("field") or "") for item in identity.get("identity_conflicts") or []),
        "discovered_at": now,
        "verified_at": now if image_status == "VERIFIED" else "",
        "last_checked_at": now,
        "next_check_at": next_check_at(),
        "evidence": {"identity": identity, "legacy_discovery": record},
        "processing_time_seconds": round(processing_time_seconds, 3),
        "pipeline_version": PIPELINE_VERSION,
    }


def discover_with_retries(
    seed: FacilitySeed,
    inventory_row: Optional[Dict[str, Any]],
    canonical_row: Dict[str, Any],
    *,
    max_candidates: int,
    max_retries: int,
) -> Dict[str, Any]:
    started = time.monotonic()
    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            record = discover_media_for_facility(seed, inventory_row, max_candidates=max_candidates)
            record["retry_count"] = attempt
            return enrich_record(record, canonical_row=canonical_row, inventory_row=inventory_row, processing_time_seconds=time.monotonic() - started)
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
    return enrich_record(
        {
            "canonical_facility_id": seed.canonical_facility_id,
            "facility_name": seed.facility_name,
            "image_status": "MISSING",
            "search_failure_reason": type(last_error).__name__ if last_error else "UNKNOWN",
            "checked_sources": [],
            "retry_count": max_retries,
        },
        canonical_row=canonical_row,
        inventory_row=inventory_row,
        processing_time_seconds=time.monotonic() - started,
    )


def atomic_save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def inventory_by_cms_ccn(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for row in payload.get("records") or []:
        if not isinstance(row, dict):
            continue
        cms_ccn = str(row.get("cms_certification_number") or "").strip()
        if cms_ccn:
            result[cms_ccn] = row
    return result


def build_statewide_seeds(canonical_payload: Dict[str, Any]) -> List[FacilitySeed]:
    seeds: List[FacilitySeed] = []
    for row in canonical_payload.get("records") or []:
        if not isinstance(row, dict):
            continue
        canonical_id = str(row.get("canonical_id") or "").strip()
        facility_name = str(row.get("facility_name") or "").strip()
        if not canonical_id or not facility_name:
            continue
        source_identity_ids = row.get("source_identity_ids") or {}
        seeds.append(
            FacilitySeed(
                canonical_facility_id=canonical_id,
                facility_name=facility_name,
                city=str(row.get("city") or "").strip(),
                state=str(row.get("state") or "FL").strip() or "FL",
                address=str(row.get("address") or "").strip(),
                phone=str(row.get("phone") or "").strip(),
                cms_ccn=str(source_identity_ids.get("cms_ccn") or "").strip(),
            )
        )
    return seeds


def is_verified_image(record: Optional[Dict[str, Any]]) -> bool:
    return bool(
        record
        and record.get("verified_facility_specific") is True
        and str(record.get("image_status") or "").upper() == "VERIFIED"
        and str(record.get("primary_image_url") or "").strip()
    )


def select_pending_seeds(
    seeds: Iterable[FacilitySeed],
    existing_by_id: Dict[str, Dict[str, Any]],
    *,
    start_after: str,
    retry_unverified: bool,
    force: bool,
) -> List[FacilitySeed]:
    pending: List[FacilitySeed] = []
    reached_start = not start_after
    for seed in seeds:
        if not reached_start:
            if seed.canonical_facility_id == start_after:
                reached_start = True
            continue
        existing = existing_by_id.get(seed.canonical_facility_id)
        if force or existing is None:
            pending.append(seed)
        elif retry_unverified and not is_verified_image(existing):
            pending.append(seed)
    return pending


def build_progress_payload(
    registry_payload: Dict[str, Any],
    *,
    total_canonical: int,
    pending_at_start: int,
    processed_this_run: int,
    last_canonical_facility_id: str,
    run_status: str,
) -> Dict[str, Any]:
    records = [row for row in registry_payload.get("records") or [] if isinstance(row, dict)]
    registry_facility_count = len({str(row.get("canonical_facility_id") or "").strip() for row in records if str(row.get("canonical_facility_id") or "").strip()})
    return {
        "updated_at_utc": utc_now_iso(),
        "status": run_status,
        "total_canonical_facilities": total_canonical,
        "pending_at_run_start": pending_at_start,
        "processed_this_run": processed_this_run,
        "last_canonical_facility_id": last_canonical_facility_id,
        "registry_facility_count": registry_facility_count,
        "remaining_unscanned_facilities": max(0, total_canonical - registry_facility_count),
        "registry_summary": summarize(records),
    }


def persist_checkpoint(
    registry_payload: Dict[str, Any],
    *,
    total_canonical: int,
    pending_at_start: int,
    processed_this_run: int,
    last_canonical_facility_id: str,
    run_status: str,
) -> None:
    registry_payload["generated_at_utc"] = utc_now_iso()
    registry_payload["status"] = "STATEWIDE_DISCOVERY_IN_PROGRESS" if run_status == "RUNNING" else run_status
    atomic_save_json(REGISTRY_PATH, registry_payload)
    atomic_save_json(
        REPORT_PATH,
        build_progress_payload(
            registry_payload,
            total_canonical=total_canonical,
            pending_at_start=pending_at_start,
            processed_this_run=processed_this_run,
            last_canonical_facility_id=last_canonical_facility_id,
            run_status=run_status,
        ),
    )


def main() -> int:
    args = parse_args()
    if args.limit < 0 or args.max_candidates < 1 or args.checkpoint_every < 1 or not 1 <= args.concurrency <= 8 or not 0 <= args.max_retries <= 3:
        raise SystemExit("Invalid bounds: limit >= 0, candidates/checkpoint >= 1, concurrency 1-8, retries 0-3")
    if args.mode == "pilot" and args.limit == 0:
        raise SystemExit("Pilot mode requires a non-zero --limit")

    canonical_payload = load_json(CANONICAL_PATH)
    inventory_payload = load_json(INVENTORY_PATH)
    registry_payload = load_json(REGISTRY_PATH) if REGISTRY_PATH.exists() else {"records": []}
    seeds = build_statewide_seeds(canonical_payload)
    total_canonical_facilities = len(seeds)
    requested_ids = {str(item).strip() for item in args.canonical_id if str(item).strip()}
    if requested_ids:
        seeds = [seed for seed in seeds if seed.canonical_facility_id in requested_ids]
        found_ids = {seed.canonical_facility_id for seed in seeds}
        missing_ids = sorted(requested_ids - found_ids)
        if missing_ids:
            raise SystemExit(f"Unknown canonical facility IDs: {', '.join(missing_ids)}")
    inventory_index = inventory_by_cms_ccn(inventory_payload)
    existing_by_id = {
        str(row.get("canonical_facility_id") or "").strip(): row
        for row in registry_payload.get("records") or []
        if isinstance(row, dict) and str(row.get("canonical_facility_id") or "").strip()
    }
    canonical_by_id = {
        str(row.get("canonical_id") or "").strip(): row
        for row in canonical_payload.get("records") or []
        if isinstance(row, dict) and str(row.get("canonical_id") or "").strip()
    }
    pending = select_pending_seeds(
        seeds,
        existing_by_id,
        start_after=str(args.start_after or "").strip(),
        retry_unverified=bool(args.retry_unverified),
        force=bool(args.force),
    )
    prioritized_rows = prioritize_facilities(
        [canonical_by_id[seed.canonical_facility_id] for seed in pending],
        recommendation_ids=args.recommendation_id,
        launch_markets=args.launch_market,
    )
    priority_order = {str(row.get("canonical_id") or row.get("canonical_facility_id")): index for index, row in enumerate(prioritized_rows)}
    pending.sort(key=lambda seed: priority_order.get(seed.canonical_facility_id, len(priority_order)))
    selected = pending[: args.limit] if args.limit else pending

    print("CANONICAL FACILITIES:", len(seeds))
    print("INVENTORY CMS RECORDS:", len(inventory_index))
    print("EXISTING MEDIA RECORDS:", len(existing_by_id))
    print("PENDING FACILITIES:", len(pending))
    print("SELECTED THIS RUN:", len(selected))
    if not args.write_registry:
        print("MODE: DRY RUN (use --write-registry to authorize writes)")
        for seed in selected[:10]:
            print("DRY RUN:", seed.canonical_facility_id, "-", seed.facility_name)
        return 0

    processed_records: List[Dict[str, Any]] = []
    last_id = ""
    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = {
                executor.submit(
                    discover_with_retries,
                    seed,
                    inventory_index.get(seed.cms_ccn),
                    canonical_by_id[seed.canonical_facility_id],
                    max_candidates=args.max_candidates,
                    max_retries=args.max_retries,
                ): seed
                for seed in selected
            }
            for index, future in enumerate(as_completed(futures), start=1):
                seed = futures[future]
                print(f"STATEWIDE {index}/{len(selected)}: {seed.canonical_facility_id} - {seed.facility_name}", flush=True)
                record = future.result()
                processed_records.append(record)
                registry_payload = merge_registry(registry_payload, [record])
                last_id = seed.canonical_facility_id
                if index % args.checkpoint_every == 0:
                    persist_checkpoint(
                        registry_payload,
                        total_canonical=total_canonical_facilities,
                        pending_at_start=len(pending),
                        processed_this_run=index,
                        last_canonical_facility_id=last_id,
                        run_status="RUNNING",
                    )
    except KeyboardInterrupt:
        persist_checkpoint(
            registry_payload,
            total_canonical=total_canonical_facilities,
            pending_at_start=len(pending),
            processed_this_run=len(processed_records),
            last_canonical_facility_id=last_id,
            run_status="INTERRUPTED",
        )
        print("INTERRUPTED: checkpoint saved", file=sys.stderr)
        return 130

    if requested_ids:
        final_status = "TARGET_COMPLETE"
    elif len(selected) == len(pending):
        final_status = "COMPLETE"
    else:
        final_status = "BATCH_COMPLETE"
    persist_checkpoint(
        registry_payload,
        total_canonical=total_canonical_facilities,
        pending_at_start=len(pending),
        processed_this_run=len(processed_records),
        last_canonical_facility_id=last_id,
        run_status=final_status,
    )
    print("BATCH SUMMARY:", json.dumps(summarize(processed_records), sort_keys=True))
    print("STATEWIDE STATUS:", final_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())