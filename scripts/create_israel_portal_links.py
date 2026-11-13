"""Create personal portal links for Israeli facilities (for outreach).

Usage:
    OPTIME_ADMIN_TOKEN=... python scripts/create_israel_portal_links.py \
        --api https://<israeli-backend>.onrender.com --site https://<site> \
        --out ~/oomnik-il-links.csv [--ids IL-MOH-237U6 IL-DM-045]

The output CSV holds working links: each one lets its holder edit that facility's
details. Keep it out of the repository and share each row only with its facility.
Creating a link replaces (revokes) that facility's previous link.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE = ROOT / "database" / "israel_facility_universe_canonical.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--ids", nargs="*", help="canonical ids; default: every facility")
    args = parser.parse_args()

    token = os.getenv("OPTIME_ADMIN_TOKEN", "").strip()
    if not token:
        print("OPTIME_ADMIN_TOKEN is not set.", file=sys.stderr)
        return 2
    out = Path(args.out).expanduser()
    if ROOT in out.resolve().parents:
        print("Refusing to write working links inside the repository.", file=sys.stderr)
        return 2

    records = json.loads(UNIVERSE.read_text(encoding="utf-8"))["records"]
    wanted = set(args.ids or [])
    rows = [r for r in records if not wanted or r["canonical_id"] in wanted]

    api = args.api.rstrip("/")
    site = args.site.rstrip("/")
    failures = 0
    with out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["canonical_id", "name", "city", "phone", "link", "expires_at"])
        for record in rows:
            response = requests.post(
                f"{api}/admin/portal/invites",
                json={"canonical_id": record["canonical_id"]},
                headers={"x-admin-token": token},
                timeout=30,
            )
            if response.status_code != 200:
                failures += 1
                print(f"{record['canonical_id']}: {response.status_code} {response.text[:120]}", file=sys.stderr)
                continue
            invite = response.json()
            writer.writerow([
                record["canonical_id"],
                record.get("facility_name"),
                record.get("city"),
                record.get("phone"),
                f"{site}{invite['link_path']}",
                invite["expires_at"],
            ])
    print(f"Wrote {len(rows) - failures} links to {out} ({failures} failed).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
