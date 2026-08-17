from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

DATASET_ID = "4pq5-n9py"
META_URL = f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{DATASET_ID}"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"


def get_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/csv,*/*"})
    with urlopen(req, timeout=120) as response:
        return response.read()


def find_download_url(meta: dict) -> str:
    for dist in meta.get("distribution") or []:
        candidates = [dist.get("downloadURL"), dist.get("accessURL")]
        data = dist.get("data") or {}
        if isinstance(data, dict):
            candidates.extend([data.get("downloadURL"), data.get("accessURL")])
        for value in candidates:
            if isinstance(value, str) and value.startswith("http") and ("csv" in value.lower() or "download" in value.lower()):
                return value
    raise RuntimeError("CMS dataset metadata did not expose a CSV download URL")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/nevada/raw/cms_provider_information_nv.csv")
    ap.add_argument("--report", default="reports/NEVADA_CMS_PROVIDER_EXTRACTION.json")
    args = ap.parse_args()

    meta = json.loads(get_bytes(META_URL).decode("utf-8"))
    download_url = find_download_url(meta)
    raw = get_bytes(download_url)
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "State" not in reader.fieldnames:
        raise RuntimeError(f"Unexpected CMS provider schema: {reader.fieldnames}")
    rows = [row for row in reader if str(row.get("State") or "").strip().upper() == "NV"]
    if not rows:
        raise RuntimeError("Live CMS Provider Information returned zero Nevada nursing facilities")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    processing_dates = sorted({str(row.get("Processing Date") or "").strip() for row in rows if row.get("Processing Date")})
    report = {
        "dataset_id": DATASET_ID,
        "metadata_url": META_URL,
        "download_url": download_url,
        "dataset_title": meta.get("title"),
        "modified": meta.get("modified"),
        "issued": meta.get("issued"),
        "released": meta.get("released"),
        "nevada_records": len(rows),
        "processing_dates": processing_dates,
        "output": str(output),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
