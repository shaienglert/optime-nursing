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
OUTPUT_DOC = REPO_ROOT / "docs" / "SOUTH_FLORIDA_MARKET_ANALYSIS.md"
OUTPUT_JSON = REPO_ROOT / "database" / "market_communities_south_florida.json"

TARGET_COUNTIES = {
    "PALM BEACH": "Palm Beach",
    "BROWARD": "Broward",
    "MIAMI DADE": "Miami-Dade",
}


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


def _normalize_county(value: Optional[str]) -> str:
    text = _norm(value).upper().replace("-", " ").replace("/", " ")
    return " ".join(text.split())


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


def _target_county(row: Dict[str, str]) -> Optional[str]:
    if _norm(row.get("State")).upper() != "FL":
        return None
    return TARGET_COUNTIES.get(_normalize_county(row.get("County/Parish")))


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

    # CMS does not explicitly publish chain tier; derive only when chain scale is available.
    chain_tier: Optional[str]
    is_national_chain: Optional[bool]
    is_regional_chain: Optional[bool]
    if not chain_id and not chain_name:
        chain_tier = "independent"
        is_national_chain = False
        is_regional_chain = False
    elif facilities_in_chain is None:
        chain_tier = None
        is_national_chain = None
        is_regional_chain = None
    elif facilities_in_chain >= 25:
        chain_tier = "national"
        is_national_chain = True
        is_regional_chain = False
    else:
        chain_tier = "regional"
        is_national_chain = False
        is_regional_chain = True

    is_independent = not chain_id and not chain_name
    county_display = _target_county(row)

    return {
        "community_id": ccn,
        "community_name": _norm(row.get("Provider Name")),
        "address": _norm(row.get("Provider Address")),
        "city": _norm(row.get("City/Town")),
        "state": _norm(row.get("State")),
        "zip_code": _norm(row.get("ZIP Code")),
        "phone": _norm(row.get("Telephone Number")),
        "county": county_display,
        "source_county_value": _norm(row.get("County/Parish")),
        "provider_type": provider_type,
        "ownership_type": ownership_type,
        "legal_business_name": _norm(row.get("Legal Business Name")),
        "operator_name": _operator_name(row),
        "chain_id": chain_id,
        "chain_name": chain_name,
        "facilities_in_chain": facilities_in_chain,
        "chain_tier": chain_tier,
        "is_national_chain": is_national_chain,
        "is_regional_chain": is_regional_chain,
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


def _county_metrics(communities: List[Dict[str, object]]) -> Dict[str, object]:
    total_communities = len(communities)

    missing_beds = sum(1 for c in communities if c.get("certified_beds") is None)
    total_beds: Optional[int]
    if missing_beds > 0:
        total_beds = None
    else:
        total_beds = sum(int(c.get("certified_beds") or 0) for c in communities)

    unknown_chain_tier = sum(1 for c in communities if c.get("chain_tier") is None)
    if unknown_chain_tier > 0:
        national_chain_count = None
        regional_chain_count = None
    else:
        national_chain_count = sum(1 for c in communities if c.get("is_national_chain") is True)
        regional_chain_count = sum(1 for c in communities if c.get("is_regional_chain") is True)

    independent_count = sum(1 for c in communities if c.get("is_independent") is True)

    op_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"communities": 0, "beds": 0})
    for c in communities:
        name = str(c.get("operator_name") or "Unknown Operator")
        op_stats[name]["communities"] += 1
        if isinstance(c.get("certified_beds"), int):
            op_stats[name]["beds"] += int(c["certified_beds"])

    top_ops = sorted(
        op_stats.items(),
        key=lambda item: (item[1]["communities"], item[1]["beds"], item[0]),
        reverse=True,
    )

    return {
        "total_communities": total_communities,
        "total_beds": total_beds,
        "national_chain_count": national_chain_count,
        "regional_chain_count": regional_chain_count,
        "independent_count": independent_count,
        "unknown_chain_tier_count": unknown_chain_tier,
        "missing_beds_count": missing_beds,
        "top_operators": [
            {
                "rank": idx,
                "operator_name": name,
                "communities": stats["communities"],
                "beds": stats["beds"],
            }
            for idx, (name, stats) in enumerate(top_ops[:10], start=1)
        ],
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


def _as_text(value: Optional[object]) -> str:
    return "null" if value is None else str(value)


def _build_market_report(
    communities: List[Dict[str, object]],
    source: Dict[str, str],
    county_metrics: Dict[str, Dict[str, object]],
) -> str:
    total_communities = len(communities)

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
    )[:30]

    generated_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    processing_dates = Counter(str(c.get("source_processing_date") or "") for c in communities)
    most_common_processing_date = processing_dates.most_common(1)[0][0] if processing_dates else ""

    lines: List[str] = []
    lines.append("# South Florida Market Intelligence (Verified Sources Only)")
    lines.append("")
    lines.append("## Scope and Source Controls")
    lines.append("- Geography: Palm Beach, Broward, and Miami-Dade counties (Florida)")
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
    lines.append("  chain_tier TEXT,")
    lines.append("  is_national_chain BOOLEAN NOT NULL,")
    lines.append("  is_regional_chain BOOLEAN NOT NULL,")
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
    lines.append("Definition notes:")
    lines.append("- `chain_tier = national` when chain identifier exists and `Number of Facilities in Chain >= 25`.")
    lines.append("- `chain_tier = regional` when chain identifier exists and `Number of Facilities in Chain < 25`.")
    lines.append("- `chain_tier = null` when chain affiliation exists but chain-size is unavailable in source.")
    lines.append("")

    lines.append("## County Metrics")
    lines.append("| County | Total Communities | Total Beds | National Chain | Regional Chain | Independent |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for county_name in ["Palm Beach", "Broward", "Miami-Dade"]:
        m = county_metrics.get(county_name)
        if not m:
            lines.append(f"| {county_name} | null | null | null | null | null |")
            continue
        lines.append(
            f"| {county_name} | {_as_text(m.get('total_communities'))} | {_as_text(m.get('total_beds'))} | "
            f"{_as_text(m.get('national_chain_count'))} | {_as_text(m.get('regional_chain_count'))} | "
            f"{_as_text(m.get('independent_count'))} |"
        )

    lines.append("")
    lines.append(f"Combined communities across target counties: {total_communities}")
    lines.append("")

    lines.append("## Top Operators Per County")
    for county_name in ["Palm Beach", "Broward", "Miami-Dade"]:
        lines.append("")
        lines.append(f"### {county_name}")
        metrics = county_metrics.get(county_name)
        top_ops = (metrics or {}).get("top_operators") or []
        if not top_ops:
            lines.append("null")
            continue
        lines.append("| Rank | Operator | Communities | Beds |")
        lines.append("|---|---|---:|---:|")
        for op in top_ops:
            lines.append(
                f"| {op['rank']} | {op['operator_name']} | {op['communities']} | {_as_text(op['beds'])} |"
            )
    lines.append("")

    lines.append("## Recommended First 30 Communities for Outreach")
    lines.append("| Rank | County | Community | City | Operator | Beds | Overall | Chain ID | Reason |")
    lines.append("|---|---|---|---|---:|---:|---|---|")
    for idx, c in enumerate(outreach_top, start=1):
        lines.append(
            "| "
            f"{idx} | {c.get('county') or ''} | {c.get('community_name') or ''} | {c.get('city') or ''} | {c.get('operator_name') or ''} | "
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

    communities = [_community_record(row) for row in _iter_rows(csv_path) if _target_county(row)]
    communities.sort(key=lambda c: (str(c.get("community_name") or ""), str(c.get("community_id") or "")))

    county_groups: Dict[str, List[Dict[str, object]]] = {name: [] for name in TARGET_COUNTIES.values()}
    for c in communities:
        county_name = str(c.get("county") or "")
        county_groups.setdefault(county_name, []).append(c)

    county_metrics: Dict[str, Dict[str, object]] = {
        county_name: _county_metrics(group)
        for county_name, group in county_groups.items()
        if group
    }

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
                "counties": ["Palm Beach", "Broward", "Miami-Dade"],
                "record_count": len(communities),
                "county_metrics": county_metrics,
                "records": communities,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    doc_content = _build_market_report(communities, source, county_metrics)
    OUTPUT_DOC.write_text(doc_content, encoding="utf-8")

    print({
        "communities": len(communities),
        "output_doc": str(OUTPUT_DOC),
        "output_json": str(OUTPUT_JSON),
        "counties": {name: len(rows) for name, rows in county_groups.items() if rows},
        "source_csv": str(csv_path),
    })


if __name__ == "__main__":
    main()
