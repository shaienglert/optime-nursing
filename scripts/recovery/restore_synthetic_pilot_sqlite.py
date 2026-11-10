#!/usr/bin/env python3
"""Restore an isolated SQLite snapshot from committed fictional Oomnik pilot fixtures.

Never connects to Render, Neon, a production DB, or external services.
Preserves the checked-in snapshots instead of regenerating potentially changed data.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "database" / "synthetic_pilot"
NAMES = ("facility_universe", "facility_parameter_evidence", "room_inventory",
         "facility_media_registry", "provider_capabilities")


def read_snapshot(name: str) -> tuple[dict, str]:
    path = FIXTURES / f"{name}.json.gz.b64"
    decoded = gzip.decompress(base64.b64decode(path.read_text(encoding="ascii").strip()))
    obj = json.loads(decoded)
    assert obj["dataset_mode"] == "SYNTHETIC_PILOT", f"{name} not synthetic"
    assert obj["record_count"] == len(obj["records"]), f"{name} record count mismatch"
    return obj, hashlib.sha256(decoded).hexdigest()


def recover(destination: Path) -> dict:
    datasets = {name: read_snapshot(name) for name in NAMES}
    fac = datasets["facility_universe"][0]["records"]
    evidence = datasets["facility_parameter_evidence"][0]["records"]
    rooms = datasets["room_inventory"][0]["records"]
    profiles = datasets["facility_media_registry"][0]["records"]
    capabilities = datasets["provider_capabilities"][0]["records"]
    ids = [row["canonical_id"] for row in fac]
    assert len(ids) == len(set(ids)) == 500, "must contain 500 unique facilities"
    assert all(row.get("synthetic_pilot") is True for row in fac)
    assert len(rooms) == 1000 and len(capabilities) == 16500
    idset = set(ids)
    for rows in (evidence, rooms, profiles, capabilities):
        assert all(row["canonical_facility_id"] in idset for row in rows)
    assert all(isinstance(r.get("monthly_price_cents"), int)
               and r["monthly_price_cents"] > 0 for r in rooms)

    # The committed media registry has one gallery per facility, while the
    # builder's SQLite schema stores one row per image.
    media = []
    for profile in profiles:
        for photo in profile["gallery_images"]:
            media.append({"canonical_facility_id": profile["canonical_facility_id"],
                          **photo})
    assert len(media) == 2500

    spec = importlib.util.spec_from_file_location("synthetic_builder", ROOT / "scripts" /
                                                   "build_synthetic_pilot_facilities.py")
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not destination.exists(), "refusing to overwrite an existing database"
    builder.DB_PATH = destination
    builder.write_sqlite(fac, evidence, rooms, media, capabilities)

    conn = sqlite3.connect(f"file:{destination}?mode=ro", uri=True)
    try:
        actual = {name: conn.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                  for name in ("pilot_facilities", "pilot_parameter_evidence",
                               "pilot_rooms", "pilot_media", "pilot_capabilities")}
        expected = {"pilot_facilities": 500, "pilot_parameter_evidence": len(evidence),
                    "pilot_rooms": 1000, "pilot_media": 2500,
                    "pilot_capabilities": 16500}
        assert actual == expected, (actual, expected)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT count(DISTINCT canonical_facility_id) FROM pilot_rooms").fetchone()[0] == 500
        assert conn.execute("SELECT count(*) FROM pilot_rooms WHERE monthly_price_cents <= 0").fetchone()[0] == 0
    finally:
        conn.close()
    return {"status": "RESTORED_ISOLATED_SQLITE", "source": "GITHUB_SYNTHETIC_FIXTURES_ONLY",
            "synthetic_not_real_world_data": True, "counts": actual,
            "sha256_sources": {name: sha for name, (_, sha) in datasets.items()},
            "sqlite_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = recover(args.out)
    manifest = args.out.with_suffix(".manifest.json")
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
