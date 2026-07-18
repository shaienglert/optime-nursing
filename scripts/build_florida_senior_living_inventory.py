from __future__ import annotations

import csv
import datetime as dt
import html as html_lib
import json
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = REPO_ROOT / "database" / "florida_senior_living_inventory.json"
OUTPUT_DOC = REPO_ROOT / "reports" / "florida_discovery_inventory.md"
DISCOVERY_REPORT_DIR = REPO_ROOT / "reports" / "discovery"
DISCOVERY_REPORT_MD = DISCOVERY_REPORT_DIR / "discovery_report.md"
COUNTY_PROGRESS_MD = DISCOVERY_REPORT_DIR / "county_progress.md"
DATABASE_STATISTICS_MD = DISCOVERY_REPORT_DIR / "database_statistics.md"
CMS_CACHE = REPO_ROOT / "backend" / "app" / "data" / "provider_information.csv"
CMS_PROVIDER_DATASET_ID = "4pq5-n9py"

FLORIDA_COUNTIES = [
    "Alachua", "Baker", "Bay", "Bradford", "Brevard", "Broward", "Calhoun", "Charlotte", "Citrus",
    "Clay", "Collier", "Columbia", "DeSoto", "Dixie", "Duval", "Escambia", "Flagler", "Franklin",
    "Gadsden", "Gilchrist", "Glades", "Gulf", "Hamilton", "Hardee", "Hendry", "Hernando", "Highlands",
    "Hillsborough", "Holmes", "Indian River", "Jackson", "Jefferson", "Lafayette", "Lake", "Lee", "Leon",
    "Levy", "Liberty", "Madison", "Manatee", "Marion", "Martin", "Miami-Dade", "Monroe", "Nassau",
    "Okaloosa", "Okeechobee", "Orange", "Osceola", "Palm Beach", "Pasco", "Pinellas", "Polk", "Putnam",
    "St. Johns", "St. Lucie", "Santa Rosa", "Sarasota", "Seminole", "Sumter", "Suwannee", "Taylor",
    "Union", "Volusia", "Wakulla", "Walton", "Washington",
]

SENIORLY_CARE_TYPES = {
    "Assisted Living": "assisted-living",
    "Independent Living": "independent-living",
    "Memory Care": "memory-care",
    "Active Adult (55+)": "active-adult",
    "Continuing Care Retirement Communities (CCRC)": "continuing-care-retirement-community",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


def county_slug(county_name: str) -> str:
    normalized = county_name.lower().replace(".", "").replace("'", "")
    normalized = re.sub(r"\s+", "-", normalized)
    return f"{normalized}-county"


def env_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def fetch_html(url: str, retries: int = 3, timeout: int = 30) -> str:
    request = Request(url, headers=HEADERS)
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf8", errors="ignore")
        except HTTPError as error:
            last_error = error
            if error.code in {429, 500, 502, 503, 504} and attempt < retries:
                continue
            raise
        except URLError as error:
            last_error = error
            if attempt < retries:
                continue
            raise
        except TimeoutError as error:
            last_error = error
            if attempt < retries:
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError(f"Unable to fetch URL: {url}")


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


def try_fetch_county_urls(care_slug: str, county_name: str, page_limit: int = 25) -> List[str]:
    slug = county_slug(county_name)
    base_url = f"https://www.seniorly.com/{care_slug}/florida/{slug}"
    discovered: List[str] = []
    seen: Set[str] = set()

    for page_number in range(1, page_limit + 1):
        url = base_url if page_number == 1 else f"{base_url}?page-number={page_number}"
        try:
            html = fetch_html(url)
        except HTTPError as error:
            status = error.code
            if status == 404:
                break
            raise
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
    for pattern in [r"Managed by ([^<\.]+)", r"managed by ([^<\.]+)"]:
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
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "google.com",
        "youtube.com",
    )
    for href in re.findall(r'href="([^"]+)"', html):
        if not href.startswith("http"):
            continue
        if any(domain in href for domain in excluded):
            continue
        return href
    return None


def extract_license_url(html: str) -> Optional[str]:
    match = re.search(r"https://quality\.healthfinder\.fl\.gov/Facility-Provider/Profile/\?LID=\d+", html)
    return match.group(0) if match else None


def extract_license_number(html: str) -> Optional[str]:
    license_url = extract_license_url(html)
    if not license_url:
        return None
    match = re.search(r"LID=(\d+)", license_url)
    return match.group(1) if match else None


def extract_capacity_text(html: str) -> Optional[str]:
    phrase = "Total number of residents this assisted living facility can support"
    idx = html.find(phrase)
    if idx != -1:
        segment = html[idx: idx + 1000]
        match = re.search(r"<!--t=[^>]+-->([^<]+)<!---->", segment)
        if match:
            return html_lib.unescape(match.group(1)).strip() or None

    for pattern in [r'"([^"\n]{1,40}(?:resident capacity|Beds))"', r"up to \d+ Beds", r"\d+ resident capacity"]:
        match = re.search(pattern, html, re.I)
        if match:
            return html_lib.unescape(match.group(0)).strip()
    return None


def parse_address_parts(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None
    parts = [part.strip() for part in str(address).split(",") if part.strip()]
    if len(parts) < 4:
        return None, None, None
    city = parts[-3]
    state = parts[-2]
    zip_code = parts[-1]
    return city, state, zip_code


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
            address = ", ".join(str(part).strip() for part in parts if part)

    community_name = local_business.get("name") if isinstance(local_business, dict) else None
    telephone = local_business.get("telephone") if isinstance(local_business, dict) else None

    care_type = None
    match = re.search(r"https://www\.seniorly\.com/([^/]+)/florida/", url)
    if match:
        care_type = match.group(1).replace("-", " ").title()

    discovered_county = None
    for county_name in FLORIDA_COUNTIES:
        if f"/florida/{county_slug(county_name)}/" in url:
            discovered_county = county_name
            break

    city, state, zip_code = parse_address_parts(address)
    license_url = extract_license_url(html)

    return {
        "community_name": community_name,
        "community_type": care_type,
        "parent_company": extract_management_company(html),
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "phone": telephone,
        "website": extract_external_website(html),
        "units_beds": extract_capacity_text(html),
        "ownership_type": None,
        "state_license_number": extract_license_number(html),
        "license_profile_url": license_url,
        "county": discovered_county,
    }


def ensure_cms_cache() -> Path:
    if CMS_CACHE.exists():
        return CMS_CACHE
    CMS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    meta_url = f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{CMS_PROVIDER_DATASET_ID}"
    with urlopen(meta_url) as response:
        payload = json.load(response)
    download_url = payload["distribution"][0]["downloadURL"]
    with urlopen(download_url) as response:
        CMS_CACHE.write_bytes(response.read())
    return CMS_CACHE


def normalize_name(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def normalize_city(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def seniorly_primary_key(record: Dict[str, object]) -> str:
    if record.get("state_license_number"):
        return f"lic:{record['state_license_number']}"
    return f"name:{normalize_name(record.get('community_name'))}|county:{normalize_name(record.get('county'))}|city:{normalize_city(record.get('city'))}"


def cms_primary_key(row: Dict[str, str]) -> str:
    ccn = (row.get("CMS Certification Number (CCN)") or "").strip()
    if ccn:
        return f"cms:{ccn}"
    return f"name:{normalize_name(row.get('Provider Name'))}|county:{normalize_name(row.get('County/Parish'))}|city:{normalize_city(row.get('City/Town'))}"


def merge_record(base: Dict[str, object], incoming: Dict[str, object]) -> None:
    base_types = set(base.get("community_types") or [])
    incoming_types = set(incoming.get("community_types") or [])
    base["community_types"] = sorted(t for t in (base_types | incoming_types) if t)

    base_sources = set(base.get("source_refs") or [])
    incoming_sources = set(incoming.get("source_refs") or [])
    base["source_refs"] = sorted(base_sources | incoming_sources)

    base_urls = set(base.get("source_urls") or [])
    incoming_urls = set(incoming.get("source_urls") or [])
    base["source_urls"] = sorted(u for u in (base_urls | incoming_urls) if u)

    for key in [
        "community_name", "address", "city", "state", "zip_code", "phone", "website", "units_beds",
        "ownership_type", "state_license_number", "license_profile_url", "county", "parent_company",
        "cms_certification_number", "cms_provider_type", "source_status", "verification_status",
        "last_source_date", "continuing_care_retirement_community",
    ]:
        if not base.get(key) and incoming.get(key):
            base[key] = incoming.get(key)

    if incoming.get("verification_status") == "verified":
        base["verification_status"] = "verified"

    if incoming.get("primary_community_type") and incoming.get("primary_community_type") not in (None, ""):
        if not base.get("primary_community_type"):
            base["primary_community_type"] = incoming.get("primary_community_type")


def build_seniorly_records() -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    records_by_url: Dict[str, Dict[str, object]] = {}
    source_map: Dict[str, Set[str]] = defaultdict(set)
    county_limit = env_int("OPTIME_COUNTY_LIMIT")
    detail_limit = env_int("OPTIME_DETAIL_LIMIT")
    counties = FLORIDA_COUNTIES[:county_limit] if county_limit else FLORIDA_COUNTIES

    for county_name in counties:
        for care_name, care_slug in SENIORLY_CARE_TYPES.items():
            urls = try_fetch_county_urls(care_slug, county_name)
            for listing_url in urls:
                record = records_by_url.setdefault(
                    listing_url,
                    {
                        "community_name": None,
                        "community_types": set(),
                        "parent_company": None,
                        "address": None,
                        "city": None,
                        "state": "FL",
                        "zip_code": None,
                        "phone": None,
                        "website": None,
                        "units_beds": None,
                        "ownership_type": None,
                        "state_license_number": None,
                        "license_profile_url": None,
                        "county": county_name,
                        "source_url": listing_url,
                    },
                )
                record["community_types"].add(care_name)
                source_map[listing_url].add(f"Seniorly:{county_name}:{care_name}")

    detail_urls = list(records_by_url.keys())
    if detail_limit:
        detail_urls = detail_urls[:detail_limit]

    max_workers = min(16, max(4, len(detail_urls) or 1))
    failed_detail_fetches = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_detail, url): url for url in detail_urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                detail = future.result()
            except Exception:
                failed_detail_fetches += 1
                continue
            record = records_by_url[url]
            for key, value in detail.items():
                if key == "community_type":
                    if value:
                        record["community_types"].add(value)
                elif value is not None and record.get(key) in {None, ""}:
                    record[key] = value
                elif value is not None and key in {"parent_company", "website", "units_beds", "state_license_number", "license_profile_url"}:
                    record[key] = value

    records: List[Dict[str, object]] = []
    for url in detail_urls:
        record = records_by_url[url]
        community_types = sorted(t for t in record["community_types"] if t)
        records.append(
            {
                "community_name": record.get("community_name"),
                "community_types": community_types,
                "primary_community_type": community_types[0] if community_types else None,
                "parent_company": record.get("parent_company") or None,
                "address": record.get("address"),
                "city": record.get("city"),
                "state": record.get("state") or "FL",
                "zip_code": record.get("zip_code"),
                "phone": record.get("phone"),
                "website": record.get("website"),
                "units_beds": record.get("units_beds"),
                "ownership_type": record.get("ownership_type"),
                "state_license_number": record.get("state_license_number"),
                "license_profile_url": record.get("license_profile_url"),
                "cms_certification_number": None,
                "cms_provider_type": None,
                "continuing_care_retirement_community": None,
                "county": record.get("county"),
                "source_refs": sorted(source_map[url]),
                "source_urls": [url],
                "verification_status": "verified" if record.get("state_license_number") or record.get("license_profile_url") else "pending_verification",
                "source_status": "active",
                "last_source_date": None,
                "is_chain": bool(record.get("parent_company")),
                "is_independent": not bool(record.get("parent_company")),
            }
        )

    records.sort(key=lambda item: (str(item.get("county") or ""), str(item.get("community_name") or "")))
    return records, {
        "counties_attempted": len(counties),
        "seniorly_urls_discovered": len(records_by_url),
        "seniorly_records_built": len(records),
        "failed_detail_fetches": failed_detail_fetches,
        "sample_mode": bool(county_limit or detail_limit),
    }


def build_cms_records() -> List[Dict[str, object]]:
    cms_path = ensure_cms_cache()
    records: List[Dict[str, object]] = []
    with cms_path.open("r", encoding="utf8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("State") or "").strip().upper() != "FL":
                continue
            county = (row.get("County/Parish") or "").strip()
            name = (row.get("Provider Name") or "").strip()
            if not name:
                continue
            community_types = ["Skilled Nursing"]
            if (row.get("Continuing Care Retirement Community") or "").strip().upper() == "Y":
                community_types.append("Continuing Care Retirement Communities (CCRC)")
            records.append(
                {
                    "community_name": name,
                    "community_types": sorted(set(community_types)),
                    "primary_community_type": "Skilled Nursing",
                    "parent_company": (row.get("Chain Name") or "").strip() or None,
                    "address": (row.get("Provider Address") or "").strip() or None,
                    "city": (row.get("City/Town") or "").strip() or None,
                    "state": "FL",
                    "zip_code": (row.get("ZIP Code") or "").strip() or None,
                    "phone": (row.get("Telephone Number") or "").strip() or None,
                    "website": None,
                    "units_beds": (row.get("Number of Certified Beds") or "").strip() or None,
                    "ownership_type": (row.get("Ownership Type") or "").strip() or None,
                    "state_license_number": None,
                    "license_profile_url": None,
                    "cms_certification_number": (row.get("CMS Certification Number (CCN)") or "").strip() or None,
                    "cms_provider_type": (row.get("Provider Type") or "").strip() or None,
                    "continuing_care_retirement_community": (row.get("Continuing Care Retirement Community") or "").strip() or None,
                    "county": county or None,
                    "source_refs": ["CMS Provider Information", "Medicare Care Compare"],
                    "source_urls": [f"https://data.cms.gov/provider-data/dataset/{CMS_PROVIDER_DATASET_ID}"],
                    "verification_status": "verified",
                    "source_status": "closed" if (row.get("Special Focus Status") or "").strip().upper() == "CLOSED" else "active",
                    "last_source_date": (row.get("Processing Date") or "").strip() or None,
                    "is_chain": bool((row.get("Chain Name") or "").strip()),
                    "is_independent": not bool((row.get("Chain Name") or "").strip()),
                }
            )
    return records


def merge_records(seniorly_records: List[Dict[str, object]], cms_records: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], int]:
    merged: Dict[str, Dict[str, object]] = {}
    alias_to_primary: Dict[str, str] = {}
    duplicate_merges = 0

    def add_record(record: Dict[str, object], primary_key: str, alias_keys: Iterable[str]) -> None:
        nonlocal duplicate_merges
        target_key = alias_to_primary.get(primary_key, primary_key)
        for alias in alias_keys:
            if alias in alias_to_primary:
                target_key = alias_to_primary[alias]
                break

        if target_key in merged:
            merge_record(merged[target_key], record)
            duplicate_merges += 1
        else:
            merged[target_key] = record

        for alias in set([primary_key, *alias_keys]):
            alias_to_primary[alias] = target_key

    for record in seniorly_records:
        primary_key = seniorly_primary_key(record)
        alias_keys = []
        if record.get("community_name"):
            alias_keys.append(f"name:{normalize_name(record.get('community_name'))}|county:{normalize_name(record.get('county'))}|city:{normalize_city(record.get('city'))}")
        add_record(record, primary_key, alias_keys)

    for record in cms_records:
        primary_key = cms_primary_key({
            "CMS Certification Number (CCN)": record.get("cms_certification_number") or "",
            "Provider Name": record.get("community_name") or "",
            "County/Parish": record.get("county") or "",
            "City/Town": record.get("city") or "",
        })
        alias_keys = [f"name:{normalize_name(record.get('community_name'))}|county:{normalize_name(record.get('county'))}|city:{normalize_city(record.get('city'))}"]
        add_record(record, primary_key, alias_keys)

    final_records = list(merged.values())
    for record in final_records:
        community_types = sorted(set(record.get("community_types") or []))
        record["community_types"] = community_types
        record["primary_community_type"] = record.get("primary_community_type") or (community_types[0] if community_types else None)
        record["official_name"] = record.get("community_name")
        record["care_type"] = record.get("primary_community_type")
        record["contact_information"] = {
            "phone": record.get("phone"),
            "website": record.get("website"),
        }
        record["source_list"] = sorted(set(record.get("source_refs") or []))
    final_records.sort(key=lambda item: (str(item.get("county") or ""), str(item.get("city") or ""), str(item.get("community_name") or "")))
    for index, record in enumerate(final_records, start=1):
        record["optime_id"] = f"OPTIME-FL-{index:06d}"
    return final_records, duplicate_merges


def count_by(items: Iterable[Dict[str, object]], field: str) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for item in items:
        value = str(item.get(field) or "UNKNOWN").strip() or "UNKNOWN"
        counts[value] += 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def count_care_types(records: Iterable[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for record in records:
        for care_type in record.get("community_types") or []:
            counts[str(care_type)] += 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def render_summary(records: List[Dict[str, object]], meta: Dict[str, object]) -> str:
    counties = count_by(records, "county")
    care_types = count_care_types(records)
    lines = [
        "# Florida Discovery Inventory",
        "",
        f"- Generated at (UTC): {meta['generated_at_utc']}",
        f"- Records: {len(records)}",
        f"- Florida counties covered: {meta['counties_covered']} / {len(FLORIDA_COUNTIES)}",
        f"- Duplicate merges performed: {meta['duplicate_merges']}",
        "",
        "## Communities By County",
        "",
    ]
    lines.extend([f"- {county}: {count}" for county, count in counties.items()])
    lines.append("")
    lines.append("## Communities By Care Type")
    lines.append("")
    lines.extend([f"- {care_type}: {count}" for care_type, count in care_types.items()])
    return "\n".join(lines) + "\n"


def canonical_key(record: Dict[str, object]) -> str:
    return "|".join(
        [
            normalize_name(record.get("community_name")),
            normalize_name(record.get("county")),
            normalize_city(record.get("city")),
            normalize_name(record.get("address")),
        ]
    )


def load_previous_payload() -> Optional[Dict[str, object]]:
    if not OUTPUT_JSON.exists():
        return None
    try:
        payload = json.loads(OUTPUT_JSON.read_text(encoding="utf8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def compute_cycle_deltas(current_records: List[Dict[str, object]], previous_payload: Optional[Dict[str, object]]) -> Dict[str, int]:
    if not previous_payload:
        verified_now = sum(1 for r in current_records if r.get("verification_status") == "verified")
        return {
            "communities_added": len(current_records),
            "communities_verified_delta": verified_now,
            "communities_updated": 0,
            "closed_communities": 0,
        }

    previous_records = previous_payload.get("records")
    if not isinstance(previous_records, list):
        previous_records = []

    prev_map = {
        canonical_key(r): r
        for r in previous_records
        if isinstance(r, dict)
    }
    curr_map = {
        canonical_key(r): r
        for r in current_records
        if isinstance(r, dict)
    }

    added_keys = set(curr_map.keys()) - set(prev_map.keys())
    closed_keys = set(prev_map.keys()) - set(curr_map.keys())

    updated = 0
    tracked_fields = [
        "phone",
        "website",
        "state_license_number",
        "license_profile_url",
        "parent_company",
        "primary_community_type",
        "source_status",
    ]
    for key in set(curr_map.keys()) & set(prev_map.keys()):
        curr = curr_map[key]
        prev = prev_map[key]
        if any((curr.get(field) or "") != (prev.get(field) or "") for field in tracked_fields):
            updated += 1

    verified_now = sum(1 for r in current_records if r.get("verification_status") == "verified")
    verified_prev = sum(1 for r in previous_records if isinstance(r, dict) and r.get("verification_status") == "verified")

    return {
        "communities_added": len(added_keys),
        "communities_verified_delta": max(0, verified_now - verified_prev),
        "communities_updated": updated,
        "closed_communities": len(closed_keys),
    }


def render_discovery_report(records: List[Dict[str, object]], meta: Dict[str, object], deltas: Dict[str, int]) -> str:
    verified_total = sum(1 for record in records if record.get("verification_status") == "verified")
    pending_total = len(records) - verified_total
    counties_completed = int(meta.get("seniorly", {}).get("counties_attempted") or 0)
    counties_total = len(FLORIDA_COUNTIES)
    counties_remaining = max(0, counties_total - counties_completed)
    coverage_pct = round((counties_completed / counties_total) * 100.0, 1) if counties_total else 0.0
    next_county = meta.get("counties_missing", [None])[0] if meta.get("counties_missing") else None

    lines = [
        "# Discovery Report",
        "",
        f"- Generated at (UTC): {meta['generated_at_utc']}",
        "",
        "## Executive Summary",
        "",
        f"- Counties Completed: **{counties_completed}**",
        f"- Counties Remaining: **{counties_remaining}**",
        f"- Communities Added: **{deltas['communities_added']}**",
        f"- Communities Verified: **{deltas['communities_verified_delta']}**",
        f"- Communities Updated: **{deltas['communities_updated']}**",
        f"- Duplicates Removed: **{meta['duplicate_merges']}**",
        f"- Closed Communities: **{deltas['closed_communities']}**",
        f"- Coverage Percentage: **{coverage_pct}%**",
        f"- Remaining Gaps: **{len(meta['counties_missing'])} counties without discovered records**",
        f"- Next County: **{next_county or 'NONE'}**",
        "",
        "## Discovery Totals",
        "",
        f"- Total Communities in Database: **{len(records)}**",
        f"- Verified Communities: **{verified_total}**",
        f"- Pending Verification: **{pending_total}**",
    ]
    return "\n".join(lines) + "\n"


def render_county_progress(records: List[Dict[str, object]], meta: Dict[str, object]) -> str:
    counts = count_by(records, "county")
    attempted = set(FLORIDA_COUNTIES[: int(meta.get("seniorly", {}).get("counties_attempted") or 0)])

    lines = [
        "# County Progress",
        "",
        f"- Generated at (UTC): {meta['generated_at_utc']}",
        "",
        "| County | Processed In Cycle | Communities Found | Status |",
        "| --- | --- | --- | --- |",
    ]
    for county in FLORIDA_COUNTIES:
        processed = "YES" if county in attempted else "NO"
        found = counts.get(county, 0)
        if processed == "NO":
            status = "NOT_PROCESSED"
        elif found == 0:
            status = "PROCESSED_NO_COMMUNITIES_FOUND"
        else:
            status = "PROCESSED_WITH_COMMUNITIES"
        lines.append(f"| {county} | {processed} | {found} | {status} |")
    return "\n".join(lines) + "\n"


def render_database_statistics(records: List[Dict[str, object]], meta: Dict[str, object]) -> str:
    verification_counts = count_by(records, "verification_status")
    source_status_counts = count_by(records, "source_status")
    care_type_counts = count_care_types(records)

    missing_fields = {
        "community_name": sum(1 for r in records if not r.get("community_name")),
        "address": sum(1 for r in records if not r.get("address")),
        "county": sum(1 for r in records if not r.get("county")),
        "city": sum(1 for r in records if not r.get("city")),
        "state": sum(1 for r in records if not r.get("state")),
        "zip_code": sum(1 for r in records if not r.get("zip_code")),
        "phone": sum(1 for r in records if not r.get("phone")),
        "website": sum(1 for r in records if not r.get("website")),
        "state_license_number": sum(1 for r in records if not r.get("state_license_number")),
        "care_type": sum(1 for r in records if not r.get("primary_community_type")),
        "ownership": sum(1 for r in records if not r.get("ownership_type") and not r.get("parent_company")),
    }

    lines = [
        "# Database Statistics",
        "",
        f"- Generated at (UTC): {meta['generated_at_utc']}",
        f"- Total Records: {len(records)}",
        f"- Duplicate Merges: {meta['duplicate_merges']}",
        "",
        "## Verification Status",
        "",
    ]
    lines.extend([f"- {k}: {v}" for k, v in verification_counts.items()])

    lines.extend([
        "",
        "## Source Status",
        "",
    ])
    lines.extend([f"- {k}: {v}" for k, v in source_status_counts.items()])

    lines.extend([
        "",
        "## Care Types",
        "",
    ])
    lines.extend([f"- {k}: {v}" for k, v in care_type_counts.items()])

    lines.extend([
        "",
        "## Missing Information",
        "",
        "| Field | Missing Count |",
        "| --- | --- |",
    ])
    for field, count in missing_fields.items():
        lines.append(f"| {field} | {count} |")

    return "\n".join(lines) + "\n"


def write_discovery_reports(records: List[Dict[str, object]], meta: Dict[str, object], deltas: Dict[str, int]) -> None:
    DISCOVERY_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERY_REPORT_MD.write_text(render_discovery_report(records, meta, deltas), encoding="utf8")
    COUNTY_PROGRESS_MD.write_text(render_county_progress(records, meta), encoding="utf8")
    DATABASE_STATISTICS_MD.write_text(render_database_statistics(records, meta), encoding="utf8")


def main() -> None:
    previous_payload = load_previous_payload()
    seniorly_records, seniorly_meta = build_seniorly_records()
    cms_records = build_cms_records()
    merged_records, duplicate_merges = merge_records(seniorly_records, cms_records)

    counties_covered = sorted({str(record.get("county") or "UNKNOWN") for record in merged_records if record.get("county")})
    meta = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "record_count": len(merged_records),
        "counties_total": len(FLORIDA_COUNTIES),
        "counties_covered": len(counties_covered),
        "counties_missing": [county for county in FLORIDA_COUNTIES if county not in counties_covered],
        "care_types_discovered": sorted(count_care_types(merged_records).keys()),
        "source_families": [
            "Seniorly public county listings",
            "Seniorly public community detail pages",
            "CMS Provider Information",
            "Medicare Care Compare",
            "Florida HealthFinder profile links exposed on source pages",
        ],
        "duplicate_merges": duplicate_merges,
        "seniorly": seniorly_meta,
        "cms_records_built": len(cms_records),
    }

    payload = {
        "generated_at_utc": meta["generated_at_utc"],
        "record_count": meta["record_count"],
        "counties_total": meta["counties_total"],
        "counties_covered": meta["counties_covered"],
        "counties_missing": meta["counties_missing"],
        "care_types_discovered": meta["care_types_discovered"],
        "source_families": meta["source_families"],
        "duplicate_merges": meta["duplicate_merges"],
        "seniorly": meta["seniorly"],
        "cms_records_built": meta["cms_records_built"],
        "records": merged_records,
    }

    deltas = compute_cycle_deltas(merged_records, previous_payload)

    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf8")
    OUTPUT_DOC.write_text(render_summary(merged_records, meta), encoding="utf8")
    write_discovery_reports(merged_records, meta, deltas)

    print(f"Wrote {OUTPUT_JSON}")
    print(f"Wrote {OUTPUT_DOC}")
    print(f"Wrote {DISCOVERY_REPORT_MD}")
    print(f"Wrote {COUNTY_PROGRESS_MD}")
    print(f"Wrote {DATABASE_STATISTICS_MD}")
    print(f"FL_COUNTIES_COVERED={meta['counties_covered']}")
    print(f"FL_COUNTIES_TOTAL={meta['counties_total']}")
    print(f"FL_COUNTIES_PROCESSED={meta['seniorly']['counties_attempted']}")
    print(f"RECORD_COUNT={meta['record_count']}")
    print(f"COMMUNITIES_ADDED={deltas['communities_added']}")
    print(f"COMMUNITIES_VERIFIED_DELTA={deltas['communities_verified_delta']}")
    print(f"COMMUNITIES_UPDATED={deltas['communities_updated']}")
    print(f"CLOSED_COMMUNITIES={deltas['closed_communities']}")
    print(f"DUPLICATE_MERGES={meta['duplicate_merges']}")
    print(f"SAMPLE_MODE={int(meta['seniorly']['sample_mode'])}")


if __name__ == "__main__":
    main()
