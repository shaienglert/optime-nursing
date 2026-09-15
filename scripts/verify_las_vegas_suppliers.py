from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.database import Base, engine  # noqa: E402
import app.models.supplier_intelligence  # noqa: E402,F401
from app.services.supplier_verification_agent import (  # noqa: E402
    last_checked_by_supplier,
    persist_verification_results,
    select_verification_batch,
    verify_supplier_record,
)


DATA_PATH = BACKEND / "app" / "data" / "las_vegas_supplier_candidates.json"
REPORT_PATH = ROOT / "reports" / "LAS_VEGAS_SUPPLIER_VERIFICATION.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Las Vegas supplier evidence without promoting unknown claims.")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("OOMNIK_SUPPLIER_VERIFY_BATCH_SIZE", "40")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("OOMNIK_SUPPLIER_VERIFY_TIMEOUT", "12")))
    parser.add_argument("--supplier-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--persist-database", action="store_true")
    args = parser.parse_args()

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    records = payload.get("records") or []
    if args.persist_database and not args.dry_run:
        Base.metadata.create_all(bind=engine)
        previous_checks = last_checked_by_supplier()
    else:
        previous_checks = {}

    if args.supplier_id:
        batch = [record for record in records if record.get("supplier_id") == args.supplier_id]
        if not batch:
            raise SystemExit(f"Unknown supplier_id: {args.supplier_id}")
    else:
        batch = select_verification_batch(records, args.batch_size, last_checked_by_supplier=previous_checks)

    results = []
    persistence_payload = []
    for index, record in enumerate(batch, start=1):
        verification = verify_supplier_record(record, timeout=args.timeout)
        record["verification"] = verification
        persistence_payload.append({"supplier_id": record.get("supplier_id"), "brand_name": record.get("brand_name"), "verification": verification})
        results.append({
            "supplier_id": record.get("supplier_id"),
            "brand_name": record.get("brand_name"),
            "stage": verification["stage"],
            "sources_attempted": verification["sources_attempted"],
            "sources_reachable": verification["sources_reachable"],
            "identity_market_matches": verification["identity_market_matches"],
        })
        print(f"[{index}/{len(batch)}] {record.get('supplier_id')}: {verification['stage']}", flush=True)

    persistence = None
    if args.persist_database and not args.dry_run:
        persistence = persist_verification_results(persistence_payload)

    report = {
        "agent": "oomnik-supplier-verification-agent",
        "market": payload.get("market"),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "records_considered": len(records),
        "records_processed": len(batch),
        "stage_counts": dict(Counter(item["stage"] for item in results)),
        "source_requests": sum(item["sources_attempted"] for item in results),
        "reachable_sources": sum(item["sources_reachable"] for item in results),
        "results": results,
        "persistence": persistence,
        "safety": {
            "publication_auto_promotions": 0,
            "ratings_auto_created": 0,
            "case_readiness_auto_confirmations": 0,
        },
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not args.dry_run and not args.persist_database:
        DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
