#!/usr/bin/env python3
"""Validate the minimum governed fields of an Oomnik supplier record."""

from __future__ import annotations

import json
import sys
from pathlib import Path


VALID_INVOLVEMENT = {"DIRECT_LINK", "DIRECTORY", "PROFESSIONAL_REFERRAL", "OUTCOME_CRITICAL"}
VALID_PUBLICATION = {"CANDIDATE", "LIMITED", "VERIFIED", "SUSPENDED", "CLOSED"}


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    for key in ("supplier_id", "brand_name", "sector_ids", "branch", "ratings", "involvement", "evidence_refs", "unknown_fields", "freshness", "publication"):
        if key not in record:
            errors.append(f"missing required field: {key}")

    if not record.get("sector_ids"):
        errors.append("sector_ids must not be empty")
    if record.get("involvement") not in VALID_INVOLVEMENT:
        errors.append("invalid involvement")

    branch = record.get("branch") or {}
    if branch.get("las_vegas_valley_verified") is not True:
        errors.append("Las Vegas Valley service must be verified")

    for index, rating in enumerate(record.get("ratings") or []):
        for key in ("source", "branch_identity", "rating", "review_count", "observed_at", "source_url"):
            if rating.get(key) is None:
                errors.append(f"ratings[{index}] missing {key}")

    publication = record.get("publication") or {}
    if publication.get("status") not in VALID_PUBLICATION:
        errors.append("invalid publication status")

    if publication.get("status") == "VERIFIED":
        if not record.get("evidence_refs"):
            errors.append("VERIFIED supplier requires evidence_refs")
        if not branch.get("website") and not branch.get("phone"):
            errors.append("VERIFIED supplier requires an active contact channel")
        if not record.get("ratings"):
            errors.append("VERIFIED supplier requires at least one source-specific rating observation")

    if record.get("involvement") == "OUTCOME_CRITICAL" and not record.get("critical_readiness"):
        errors.append("OUTCOME_CRITICAL supplier requires critical_readiness")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_supplier_record.py RECORD.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    record = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(record)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("supplier record valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

