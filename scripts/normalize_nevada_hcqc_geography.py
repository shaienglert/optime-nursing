from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

# ALiS publishes physical addresses in the result table. The legacy extractor split
# the street number from the rest of the address, so this normalizer reconstructs
# that published string and identifies the municipality only when a known Nevada
# place is an unambiguous suffix. No external geocoder is required for the gate.
# UNKNOWN remains UNKNOWN.
NEVADA_PLACES = tuple(sorted({
    "NORTH LAS VEGAS", "LAS VEGAS", "CARSON CITY", "BOULDER CITY", "BATTLE MOUNTAIN",
    "HENDERSON", "RENO", "SPARKS", "PAHRUMP", "MESQUITE", "FALLON", "GARDNERVILLE",
    "FERNLEY", "ELKO", "YERINGTON", "LOVELOCK", "MINDEN", "ELY", "CALIENTE",
    "WINNEMUCCA", "HAWTHORNE",
}, key=len, reverse=True))

CLARK_COUNTY_PLACES = {"LAS VEGAS", "NORTH LAS VEGAS", "HENDERSON", "BOULDER CITY", "MESQUITE"}
LAS_VEGAS_VALLEY_PLACES = {"LAS VEGAS", "NORTH LAS VEGAS", "HENDERSON"}


def reconstruct(row: dict[str, str]) -> str:
    return re.sub(r"\s+", " ", f'{row.get("address", "")} {row.get("city", "")}'.strip())


def split_city(full: str) -> tuple[str, str]:
    upper = full.upper().strip(" ,")
    for place in NEVADA_PLACES:
        if upper == place:
            return "UNKNOWN", place
        if upper.endswith(" " + place):
            street = full[: -(len(place) + 1)].strip(" ,")
            return street or "UNKNOWN", place
    return full or "UNKNOWN", "UNKNOWN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/nevada/raw/hcqc_alis_facilities.csv")
    ap.add_argument("--output", default="data/nevada/clean/hcqc_alis_facilities.csv")
    ap.add_argument("--report", default="reports/NEVADA_HCQC_GEOGRAPHY_NORMALIZATION.json")
    args = ap.parse_args()

    with Path(args.input).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    city_counts: Counter[str] = Counter()
    unresolved = clark = valley = 0
    for row in rows:
        raw = reconstruct(row)
        street, city = split_city(raw)
        row["raw_full_address"] = raw
        row["address"] = street
        row["city"] = city
        row["geography_parse_source"] = "Nevada HCQC/ALiS physical address suffix" if city != "UNKNOWN" else "UNKNOWN"
        row["county"] = "Clark" if city in CLARK_COUNTY_PLACES else "UNKNOWN"
        row["county_fips"] = "003" if city in CLARK_COUNTY_PLACES else "UNKNOWN"
        row["is_clark_county"] = "true" if city in CLARK_COUNTY_PLACES else ("UNKNOWN" if city == "UNKNOWN" else "false")
        row["is_las_vegas_valley"] = "true" if city in LAS_VEGAS_VALLEY_PLACES else ("UNKNOWN" if city == "UNKNOWN" else "false")
        row["census_geocoder_match"] = "NOT_REQUIRED"
        row["census_geocoder_matched_address"] = "UNKNOWN"
        row["census_geography_source"] = "NOT_USED"
        city_counts[city] += 1
        unresolved += int(city == "UNKNOWN")
        clark += int(city in CLARK_COUNTY_PLACES)
        valley += int(city in LAS_VEGAS_VALLEY_PLACES)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "records": len(rows),
        "geography_method": "official ALiS physical-address suffix; no external geocoder dependency",
        "place_parse_unresolved": unresolved,
        "clark_county_confirmed": clark,
        "las_vegas_valley_confirmed": valley,
        "las_vegas_count": city_counts["LAS VEGAS"],
        "north_las_vegas_count": city_counts["NORTH LAS VEGAS"],
        "henderson_count": city_counts["HENDERSON"],
        "by_city": dict(sorted(city_counts.items())),
        "unknown_policy": "UNKNOWN is preserved when the official address cannot be parsed safely.",
        "output": str(output),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
