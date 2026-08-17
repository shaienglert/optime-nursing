from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, build_opener

from extract_nevada_hcqc_alis import extract_detail, request


def fetch_one(index: int, url: str):
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    raw, _ = request(opener, url)
    return index, extract_detail(raw, url)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/nevada/raw/hcqc_alis_facilities.csv")
    ap.add_argument("--output", default="data/nevada/raw/hcqc_alis_facilities.csv")
    ap.add_argument("--report", default="reports/NEVADA_HCQC_ALIS_DETAIL_ENRICHMENT.json")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    targets = [(i, row.get("detail_url", "")) for i, row in enumerate(rows) if row.get("license_type") == "AGC" and str(row.get("detail_url") or "").startswith("http")]
    failures = 0
    keyword_hits = 0
    confirmed = 0
    field_keys: set[str] = set()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_one, i, url): (i, url) for i, url in targets}
        for future in as_completed(futures):
            i, url = futures[future]
            try:
                _, detail = future.result()
                rows[i]["official_detail"] = json.dumps(detail.get("detail_fields") or {}, ensure_ascii=False, sort_keys=True)
                rows[i]["memory_care_evidence"] = json.dumps(detail.get("memory_contexts") or [], ensure_ascii=False)
                field_keys.update((detail.get("detail_fields") or {}).keys())
                if detail.get("memory_keywords"):
                    keyword_hits += 1
                    rows[i]["memory_care_classification"] = "CANDIDATE_OFFICIAL_DETAIL_KEYWORD"
                else:
                    rows[i]["memory_care_classification"] = "UNKNOWN"
                if detail.get("memory_care_official_detail_evidence"):
                    confirmed += 1
                    rows[i]["memory_care_classification"] = "CONFIRMED_OFFICIAL_DETAIL"
            except Exception as exc:
                failures += 1
                rows[i]["official_detail"] = json.dumps({"error": type(exc).__name__})
                rows[i]["memory_care_classification"] = "UNKNOWN"

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    report = {
        "agc_targets": len(targets),
        "detail_successes": len(targets) - failures,
        "detail_failures": failures,
        "memory_keyword_hits": keyword_hits,
        "memory_confirmed_official_detail": confirmed,
        "observed_detail_field_keys": sorted(field_keys),
        "classification_policy": "Names are never used as memory-care proof; only explicit official detail evidence may confirm.",
        "output": str(output),
    }
    rp = Path(args.report); rp.parent.mkdir(parents=True, exist_ok=True); rp.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(f"AGC detail enrichment incomplete: {failures} failures")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
