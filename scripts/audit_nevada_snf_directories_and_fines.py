from __future__ import annotations

import argparse
import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+Nevada SNF coverage audit)"
NHD_URLS = [
    "https://www.nursinghomedatabase.com/list/bestskillednursinghome/NV",
    "https://www.nursinghomedatabase.com/list/bestskillednursinghome/NV/LAS%20VEGAS",
    "https://www.nursinghomedatabase.com/list/worstskillednursinghome/NV/LAS%20VEGAS",
]
NHCOM_URLS = ["https://www.nursinghomes.com/nv/las-vegas/"]
BLOCK_MARKERS = (
    "incapsula incident id",
    "request unsuccessful",
    "access denied",
    "captcha",
    "verify you are human",
    "cf-chl-",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(str(value or "")).lower().replace("&", " and ")).strip()


def norm_addr(value: object) -> str:
    text = f" {norm(value)} "
    for source, target in {
        " street ": " st ", " road ": " rd ", " avenue ": " ave ", " boulevard ": " blvd ",
        " drive ": " dr ", " lane ": " ln ", " court ": " ct ", " circle ": " cir ",
        " highway ": " hwy ", " parkway ": " pkwy ", " north ": " n ", " south ": " s ",
        " east ": " e ", " west ": " w ",
    }.items():
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def strip_html(raw: str) -> str:
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def is_block_page(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


def fetch_text(url: str) -> dict:
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            text = strip_html(raw)
            blocked = is_block_page(text)
            return {
                "url": url,
                "status": "BLOCKED_CHALLENGE" if blocked else "REACHABLE",
                "http_status": getattr(response, "status", None),
                "final_url": response.geturl(),
                "bytes": len(raw.encode("utf-8")),
                "text": text,
            }
    except Exception as exc:
        return {"url": url, "status": "UNREACHABLE_OR_BLOCKED", "error": type(exc).__name__, "message": str(exc)[:220], "text": ""}


def snf_valley(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("is_las_vegas_valley") is True and r.get("canonical_type") == "SKILLED_NURSING"]


def directory_match(record: dict, page: str) -> bool:
    address = norm_addr(record.get("address"))
    name = norm(record.get("facility_name"))
    city = norm(record.get("city"))
    z = re.search(r"\b\d{5}\b", str(record.get("zip") or ""))
    zip_code = z.group(0) if z else ""
    if not address:
        return False
    # Strongest: normalized address. Statewide NursingHomeDatabase listing publishes full addresses.
    if address in page and (not zip_code or zip_code in page):
        return True
    # Ranked city pages may omit street addresses; require name + city in that case and mark method separately.
    return bool(name and city and name in page and city in page)


def audit_directory(name: str, urls: list[str], records: list[dict]) -> dict:
    fetches = [fetch_text(url) for url in urls]
    usable = [f for f in fetches if f.get("status") == "REACHABLE"]
    if not usable:
        return {
            "source": name,
            "status": "SOURCE_UNAVAILABLE_OR_BLOCKED",
            "denominator": len(records),
            "covered": "UNKNOWN",
            "missing": "UNKNOWN",
            "coverage_pct": "UNKNOWN",
            "matched_canonical_ids": [],
            "fetches": [{k: v for k, v in f.items() if k != "text"} for f in fetches],
            "policy": "Blocked/challenge pages are UNKNOWN, never zero coverage.",
        }
    page = norm_addr(" ".join(str(f.get("text") or "") for f in usable))
    matched = [r for r in records if directory_match(r, page)]
    return {
        "source": name,
        "status": "LIVE_FETCHED",
        "denominator": len(records),
        "covered": len(matched),
        "missing": len(records) - len(matched),
        "coverage_pct": round(100 * len(matched) / len(records), 2) if records else "UNKNOWN",
        "matched_canonical_ids": [r.get("canonical_id") for r in matched],
        "fetches": [{k: v for k, v in f.items() if k != "text"} for f in fetches],
        "policy": "Address is preferred strong identity; ranked pages may additionally match exact normalized facility name + city.",
    }


def audit_fines(records: list[dict], penalty_rows: list[dict]) -> dict:
    by_ccn: dict[str, list[dict]] = {}
    for row in penalty_rows:
        ccn = str(row.get("CMS Certification Number (CCN)") or "").strip()
        if ccn:
            by_ccn.setdefault(ccn, []).append(row)
    matched = []
    fine_rows = 0
    denial_rows = 0
    total_fines = 0.0
    facility_details = []
    for record in records:
        ccn = str(record.get("cms_ccn") or "").strip()
        rows = by_ccn.get(ccn, []) if ccn and ccn != "UNKNOWN" else []
        if not rows:
            continue
        matched.append(record)
        local_fines = [r for r in rows if str(r.get("Penalty Type") or "").strip().lower() == "fine"]
        local_denials = [r for r in rows if "denial" in str(r.get("Penalty Type") or "").strip().lower()]
        fine_rows += len(local_fines)
        denial_rows += len(local_denials)
        local_amount = 0.0
        for row in local_fines:
            try:
                local_amount += float(str(row.get("Fine Amount") or "0").replace(",", "").replace("$", ""))
            except ValueError:
                pass
        total_fines += local_amount
        facility_details.append({
            "canonical_id": record.get("canonical_id"),
            "cms_ccn": ccn,
            "facility_name": record.get("facility_name"),
            "penalty_rows": len(rows),
            "fine_rows": len(local_fines),
            "payment_denial_rows": len(local_denials),
            "fine_amount_total_last_3_years": round(local_amount, 2),
        })
    return {
        "source": "CMS Penalties",
        "status": "STRUCTURED_OFFICIAL_CMS_LAST_3_YEARS",
        "dataset_id": "g6vv-u9sr",
        "denominator": len(records),
        "covered_facilities_with_any_penalty": len(matched),
        "facilities_without_penalty_row_in_dataset": len(records) - len(matched),
        "fine_rows": fine_rows,
        "payment_denial_rows": denial_rows,
        "fine_amount_total_last_3_years": round(total_fines, 2),
        "matched_canonical_ids": [r.get("canonical_id") for r in matched],
        "facilities": facility_details,
        "policy": "Coverage means a CMS penalty record exists in the last-three-years dataset. No record does not prove zero lifetime/state penalties. Non-CMS assisted/independent living is out of scope.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", type=Path, default=Path("database/nevada_facility_universe_canonical.json"))
    ap.add_argument("--penalties", type=Path, default=Path("data/nevada/raw/cms_penalties_nv.csv"))
    ap.add_argument("--output", type=Path, default=Path("reports/NEVADA_SNF_DIRECTORIES_AND_FINES.json"))
    ap.add_argument("--markdown", type=Path, default=Path("reports/NEVADA_SNF_DIRECTORIES_AND_FINES.md"))
    args = ap.parse_args()

    universe = json.loads(args.universe.read_text(encoding="utf-8"))
    records = snf_valley(list(universe.get("records") or []))
    with args.penalties.open("r", encoding="utf-8-sig", newline="") as handle:
        penalty_rows = list(csv.DictReader(handle))

    nhd = audit_directory("NursingHomeDatabase", NHD_URLS, records)
    nhcom = audit_directory("NursingHomes.com", NHCOM_URLS, records)
    fines = audit_fines(records, penalty_rows)
    result = {
        "schema_version": "nevada-snf-directories-fines-v1.0.0",
        "generated_at": utcnow(),
        "las_vegas_valley_snf_denominator": len(records),
        "directories": [nhd, nhcom],
        "fines": fines,
        "truth_policy": [
            "CMS/ALiS remain truth sources; directories are discovery/enrichment only.",
            "Blocked source pages produce UNKNOWN, never zero.",
            "CMS penalty identity joins only by exact CCN.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Nevada SNF Directory + Fines Audit", "",
        f"Generated: `{result['generated_at']}`", "",
        f"Las Vegas Valley SNF denominator: **{len(records)}**", "",
        "| Source | Status | Covered | Denominator | Missing | Coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in result["directories"]:
        lines.append(f"| {row['source']} | {row['status']} | {row['covered']} | {row['denominator']} | {row['missing']} | {row['coverage_pct']} |")
    lines += ["", "## CMS Penalties", "", f"Facilities with any CMS penalty row (last 3 years): **{fines['covered_facilities_with_any_penalty']} / {fines['denominator']}**", f"Fine rows: **{fines['fine_rows']}**", f"Payment denial rows: **{fines['payment_denial_rows']}**", f"Fine amount total: **${fines['fine_amount_total_last_3_years']:,.2f}**", "", "No penalty row is not interpreted as zero lifetime/state penalties."]
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "las_vegas_valley_snf_denominator": len(records),
        "nursinghomedatabase": {"status": nhd["status"], "covered": nhd["covered"]},
        "nursinghomes_com": {"status": nhcom["status"], "covered": nhcom["covered"]},
        "cms_penalties": {"covered_facilities": fines["covered_facilities_with_any_penalty"], "fine_rows": fines["fine_rows"], "payment_denial_rows": fines["payment_denial_rows"], "fine_amount": fines["fine_amount_total_last_3_years"]},
    }, indent=2))
    if len(records) <= 0:
        raise SystemExit("Las Vegas Valley SNF denominator is empty")
    if nhd["status"] == "LIVE_FETCHED" and nhd["covered"] == 0:
        raise SystemExit("NursingHomeDatabase live adapter returned zero strong matches; likely parser/URL regression")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
