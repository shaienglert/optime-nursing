from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, build_opener

from extract_nevada_hcqc_alis import SEARCH_URL, extract_detail, request


def fetch_one(index: int, url: str, retries: int = 4):
    last_error: Exception | None = None
    for attempt in range(retries):
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        try:
            request(opener, SEARCH_URL)
            raw, _ = request(opener, url)
            text = raw.decode("utf-8", errors="replace")
            if "SODPublicView" not in text and "License" not in text and "Credential" not in text:
                raise RuntimeError("ALiS detail response did not contain a recognizable detail surface")
            detail = extract_detail(raw, url)
            detail["response_bytes"] = len(raw)
            detail["response_has_credential_surface"] = "Credential" in text or "License" in text
            return index, detail, raw
        except Exception as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/nevada/raw/hcqc_alis_facilities.csv")
    ap.add_argument("--output", default="data/nevada/raw/hcqc_alis_facilities.csv")
    ap.add_argument("--report", default="reports/NEVADA_HCQC_ALIS_DETAIL_ENRICHMENT.json")
    ap.add_argument("--sample-html", default="reports/evidence/nevada_alis_agc_detail_sample.html")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    targets = [(i, row.get("detail_url", "")) for i, row in enumerate(rows) if row.get("license_type") == "AGC" and str(row.get("detail_url") or "").startswith("http")]
    failures = 0
    keyword_hits = 0
    confirmed = 0
    field_keys: set[str] = set()
    response_sizes: list[int] = []
    sample_written = False
    sample_path = Path(args.sample_html)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_one, i, url): (i, url) for i, url in targets}
        for future in as_completed(futures):
            i, url = futures[future]
            try:
                _, detail, raw = future.result()
                response_sizes.append(int(detail.get("response_bytes") or 0))
                if not sample_written:
                    sample_path.parent.mkdir(parents=True, exist_ok=True)
                    sample_path.write_bytes(raw)
                    sample_written = True
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
                rows[i]["official_detail"] = json.dumps({"error": type(exc).__name__, "message": str(exc)[:200]})
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
        "response_bytes_min": min(response_sizes) if response_sizes else 0,
        "response_bytes_max": max(response_sizes) if response_sizes else 0,
        "sample_html": str(sample_path) if sample_written else "UNKNOWN",
        "classification_policy": "Names are never used as memory-care proof; only explicit official detail evidence may confirm.",
        "output": str(output),
    }
    rp = Path(args.report); rp.parent.mkdir(parents=True, exist_ok=True); rp.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(f"AGC detail enrichment incomplete after retries: {failures} failures")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
