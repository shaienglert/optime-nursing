from __future__ import annotations

import datetime as dt
import html as html_lib
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DOC = REPO_ROOT / "docs" / "SOUTH_FLORIDA_SENIOR_LIVING_MARKET.md"
OUTPUT_JSON = REPO_ROOT / "database" / "south_florida_senior_living_inventory.json"

COUNTIES = {
    "Palm Beach": "palm-beach-county",
    "Broward": "broward-county",
    "Miami-Dade": "miami-dade-county",
}

CARE_TYPES = {
    "Assisted Living": "assisted-living",
    "Independent Living": "independent-living",
    "Memory Care": "memory-care",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def parse_jsonld_objects(html: str) -> List[object]:
    objects: List[object] = []
    for script in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        script = script.strip()
        try:
            objects.append(json.loads(script))
        except Exception:
            continue
    return objects


def extract_listing_items(html: str) -> List[Dict[str, object]]:
    for obj in parse_jsonld_objects(html):
        if isinstance(obj, dict) and isinstance(obj.get("itemListElement"), list):
            return [item for item in obj["itemListElement"] if isinstance(item, dict)]
    return []


def list_county_urls(care_slug: str, county_slug: str) -> List[str]:
    base_url = f"https://www.seniorly.com/{care_slug}/florida/{county_slug}"
    discovered: List[str] = []
    seen: Set[str] = set()

    for page_number in range(1, 21):
        url = base_url if page_number == 1 else f"{base_url}?page-number={page_number}"
        html = fetch_html(url)
        items = extract_listing_items(html)
        if not items:
            break

        page_new = 0
        for item in items:
            listing_url = item.get("url")
            if not isinstance(listing_url, str) or not listing_url:
                continue
            if listing_url not in seen:
                seen.add(listing_url)
                discovered.append(listing_url)
                page_new += 1

        if page_new == 0:
            break

    return discovered


def extract_management_company(html: str) -> Optional[str]:
    patterns = [
        r"Managed by ([^<\.]+)",
        r"managed by ([^<\.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            text = html_lib.unescape(match.group(1)).strip()
            text = re.split(r"(?:,|\.| exemplifies| provides| offers| is )", text, maxsplit=1)[0].strip()
            if text:
                return text
    return None


def extract_external_website(html: str) -> Optional[str]:
    excluded = (
        "seniorly.com",
        "quality.healthfinder.fl.gov",
        "carescout.com",
        "census.gov",
        "epa.gov",
        "instagram.com",
        "linkedin.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "youtube.com",
        "google.com",
    )
    hrefs = re.findall(r'href="([^"]+)"', html)
    for href in hrefs:
        if not href.startswith("http"):
            continue
        if any(domain in href for domain in excluded):
            continue
        return href
    return None


def extract_license_number(html: str) -> Optional[str]:
    match = re.search(r"https://quality\.healthfinder\.fl\.gov/Facility-Provider/Profile/\?LID=(\d+)", html)
    if match:
        return match.group(1)
    return None


def extract_capacity_text(html: str) -> Optional[str]:
    phrase = "Total number of residents this assisted living facility can support"
    idx = html.find(phrase)
    if idx != -1:
        segment = html[idx : idx + 1000]
        match = re.search(r"<!--t=[^>]+-->([^<]+)<!---->", segment)
        if match:
            return html_lib.unescape(match.group(1)).strip() or None

    fallback_patterns = [
        r'"([^"\n]{1,40}(?:resident capacity|Beds))"',
        r"up to \d+ Beds",
        r"\d+ \+ resident capacity",
        r"\d+ resident capacity",
    ]
    for pattern in fallback_patterns:
        match = re.search(pattern, html, re.I)
        if match:
            return html_lib.unescape(match.group(0)).strip()
    return None


def extract_detail(url: str) -> Dict[str, object]:
    html = fetch_html(url)
    local_business = None
    for obj in parse_jsonld_objects(html):
        if isinstance(obj, dict) and obj.get("@type") == "LocalBusiness":
            local_business = obj
            break

    address = None
    if isinstance(local_business, dict):
        address_obj = local_business.get("address")
        if isinstance(address_obj, dict):
            parts = [
                address_obj.get("streetAddress"),
                address_obj.get("addressLocality"),
                address_obj.get("addressRegion"),
                address_obj.get("postalCode"),
            ]
            parts = [str(part).strip() for part in parts if part]
            address = ", ".join(parts) if parts else None

    community_name = None
    telephone = None
    if isinstance(local_business, dict):
        community_name = local_business.get("name")
        telephone = local_business.get("telephone")

    care_type = None
    match = re.search(r"https://www\.seniorly\.com/([^/]+)/florida/", url)
    if match:
        care_type = match.group(1).replace("-", " ").title()

    county = None
    for county_name, county_slug in COUNTIES.items():
        if f"/florida/{county_slug}/" in url:
            county = county_name
            break

    return {
        "community_name": community_name,
        "community_type": care_type,
        "parent_company": extract_management_company(html),
        "address": address,
        "phone": telephone,
        "website": extract_external_website(html),
        "units_beds": extract_capacity_text(html),
        "ownership_type": None,
        "state_license_number": extract_license_number(html),
        "license_profile_url": re.search(
            r"https://quality\.healthfinder\.fl\.gov/Facility-Provider/Profile/\?LID=\d+", html
        ).group(0)
        if re.search(r"https://quality\.healthfinder\.fl\.gov/Facility-Provider/Profile/\?LID=\d+", html)
        else None,
        "detail_url": url,
        "county": county,
    }


def build_inventory() -> List[Dict[str, object]]:
    records_by_url: Dict[str, Dict[str, object]] = {}
    source_map: Dict[str, Set[str]] = defaultdict(set)

    for county_name, county_slug in COUNTIES.items():
        for care_name, care_slug in CARE_TYPES.items():
            urls = list_county_urls(care_slug, county_slug)
            for listing_url in urls:
                record = records_by_url.setdefault(
                    listing_url,
                    {
                        "community_name": None,
                        "community_types": set(),
                        "parent_company": None,
                        "address": None,
                        "phone": None,
                        "website": None,
                        "units_beds": None,
                        "ownership_type": None,
                        "state_license_number": None,
                        "license_profile_url": None,
                        "county": county_name,
                        "detail_url": listing_url,
                    },
                )
                record["community_types"].add(care_name)
                source_map[listing_url].add(f"{county_name}:{care_name}")

    detail_urls = list(records_by_url.keys())
    max_workers = min(12, max(4, len(detail_urls)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_detail, url): url for url in detail_urls}
        for future in as_completed(futures):
            url = futures[future]
            detail = future.result()
            record = records_by_url[url]
            for key, value in detail.items():
                if key == "community_type":
                    record["community_types"].add(value) if value else None
                elif value is not None and record.get(key) in {None, ""}:
                    record[key] = value
                elif value is not None and key in {"parent_company", "website", "units_beds", "state_license_number", "license_profile_url"}:
                    record[key] = value
            if detail.get("county"):
                record["county"] = detail["county"]

    records: List[Dict[str, object]] = []
    for url, record in records_by_url.items():
        community_types = sorted(t for t in record["community_types"] if t)
        parent_company = record.get("parent_company") or None
        records.append(
            {
                "community_name": record.get("community_name"),
                "community_types": community_types,
                "primary_community_type": community_types[0] if community_types else None,
                "parent_company": parent_company,
                "address": record.get("address"),
                "phone": record.get("phone"),
                "website": record.get("website"),
                "units_beds": record.get("units_beds"),
                "ownership_type": record.get("ownership_type"),
                "state_license_number": record.get("state_license_number"),
                "license_profile_url": record.get("license_profile_url"),
                "county": record.get("county"),
                "source_url": url,
                "is_chain": bool(parent_company),
                "is_independent": not bool(parent_company),
                "source_refs": sorted(source_map[url]),
            }
        )

    records.sort(key=lambda r: (str(r.get("county") or ""), str(r.get("community_name") or ""), str(r.get("source_url") or "")))
    return records


def count_by_county_and_type(records: List[Dict[str, object]]) -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {county: {care: 0 for care in CARE_TYPES.keys()} for county in COUNTIES.keys()}
    for record in records:
        county = record.get("county")
        for care_type in record.get("community_types") or []:
            if county in counts and care_type in counts[county]:
                counts[county][care_type] += 1
    return counts


def county_summaries(records: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    by_county: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for record in records:
        by_county[str(record.get("county") or "")].append(record)

    summaries: Dict[str, Dict[str, object]] = {}
    for county, county_records in by_county.items():
        if not county:
            continue
        chain = sum(1 for r in county_records if r.get("is_chain"))
        independent = sum(1 for r in county_records if r.get("is_independent"))
        total_beds: Optional[int] = None
        exact_beds: List[int] = []
        for record in county_records:
            value = record.get("units_beds")
            if not isinstance(value, str):
                exact_beds = []
                break
            if re.fullmatch(r"\d+", value.strip()):
                exact_beds.append(int(value.strip()))
            else:
                exact_beds = []
                break
        if exact_beds:
            total_beds = sum(exact_beds)
        summaries[county] = {
            "total_communities": len(county_records),
            "total_beds": total_beds,
            "chain_count": chain,
            "independent_count": independent,
        }
    return summaries


def top_operators(records: List[Dict[str, object]], county: Optional[str] = None, limit: int = 10) -> List[Dict[str, object]]:
    operator_counts: Dict[str, int] = defaultdict(int)
    for record in records:
        if county and record.get("county") != county:
            continue
        operator = record.get("parent_company") or record.get("community_name") or "Unknown"
        operator_counts[str(operator)] += 1

    ranked = sorted(operator_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return [
        {"rank": idx, "operator": operator, "community_count": count}
        for idx, (operator, count) in enumerate(ranked, start=1)
    ]


def render_doc(records: List[Dict[str, object]], county_type_counts: Dict[str, Dict[str, int]], summaries: Dict[str, Dict[str, object]]) -> str:
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    total_records = len(records)
    overall_chain = sum(1 for r in records if r.get("is_chain"))
    overall_independent = sum(1 for r in records if r.get("is_independent"))

    lines: List[str] = []
    lines.append("# South Florida Senior Living Market")
    lines.append("")
    lines.append("## Scope And Method")
    lines.append("- Geography: Palm Beach County, Broward County, and Miami-Dade County, Florida")
    lines.append("- Care types: Independent Living, Assisted Living, Memory Care")
    lines.append("- Source: public Seniorly county pages and community detail pages")
    lines.append("- Rules: regulated/licensed communities only, missing values are null, no estimates")
    lines.append(f"- Generated at (UTC): {generated_at}")
    lines.append("")
    lines.append("## Inventory Model")
    lines.append("Each row is a unique Seniorly community URL. `community_types` captures every listed care type found on the county pages.")
    lines.append("License numbers are taken from the Florida HealthFinder profile ID exposed in Seniorly page source when available; otherwise null.")
    lines.append("Ownership type is null unless explicitly surfaced on the public page.")
    lines.append("")
    lines.append("## Count By County And Care Type")
    lines.append("| County | Independent Living | Assisted Living | Memory Care | Total Communities | Chain | Independent |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for county in COUNTIES.keys():
        county_records = [r for r in records if r.get("county") == county]
        type_counts = county_type_counts.get(county, {})
        lines.append(
            f"| {county} | {type_counts.get('Independent Living', 0)} | {type_counts.get('Assisted Living', 0)} | {type_counts.get('Memory Care', 0)} | {len(county_records)} | {summaries.get(county, {}).get('chain_count', 0)} | {summaries.get(county, {}).get('independent_count', 0)} |"
        )
    lines.append("")
    lines.append("## County Summaries")
    lines.append("| County | Total Communities | Total Beds | Chain Count | Independent Count |")
    lines.append("|---|---:|---:|---:|---:|")
    for county in COUNTIES.keys():
        summary = summaries.get(county, {})
        lines.append(
            f"| {county} | {summary.get('total_communities', 0)} | null | {summary.get('chain_count', 0)} | {summary.get('independent_count', 0)} |"
        )
    lines.append("")
    lines.append(f"Overall communities: {total_records}")
    lines.append(f"Overall chain communities: {overall_chain}")
    lines.append(f"Overall independent communities: {overall_independent}")
    lines.append("")
    lines.append("## Top Operators By Community Count")
    lines.append("| Rank | Operator | Community Count |")
    lines.append("|---|---|---:|")
    for row in top_operators(records, limit=10):
        lines.append(f"| {row['rank']} | {row['operator']} | {row['community_count']} |")
    lines.append("")
    lines.append("## Top Operators By County")
    for county in COUNTIES.keys():
        lines.append("")
        lines.append(f"### {county}")
        lines.append("| Rank | Operator | Community Count |")
        lines.append("|---|---|---:|")
        for row in top_operators(records, county=county, limit=10):
            lines.append(f"| {row['rank']} | {row['operator']} | {row['community_count']} |")
    lines.append("")
    lines.append("## Inventory")
    for county in COUNTIES.keys():
        lines.append("")
        lines.append(f"### {county}")
        lines.append("| Name | Community Type | Parent Company | Address | Phone | Website | Number of Units/Beds | Ownership Type | State License Number |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for record in [r for r in records if r.get("county") == county]:
            lines.append(
                "| "
                f"{record.get('community_name') or 'null'} | "
                f"{', '.join(record.get('community_types') or []) or 'null'} | "
                f"{record.get('parent_company') or 'null'} | "
                f"{record.get('address') or 'null'} | "
                f"{record.get('phone') or 'null'} | "
                f"{record.get('website') or 'null'} | "
                f"{record.get('units_beds') or 'null'} | "
                f"{record.get('ownership_type') or 'null'} | "
                f"{record.get('state_license_number') or 'null'} |"
            )
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("Run this command from the repository root to regenerate the inventory:")
    lines.append("```bash")
    lines.append("python scripts/build_south_florida_senior_living.py")
    lines.append("```")
    lines.append(f"Full machine-readable inventory: {OUTPUT_JSON.as_posix()}")
    return "\n".join(lines) + "\n"


def main() -> None:
    records = build_inventory()
    county_type_counts = count_by_county_and_type(records)
    summaries = county_summaries(records)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                "counties": list(COUNTIES.keys()),
                "care_types": list(CARE_TYPES.keys()),
                "record_count": len(records),
                "county_type_counts": county_type_counts,
                "county_summaries": summaries,
                "records": records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    OUTPUT_DOC.write_text(render_doc(records, county_type_counts, summaries), encoding="utf-8")
    print({"records": len(records), "doc": str(OUTPUT_DOC), "json": str(OUTPUT_JSON)})


if __name__ == "__main__":
    main()
