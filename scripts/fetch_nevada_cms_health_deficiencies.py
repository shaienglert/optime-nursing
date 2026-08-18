from __future__ import annotations

import argparse, csv, io, json
from pathlib import Path
from urllib.request import Request, urlopen

DATASET_ID = "r5ix-sfxw"
META_URL = f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{DATASET_ID}"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+Nevada penalty citation research)"


def get_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json,text/csv,*/*"})
    with urlopen(req, timeout=180) as response:
        return response.read()


def find_download_url(meta: dict) -> str:
    for dist in meta.get("distribution") or []:
        for value in (dist.get("downloadURL"), dist.get("accessURL"), (dist.get("data") or {}).get("downloadURL") if isinstance(dist.get("data"), dict) else None):
            if isinstance(value, str) and value.startswith("http") and ("csv" in value.lower() or "download" in value.lower()):
                return value
    raise RuntimeError("CMS health deficiencies metadata did not expose a CSV download URL")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/nevada/raw/cms_health_deficiencies_nv.csv")
    ap.add_argument("--report", default="reports/NEVADA_CMS_HEALTH_DEFICIENCIES_EXTRACTION.json")
    args = ap.parse_args()
    meta = json.loads(get_bytes(META_URL).decode("utf-8"))
    download_url = find_download_url(meta)
    reader = csv.DictReader(io.StringIO(get_bytes(download_url).decode("utf-8-sig", errors="replace")))
    required = {"CMS Certification Number (CCN)", "State", "Survey Date", "Deficiency Prefix", "Deficiency Tag Number", "Deficiency Description", "Scope Severity Code"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise RuntimeError(f"Unexpected CMS health deficiencies schema: {reader.fieldnames}")
    rows = [r for r in reader if str(r.get("State") or "").strip().upper() == "NV"]
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=reader.fieldnames); w.writeheader(); w.writerows(rows)
    report = {
        "dataset_id": DATASET_ID,
        "dataset_title": meta.get("title"),
        "download_url": download_url,
        "nevada_citation_rows": len(rows),
        "nevada_ccns_with_citations": len({str(r.get('CMS Certification Number (CCN)') or '').strip() for r in rows if r.get('CMS Certification Number (CCN)')}),
        "output": str(out),
        "semantics": "One CMS health citation per row for the last three years. This dataset describes inspection findings but does not directly identify which citation caused a particular penalty."
    }
    rp = Path(args.report); rp.parent.mkdir(parents=True, exist_ok=True); rp.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
