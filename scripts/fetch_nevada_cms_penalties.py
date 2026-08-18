from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

DATASET_ID = "g6vv-u9sr"
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
    raise RuntimeError("CMS penalties metadata did not expose a CSV download URL")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/nevada/raw/cms_penalties_nv.csv")
    ap.add_argument("--report", default="reports/NEVADA_CMS_PENALTIES_EXTRACTION.json")
    args = ap.parse_args()

    meta = json.loads(get_bytes(META_URL).decode("utf-8"))
    download_url = find_download_url(meta)
    raw = get_bytes(download_url)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    required = {"CMS Certification Number (CCN)", "State", "Penalty Type", "Penalty Date"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise RuntimeError(f"Unexpected CMS penalties schema: {reader.fieldnames}")
    rows = [row for row in reader if str(row.get("State") or "").strip().upper() == "NV"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    fine_rows = [r for r in rows if str(r.get("Penalty Type") or "").strip().lower() == "fine"]
    denial_rows = [r for r in rows if "denial" in str(r.get("Penalty Type") or "").strip().lower()]
    ccns = {str(r.get("CMS Certification Number (CCN)") or "").strip() for r in rows if r.get("CMS Certification Number (CCN)")}
    fine_ccns = {str(r.get("CMS Certification Number (CCN)") or "").strip() for r in fine_rows if r.get("CMS Certification Number (CCN)")}
    total_fine_amount = 0.0
    for row in fine_rows:
        try:
            total_fine_amount += float(str(row.get("Fine Amount") or "0").replace(",", "").replace("$", ""))
        except ValueError:
            pass

    report = {
        "dataset_id": DATASET_ID,
        "metadata_url": META_URL,
        "download_url": download_url,
        "dataset_title": meta.get("title"),
        "modified": meta.get("modified"),
        "issued": meta.get("issued"),
        "released": meta.get("released"),
        "nevada_penalty_rows": len(rows),
        "nevada_ccns_with_any_penalty": len(ccns),
        "nevada_fine_rows": len(fine_rows),
        "nevada_ccns_with_fines": len(fine_ccns),
        "nevada_payment_denial_rows": len(denial_rows),
        "nevada_total_fine_amount": round(total_fine_amount, 2),
        "output": str(output),
        "semantics": "CMS Penalties lists fines and payment denials received by Medicare/Medicaid-certified nursing homes in the last three years. Absence is not evidence of zero lifetime penalties and does not apply to non-CMS assisted living/independent living facilities.",
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
