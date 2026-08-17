from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, build_opener

from extract_nevada_hcqc_alis import SEARCH_URL, extract_detail, parse_page, request

MEMORY_TOKENS = ("alzheimer", "dementia", "memory care")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def parse_official_detail(raw: bytes, url: str) -> dict:
    """Parse only explicit fields from the Nevada ALiS View Detail surface.

    The View Detail page contains a credential table with an Endorsement column,
    a Facility Bed Information table whose counts are input values, and an
    inspection/SOD table. Generic labels such as 'Category-II (Alzheimer’s)'
    are not evidence unless their bed count is > 0 or the credential has an
    explicit Alzheimer/dementia/memory-care endorsement.
    """
    fallback = extract_detail(raw, url)
    parser = parse_page(raw)
    decoded = raw.decode("utf-8", errors="replace")

    endorsements: list[str] = []
    credential_statuses: list[str] = []
    credential_numbers: list[str] = []
    inspection_rows: list[dict[str, str]] = []

    for table in parser.tables:
        if not table:
            continue
        header = table[0]
        normalized_header = [clean(cell).lower() for cell in header]
        if normalized_header[:5] == ["credential type", "credential number", "endorsement", "status", "expiration date"]:
            for row in table[1:]:
                if len(row) < 5:
                    continue
                credential_numbers.append(clean(row[1]))
                endorsement = clean(row[2])
                if endorsement:
                    endorsements.append(endorsement)
                credential_statuses.append(clean(row[3]))
        elif normalized_header[:3] == ["inspection date-time", "inspection number", "event id"]:
            for row in table[1:]:
                if len(row) < 3:
                    continue
                inspection_rows.append({
                    "inspection_date_time": clean(row[0]),
                    "inspection_number": clean(row[1]),
                    "event_id": clean(row[2]),
                    "grade": clean(row[3]) if len(row) > 3 else "UNKNOWN",
                })

    # Bed counts are readonly input values rather than text nodes, so parse their
    # explicit HTML values. The pattern is scoped to the Alzheimer category row.
    memory_bed_count = None
    memory_row = re.search(
        r"Category-II\s*\(Alzheimer(?:&rsquo;|&#39;|['’])s\).*?txtCount\"[^>]*\bvalue=\"(\d+)\"",
        decoded,
        flags=re.I | re.S,
    )
    if memory_row:
        memory_bed_count = int(memory_row.group(1))

    total_bed_count = None
    total_match = re.search(r"Total\s+Count\s*:\s*Count\s*=\s*(\d+)", decoded, flags=re.I)
    if total_match:
        total_bed_count = int(total_match.group(1))

    explicit_memory_endorsements = [
        endorsement for endorsement in endorsements
        if any(token in endorsement.lower() for token in MEMORY_TOKENS)
    ]
    memory_confirmed = bool(explicit_memory_endorsements) or bool(memory_bed_count and memory_bed_count > 0)
    memory_evidence: list[dict[str, object]] = []
    for endorsement in explicit_memory_endorsements:
        memory_evidence.append({"field": "Endorsement", "value": endorsement, "source_url": url})
    if memory_bed_count is not None:
        memory_evidence.append({"field": "Category-II (Alzheimer's) Bed Count", "value": memory_bed_count, "source_url": url})

    fields = dict(fallback.get("detail_fields") or {})
    fields.update({
        "credential_numbers": credential_numbers,
        "endorsements": endorsements,
        "credential_statuses": credential_statuses,
        "memory_bed_count": memory_bed_count if memory_bed_count is not None else "UNKNOWN",
        "total_bed_count": total_bed_count if total_bed_count is not None else "UNKNOWN",
        "inspection_count_on_detail_surface": len(inspection_rows),
        "latest_inspection": inspection_rows[0] if inspection_rows else "UNKNOWN",
    })
    return {
        "detail_url": url,
        "detail_fields": fields,
        "memory_keywords": ["official_memory_evidence"] if memory_confirmed else [],
        "memory_contexts": memory_evidence,
        "memory_care_official_detail_evidence": memory_confirmed,
        "inspection_rows": inspection_rows,
    }


def fetch_one(index: int, url: str, retries: int = 4):
    last_error: Exception | None = None
    for attempt in range(retries):
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        try:
            request(opener, SEARCH_URL)
            raw, _ = request(opener, url)
            text = raw.decode("utf-8", errors="replace")
            if "Credential" not in text:
                raise RuntimeError("ALiS detail response did not contain the Credential surface")
            detail = parse_official_detail(raw, url)
            detail["response_bytes"] = len(raw)
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
    confirmed = 0
    with_memory_beds = 0
    inspections_exposed = 0
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
                fields = detail.get("detail_fields") or {}
                rows[i]["official_detail"] = json.dumps(fields, ensure_ascii=False, sort_keys=True)
                rows[i]["memory_care_evidence"] = json.dumps(detail.get("memory_contexts") or [], ensure_ascii=False)
                field_keys.update(fields.keys())
                rows[i]["memory_care_classification"] = "UNKNOWN"
                if detail.get("memory_care_official_detail_evidence"):
                    confirmed += 1
                    rows[i]["memory_care_classification"] = "CONFIRMED_OFFICIAL_DETAIL"
                memory_beds = fields.get("memory_bed_count")
                if isinstance(memory_beds, int) and memory_beds > 0:
                    with_memory_beds += 1
                if int(fields.get("inspection_count_on_detail_surface") or 0) > 0:
                    inspections_exposed += 1
            except Exception as exc:
                failures += 1
                rows[i]["official_detail"] = json.dumps({"error": type(exc).__name__, "message": str(exc)[:200]})
                rows[i]["memory_care_classification"] = "UNKNOWN"

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "agc_targets": len(targets),
        "detail_successes": len(targets) - failures,
        "detail_failures": failures,
        "memory_confirmed_official_detail": confirmed,
        "facilities_with_positive_alzheimer_bed_count": with_memory_beds,
        "facilities_with_inspections_on_detail_surface": inspections_exposed,
        "observed_detail_field_keys": sorted(field_keys),
        "response_bytes_min": min(response_sizes) if response_sizes else 0,
        "response_bytes_max": max(response_sizes) if response_sizes else 0,
        "sample_html": str(sample_path) if sample_written else "UNKNOWN",
        "classification_policy": "Memory Care is confirmed only by an explicit ALiS endorsement or a positive official Alzheimer bed count. Generic page labels and facility names are never proof.",
        "output": str(output),
    }
    rp = Path(args.report)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if failures:
        raise SystemExit(f"AGC detail enrichment incomplete after retries: {failures} failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
