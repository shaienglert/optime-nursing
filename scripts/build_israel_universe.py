"""Build the Israeli canonical facility universe from the raw source files.

One record per source row: no cross-list merging (owner decision 2026-11-12).
Missing fields stay null/UNKNOWN; nothing is inferred beyond what a source states.

Usage: python scripts/build_israel_universe.py [raw_dir] [output_json]
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "israel" / "raw"
OUTPUT = REPO_ROOT / "database" / "israel_facility_universe_canonical.json"
SCHEMA_VERSION = "israel-canonical-facility-v1.0.0"
RECEIVED_DATE = "2026-11-12"

MOH_FILE = "Institutions.xlsx"
WELFARE_FILE = "israel-nursing-homes-115.csv"
PROTECTED_FILE = "protected-housing-08092025.csv"

SOURCES = {
    "moh": {
        "source_name": "רשימת מוסדות סיעוד גריאטריים (Institutions.xlsx)",
        "source_authority": "משרד הבריאות (לפי מבנה הקובץ; המפרסם לא צוין בקובץ)",
        "source_file": f"data/israel/raw/{MOH_FILE}",
    },
    "welfare": {
        "source_name": "רשימת בתי אבות (israel-nursing-homes-115.csv)",
        "source_authority": "משרד הרווחה (לפי הבעלים, 2026-11-12)",
        "source_file": f"data/israel/raw/{WELFARE_FILE}",
    },
    "protected": {
        "source_name": "רשימת בתי דיור מוגן (08092025-.csv)",
        "source_authority": "המפרסם לא צוין",
        "source_file": f"data/israel/raw/{PROTECTED_FILE}",
    },
}


def _clean(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _split(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def _website(raw: str | None) -> tuple[str | None, bool]:
    if not raw:
        return None, False
    match = re.search(r'href="([^"]+)', raw)
    if not match:
        return None, True
    url = match.group(1).strip().replace("https:///", "https://")
    url = url.split("�")[0].strip()
    malformed = (
        "�" in raw
        or raw.count("<a") > 1
        or 'target""' in raw
        or "https:///" in raw
    )
    return url or None, malformed


def _evidence(key: str, record_id: str, retrieved_at: str) -> dict:
    source = SOURCES[key]
    return {
        f"{key}:{record_id}": {
            **source,
            "source_record_id": record_id,
            "source_received_date": RECEIVED_DATE,
            "source_retrieved_at": retrieved_at,
            "scope": "FACILITY",
        }
    }


def _base(canonical_id: str, name: str, city: str | None, retrieved_at: str) -> dict:
    return {
        "canonical_id": canonical_id,
        "canonical_schema_version": SCHEMA_VERSION,
        "country": "IL",
        "state": "IL",
        "facility_name": name,
        "city": city,
        "address": None,
        "district": None,
        "phone": None,
        "website": None,
        "latitude": None,
        "longitude": None,
        "license_id": None,
        "operator_name": None,
        "ownership_type": None,
        "moh_code_agreement": "UNKNOWN",
        "departments_reported": [],
        "religion_attitude": [],
        "availability": "UNKNOWN",
        "merge_confidence": "NOT_MERGED",
        "data_quality_flags": [],
        "source_retrieved_at": retrieved_at,
    }


def build(raw_dir: Path = RAW_DIR) -> dict:
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records: list[dict] = []

    workbook = openpyxl.load_workbook(raw_dir / MOH_FILE, read_only=True)
    rows = list(workbook.active.iter_rows(values_only=True))
    header = [str(h).strip() for h in rows[0]]
    for row in rows[1:]:
        if not any(row):
            continue
        item = dict(zip(header, row))
        license_id = _clean(item["מספר רישום מוסד"])
        record = _base(f"IL-MOH-{license_id}", _clean(item["שם מוסד"]), _clean(item["ישוב"]), retrieved_at)
        agreement = _clean(item["בהסכם"])
        record.update(
            {
                "facility_type": "מוסד סיעוד גריאטרי",
                "source_facility_type": _clean(item["סוג מוסד"]),
                "canonical_setting": "IL_GERIATRIC_NURSING_INSTITUTION",
                "license_authority": "MINISTRY_OF_HEALTH",
                "license_id": license_id,
                "district": _clean(item["מחוז"]),
                "ownership_type": _clean(item["בעלות"]),
                "moh_code_agreement": {"כן": "YES", "לא": "NO"}.get(agreement or "", "UNKNOWN"),
                # The list does not say which wards (סיעודי / תשו״ן) each institution runs.
                "functional_levels_served": "UNKNOWN",
                "source_identity_ids": {"moh_license_id": license_id},
                "source_evidence": _evidence("moh", license_id, retrieved_at),
            }
        )
        records.append(record)

    with open(raw_dir / WELFARE_FILE, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            serial = int(row["מספר"])
            name = _clean(row["שם בית האבות"])
            record = _base(f"IL-WEL-{serial:03d}", name, _clean(row["יישוב"]), retrieved_at)
            record.update(
                {
                    "facility_type": "בית אבות",
                    "source_facility_type": None,
                    "canonical_setting": "IL_OLD_AGE_HOME",
                    "license_authority": "MINISTRY_OF_WELFARE",
                    # Regulatory scope of a welfare-licensed home, not a facility-verified fact.
                    "functional_levels_served": "REGULATORY_SCOPE_INDEPENDENT_AND_FRAIL",
                    "source_identity_ids": {"welfare_list_serial": str(serial)},
                    "source_evidence": _evidence("welfare", str(serial), retrieved_at),
                }
            )
            if name and len(name) == 20:
                record["data_quality_flags"].append("NAME_POSSIBLY_TRUNCATED_AT_20_CHARS")
            records.append(record)

    raw_bytes = (raw_dir / PROTECTED_FILE).read_bytes()
    text = raw_bytes.decode("windows-1255", errors="replace")
    for index, row in enumerate(csv.DictReader(text.splitlines()), start=1):
        record = _base(
            f"IL-DM-{index:03d}", _clean(row["protected_house_name"]), _clean(row["settlement"]), retrieved_at
        )
        website, malformed = _website(_clean(row["internet_site"]))
        phone = _clean(row["telephone"])
        record.update(
            {
                "facility_type": "דיור מוגן",
                "source_facility_type": None,
                "canonical_setting": "IL_PROTECTED_HOUSING",
                "license_authority": "MINISTRY_OF_WELFARE",
                "functional_levels_served": "REGULATORY_SCOPE_INDEPENDENT",
                "operator_name": _clean(row["company"]),
                "phone": phone.rstrip(":").strip() if phone else None,
                "website": website,
                "departments_reported": _split(_clean(row["treatment"])),
                "religion_attitude": _split(_clean(row["religion_attitude"])),
                "source_identity_ids": {"protected_housing_list_row": str(index)},
                "source_evidence": _evidence("protected", str(index), retrieved_at),
            }
        )
        if malformed:
            record["data_quality_flags"].append("WEBSITE_HTML_MALFORMED_IN_SOURCE")
        if not record["departments_reported"]:
            record["data_quality_flags"].append("DEPARTMENTS_NOT_REPORTED")
        records.append(record)

    return {
        "generated_at_utc": retrieved_at,
        "record_count": len(records),
        "canonical_schema_version": SCHEMA_VERSION,
        "merge_policy": "ONE_RECORD_PER_SOURCE_ROW_NO_CROSS_LIST_MERGE",
        "records": records,
    }


def main() -> None:
    raw_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW_DIR
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else OUTPUT
    payload = build(raw_dir)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {payload['record_count']} records to {output}")


if __name__ == "__main__":
    main()
