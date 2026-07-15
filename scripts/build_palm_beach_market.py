from __future__ import annotations

import csv
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.request import urlopen


CMS_PROVIDER_DATASET_ID = "4pq5-n9py"
CMS_METADATA_URL = (
    "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/"
    f"{CMS_PROVIDER_DATASET_ID}"
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = REPO_ROOT / "backend" / "app" / "data"
OUTPUT_DOC = REPO_ROOT / "docs" / "PALM_BEACH_MARKET_ANALYSIS.md"
OUTPUT_JSON = REPO_ROOT / "database" / "market_communities_palm_beach.json"


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "Not Available", "NA", "N/A", "-"}:
        return None
    try:
        return int(round(float(text)))
    except ValueError:
        return None


def _norm(value: Optional[str]) -> str:
    return (value or "").strip()


def _download_provider_csv() -> Dict[str, str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with urlopen(CMS_METADATA_URL) as response:
        metadata = json.load(response)

    distributions = metadata.get("distribution") or []
    if not distributions:
        raise RuntimeError("No distribution found for CMS provider dataset")

    download_url = distributions[0]["downloadURL"]
    filename = Path(download_url.split("?")[0]).name or "cms_provider_info.csv"
    local_csv = CACHE_DIR / filename

    if not local_csv.exists():
        with urlopen(download_url) as response:
            local_csv.write_bytes(response.read())

    return {
        "download_url": download_url,
        "local_csv": str(local_csv),
        "title": metadata.get("title") or "CMS Nursing Home Provider Information",
        "modified": metadata.get("modified") or "",
    }


def _iter_rows(csv_path: Path) -> Iterable[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def _is_palm_beach_fl(row: Dict[str, str]) -> bool:
    return _norm(row.get("State")).upper() == "FL" and _norm(row.get("County/Parish")).upper() == "PALM BEACH"


def _operator_name(row: Dict[str, str]) -> str:
    chain_name = _norm(row.get("Chain Name"))
    legal_name = _norm(row.get("Legal Business Name"))
    provider_name = _norm(row.get("Provider Name"))
    if chain_name:
        return chain_name
    if legal_name:
        return legal_name
    return provider_name


def _is_special_focus(status: str) -> bool:
    value = _norm(status).upper()
    return value not in {"", "N", "NONE", "NOT IN PROGRAM"}


def _community_record(row: Dict[str, str]) -> Dict[str, object]:
    ccn = _norm(row.get("CMS Certification Number (CCN)"))
    chain_id = _norm(row.get("Chain ID"))
    chain_name = _norm(row.get("Chain Name"))
    facilities_in_chain = _to_int(row.get("Number of Facilities in Chain"))
    beds = _to_int(row.get("Number of Certified Beds"))
    overall_rating = _to_int(row.get("Overall Rating"))
    provider_type = _norm(row.get("Provider Type"))
    ownership_type = _norm(row.get("Ownership Type"))
    ownership_change = _norm(row.get("Provider Changed Ownership in Last 12 Months")).upper()
    special_focus_status = _norm(row.get("Special Focus Status"))

    # CMS does not explicitly publish a "national chain" boolean; we use chain-scale threshold.
    is_national_chain = bool(chain_id and (facilities_in_chain or 0) >= 25)
    is_independent = not chain_id and not chain_name

    return {
        "community_id": ccn,
        "community_name": _norm(row.get("Provider Name")),
        "address": _norm(row.get("Provider Address")),
        "city": _norm(row.get("City/Town")),
        "state": _norm(row.get("State")),
        "zip_code": _norm(row.get("ZIP Code")),
        "phone": _norm(row.get("Telephone Number")),
        "county": _norm(row.get("County/Parish")),
        "provider_type": provider_type,
        "ownership_type": ownership_type,
        "legal_business_name": _norm(row.get("Legal Business Name")),
        "operator_name": _operator_name(row),
        "chain_id": chain_id,
        "chain_name": chain_name,
        "facilities_in_chain": facilities_in_chain,
        "is_national_chain": is_national_chain,
        "is_independent": is_independent,
        "certified_beds": beds,
        "overall_rating": overall_rating,
        "staffing_rating": _to_int(row.get("Staffing Rating")),
        "quality_rating": _to_int(row.get("QM Rating")),
        "inspection_rating": _to_int(row.get("Health Inspection Rating")),
        "special_focus_status": special_focus_status,
        "changed_ownership_last_12m": ownership_change == "Y",
        "source_processing_date": _norm(row.get("Processing Date")),
    }


def _outreach_score(community: Dict[str, object]) -> int:
    score = 0
    beds = community.get("certified_beds") or 0
    overall_rating = community.get("overall_rating")
    staffing_rating = community.get("staffing_rating")
    facilities_in_chain = community.get("facilities_in_chain") or 0
    changed_ownership = bool(community.get("changed_ownership_last_12m"))
    special_focus = _is_special_focus(str(community.get("special_focus_status") or ""))

    if isinstance(beds, int):
        score += min(6, beds // 30)
    if isinstance(overall_rating, int):
        score += overall_rating
    if isinstance(staffing_rating, int):
        score += max(0, staffing_rating - 2)
    if isinstance(facilities_in_chain, int):
        score += min(4, facilities_in_chain // 25)
    if changed_ownership:
        score += 1
    if special_focus:
        score -= 3

    return score


def _outreach_reason(community: Dict[str, object]) -> str:
    reasons: List[str] = []

    beds = community.get("certified_beds")
    if isinstance(beds, int) and beds >= 120:
        reasons.append(f"large capacity ({beds} beds)")

    overall = community.get("overall_rating")
    if isinstance(overall, int) and overall >= 4:
        reasons.append(f"strong overall rating ({overall}/5)")

    facilities_in_chain = community.get("facilities_in_chain")
    chain_name = community.get("chain_name")
    if chain_name and isinstance(facilities_in_chain, int) and facilities_in_chain >= 25:
        reasons.append(f"large chain footprint ({facilities_in_chain} facilities)")
    elif chain_name:
        reasons.append("chain-affiliated operator")

    if community.get("changed_ownership_last_12m"):
        reasons.append("ownership changed in last 12 months")

    if _is_special_focus(str(community.get("special_focus_status") or "")):
        reasons.append("special focus flag present")

    if not reasons:
        reasons.append("county coverage candidate")

    return "; ".join(reasons)


def _build_market_report(communities: List[Dict[str, object]], source: Dict[str, str]) -> str:
    total_communities = len(communities)
    national_chain_count = sum(1 for c in communities if c.get("is_national_chain"))
    independent_count = sum(1 for c in communities if c.get("is_independent"))

    total_beds = sum((c.get("certified_beds") or 0) for c in communities)

    op_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"facilities": 0, "beds": 0})
    for c in communities:
        name = str(c.get("operator_name") or "Unknown Operator")
        op_stats[name]["facilities"] += 1
        op_stats[name]["beds"] += int(c.get("certified_beds") or 0)

    top_ops = sorted(
        op_stats.items(),
        key=lambda item: (item[1]["facilities"], item[1]["beds"], item[0]),
        reverse=True,
    )[:10]

    scored = []
    for c in communities:
        item = dict(c)
        item["outreach_score"] = _outreach_score(c)
        item["outreach_reason"] = _outreach_reason(c)
        scored.append(item)

    outreach_top = sorted(
        scored,
        key=lambda c: (c["outreach_score"], c.get("certified_beds") or 0, c.get("community_name") or ""),
        reverse=True,
    )[:20]

    generated_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    processing_dates = Counter(str(c.get("source_processing_date") or "") for c in communities)
    most_common_processing_date = processing_dates.most_common(1)[0][0] if processing_dates else ""

    lines: List[str] = []
    lines.append("# Palm Beach County Market Intelligence (Verified Sources Only)")
    lines.append("")
    lines.append("## Scope and Source Controls")
    lines.append("- Geography: Palm Beach County, Florida")
    lines.append("- Facility class: CMS Nursing Home Provider Information records (skilled nursing facilities)")
    lines.append("- Estimates: none used; all values are direct source fields or deterministic calculations")
    lines.append(f"- Source dataset: {source['title']} ({CMS_PROVIDER_DATASET_ID})")
    lines.append(f"- Source metadata endpoint: {CMS_METADATA_URL}")
    lines.append(f"- Source CSV endpoint: {source['download_url']}")
    lines.append(f"- Report generated (UTC): {generated_utc}")
    if source.get("modified"):
        lines.append(f"- CMS metadata modified timestamp: {source['modified']}")
    if most_common_processing_date:
        lines.append(f"- Most common provider Processing Date in county rows: {most_common_processing_date}")
    lines.append("")

    lines.append("## market_communities Table Spec")
    lines.append("```sql")
    lines.append("CREATE TABLE market_communities (")
    lines.append("  community_id TEXT PRIMARY KEY,")
    lines.append("  community_name TEXT NOT NULL,")
    lines.append("  address TEXT NOT NULL,")
    lines.append("  city TEXT NOT NULL,")
    lines.append("  state TEXT NOT NULL,")
    lines.append("  zip_code TEXT NOT NULL,")
    lines.append("  phone TEXT,")
    lines.append("  county TEXT NOT NULL,")
    lines.append("  provider_type TEXT,")
    lines.append("  ownership_type TEXT,")
    lines.append("  legal_business_name TEXT,")
    lines.append("  operator_name TEXT NOT NULL,")
    lines.append("  chain_id TEXT,")
    lines.append("  chain_name TEXT,")
    lines.append("  facilities_in_chain INTEGER,")
    lines.append("  is_national_chain BOOLEAN NOT NULL,")
    lines.append("  is_independent BOOLEAN NOT NULL,")
    lines.append("  certified_beds INTEGER,")
    lines.append("  overall_rating INTEGER,")
    lines.append("  staffing_rating INTEGER,")
    lines.append("  quality_rating INTEGER,")
    lines.append("  inspection_rating INTEGER,")
    lines.append("  special_focus_status TEXT,")
    lines.append("  changed_ownership_last_12m BOOLEAN NOT NULL,")
    lines.append("  source_processing_date TEXT,")
    lines.append("  source_dataset_id TEXT NOT NULL,")
    lines.append("  source_download_url TEXT NOT NULL,")
    lines.append("  generated_at_utc TEXT NOT NULL")
    lines.append(");")
    lines.append("```")
    lines.append("")
    lines.append("Definition note: `is_national_chain` is true when CMS `Chain ID` is present and `Number of Facilities in Chain >= 25`.")
    lines.append("")

    lines.append("## Market Metrics")
    lines.append(f"- Total communities: {total_communities}")
    lines.append(f"- National chain communities: {national_chain_count}")
    lines.append(f"- Independent communities: {independent_count}")
    lines.append(f"- Total certified beds: {total_beds}")
    lines.append("")

    lines.append("## Top 10 Operators by Market Share")
    lines.append("| Rank | Operator | Communities | Facility Share | Beds | Bed Share |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for idx, (name, stats) in enumerate(top_ops, start=1):
        facilities = stats["facilities"]
        beds = stats["beds"]
        facility_share = (facilities / total_communities * 100.0) if total_communities else 0.0
        bed_share = (beds / total_beds * 100.0) if total_beds else 0.0
        lines.append(
            f"| {idx} | {name} | {facilities} | {facility_share:.1f}% | {beds} | {bed_share:.1f}% |"
        )
    lines.append("")

    lines.append("## Recommended First 20 Communities for Outreach")
    lines.append("| Rank | Community | City | Operator | Beds | Overall | Chain ID | Reason |")
    lines.append("|---|---|---|---|---:|---:|---|---|")
    for idx, c in enumerate(outreach_top, start=1):
        lines.append(
            "| "
            f"{idx} | {c.get('community_name') or ''} | {c.get('city') or ''} | {c.get('operator_name') or ''} | "
            f"{c.get('certified_beds') or 0} | {c.get('overall_rating') or ''} | {c.get('chain_id') or ''} | "
            f"{c.get('outreach_reason') or ''} |"
        )
    lines.append("")

    lines.append("## Reproducibility")
    lines.append("Run the command below from the repository root to regenerate this report:")
    lines.append("```bash")
    lines.append("python scripts/build_palm_beach_market.py")
    lines.append("```")

    return "\n".join(lines) + "\n"


def main() -> None:
    source = _download_provider_csv()
    csv_path = Path(source["local_csv"])

    communities = [_community_record(row) for row in _iter_rows(csv_path) if _is_palm_beach_fl(row)]
    communities.sort(key=lambda c: (str(c.get("community_name") or ""), str(c.get("community_id") or "")))

    generated_at_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "dataset_id": CMS_PROVIDER_DATASET_ID,
                "metadata_endpoint": CMS_METADATA_URL,
                "source_download_url": source["download_url"],
                "source_metadata_modified": source.get("modified") or "",
                "generated_at_utc": generated_at_utc,
                "record_count": len(communities),
                "records": communities,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    doc_content = _build_market_report(communities, source)
    OUTPUT_DOC.write_text(doc_content, encoding="utf-8")

    print({
        "communities": len(communities),
        "output_doc": str(OUTPUT_DOC),
        "output_json": str(OUTPUT_JSON),
        "source_csv": str(csv_path),
    })


if __name__ == "__main__":
    main()
