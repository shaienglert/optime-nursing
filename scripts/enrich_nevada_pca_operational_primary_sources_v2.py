from __future__ import annotations

import argparse
import json
import re
import time
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from enrich_nevada_pca_operational_primary_sources import (
    SKIP_DOMAINS,
    TIMEOUT,
    UNKNOWN,
    USER_AGENT,
    agency_tokens,
    extract_operational_facts,
    fetch,
    identity_matches,
    norm,
    same_domain_links,
    strip_html,
)

ALIS_SEARCH_URL = "https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0"
REGULATORY_DOMAINS = ("nvdpbh.aithent.com", "dpbh.nv.gov", "health.nv.gov")
SEARCH_TIMEOUT = 15


def _allowed_candidate(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    domain = parsed.netloc.lower().split(":", 1)[0]
    if parsed.scheme not in {"http", "https"} or not domain:
        return False
    if any(domain == skip or domain.endswith("." + skip) for skip in SKIP_DOMAINS):
        return False
    if any(domain == reg or domain.endswith("." + reg) for reg in REGULATORY_DOMAINS):
        return False
    return True


def hcqc_external_links(task: dict[str, Any]) -> list[tuple[str, str]]:
    """Use the regulator detail page as the first source-discovery surface.

    This does not trust an external link as the agency website. It merely gives
    the primary-source verifier a regulator-connected candidate URL.
    """
    detail_url = str(task.get("hcqc_detail_url") or "").strip()
    if not detail_url.startswith("http"):
        return []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    try:
        session.get(ALIS_SEARCH_URL, timeout=SEARCH_TIMEOUT)
        response = session.get(detail_url, timeout=SEARCH_TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return []
    if response.status_code != 200:
        return []
    body = response.text or ""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', body, flags=re.I | re.S):
        href, anchor = unescape(match.group(1)).strip(), strip_html(match.group(2))
        absolute = urljoin(str(response.url), href)
        if not _allowed_candidate(absolute):
            continue
        cleaned = absolute.split("#", 1)[0]
        if cleaned in seen:
            continue
        seen.add(cleaned)
        out.append((cleaned, f"HCQC detail external link {anchor}".strip()))
    return out


def bing_result_urls(query: str) -> list[tuple[str, str]]:
    url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&count=20"
    try:
        response = requests.get(
            url,
            timeout=SEARCH_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            allow_redirects=True,
        )
    except requests.RequestException:
        return []
    if response.status_code != 200:
        return []
    body = response.text or ""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for block in re.findall(r'<li\b[^>]*class=["\'][^"\']*b_algo[^"\']*["\'][^>]*>(.*?)</li>', body, flags=re.I | re.S):
        match = re.search(r'<h2[^>]*>\s*<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not match:
            continue
        candidate, title = unescape(match.group(1)).strip(), strip_html(match.group(2))
        if not _allowed_candidate(candidate) or candidate in seen:
            continue
        seen.add(candidate)
        out.append((candidate, title))
    return out


def duckduckgo_lite_urls(query: str) -> list[tuple[str, str]]:
    url = f"https://lite.duckduckgo.com/lite/?q={requests.utils.quote(query)}"
    try:
        response = requests.get(url, timeout=SEARCH_TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
    except requests.RequestException:
        return []
    if response.status_code != 200:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, anchor in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', response.text or "", flags=re.I | re.S):
        candidate = unescape(href).strip()
        if candidate.startswith("//"):
            candidate = "https:" + candidate
        if not _allowed_candidate(candidate) or candidate in seen:
            continue
        seen.add(candidate)
        out.append((candidate, strip_html(anchor)))
    return out


def _candidate_matches_search_identity(url: str, title: str, task: dict[str, Any]) -> bool:
    tokens = agency_tokens(str(task.get("agency_name") or ""))
    haystack = norm(f"{url} {title}")
    if not tokens:
        return False
    required = 1 if len(tokens) <= 1 else 2
    token_hits = sum(1 for token in tokens if token in haystack)
    city = norm(task.get("city"))
    location_hint = city in haystack if city else False
    return token_hits >= required or (token_hits >= 1 and location_hint)


def discover_candidates(task: dict[str, Any]) -> list[dict[str, str]]:
    query = str(task.get("official_source_discovery_query") or "").strip()
    if not query:
        query = f'"{task.get("agency_name")}" {task.get("city")} Nevada official home care'
    sources: list[tuple[str, list[tuple[str, str]]]] = [
        ("HCQC_EXTERNAL_LINK", hcqc_external_links(task)),
        ("BING_HTML", bing_result_urls(query)),
        ("DUCKDUCKGO_LITE", duckduckgo_lite_urls(query)),
    ]
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for method, rows in sources:
        for url, title in rows:
            if url in seen:
                continue
            if method != "HCQC_EXTERNAL_LINK" and not _candidate_matches_search_identity(url, title, task):
                continue
            seen.add(url)
            candidates.append({"url": url, "title": title, "discovery_method": method})
            if len(candidates) >= 8:
                return candidates
    return candidates


def verify_candidate(candidate: dict[str, str], task: dict[str, Any], throttle: float) -> dict[str, Any] | None:
    url = candidate["url"]
    try:
        body, status, final_url = fetch(url)
    except requests.RequestException:
        return None
    if status != 200:
        return None

    page_texts = [strip_html(body)]
    pages = [final_url]
    identity = identity_matches(page_texts[0], task)
    for link in same_domain_links(final_url, body):
        if throttle:
            time.sleep(throttle)
        try:
            child_body, child_status, child_final = fetch(link)
        except requests.RequestException:
            continue
        if child_status != 200:
            continue
        child_text = strip_html(child_body)
        page_texts.append(child_text)
        pages.append(child_final)
        if not identity and identity_matches(child_text, task):
            identity = True
    if not identity:
        return None

    combined = " ".join(page_texts)
    facts = extract_operational_facts(combined)
    return {
        "primary_source_url": final_url,
        "discovery_method": candidate["discovery_method"],
        "source_pages": pages,
        "identity_verified": True,
        "serves_las_vegas_valley": True if any(
            token in combined.lower() for token in ("las vegas", "north las vegas", "henderson", "clark county")
        ) else UNKNOWN,
        **facts,
    }


def research_task_v2(task: dict[str, Any], throttle: float) -> dict[str, Any]:
    base = {
        "agency_id": task.get("agency_id") or UNKNOWN,
        "agency_name": task.get("agency_name") or UNKNOWN,
        "license_number": task.get("license_number") or UNKNOWN,
        "license_status": task.get("license_status") or UNKNOWN,
        "address": task.get("address") or UNKNOWN,
        "city": task.get("city") or UNKNOWN,
        "state": task.get("state") or "NV",
        "zip": task.get("zip") or UNKNOWN,
        "phone": task.get("phone") or UNKNOWN,
        "hcqc_detail_url": task.get("hcqc_detail_url") or UNKNOWN,
        "identity_verified": False,
        "primary_source_url": UNKNOWN,
        "serves_las_vegas_valley": UNKNOWN,
        "source_pages": [],
    }
    candidates = discover_candidates(task)
    base["candidate_count"] = len(candidates)
    base["candidate_discovery_methods"] = sorted({row["discovery_method"] for row in candidates})
    for candidate in candidates:
        verified = verify_candidate(candidate, task, throttle)
        if verified:
            base.update(verified)
            base["research_status"] = "PRIMARY_SOURCE_VERIFIED"
            base["policy"] = "The source was discovered through HCQC or a search fallback, then independently verified against the licensed agency identity. Only explicit primary-source operational facts are populated; missing facts remain UNKNOWN."
            return base
    base["research_status"] = "SOURCE_NOT_FOUND" if not candidates else "CANDIDATES_NOT_IDENTITY_VERIFIED"
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="reports/NEVADA_PCA_OPERATIONAL_RESEARCH_QUEUE.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_OPERATIONAL_PRIMARY_RESEARCH.json")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--throttle", type=float, default=0.05)
    args = ap.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    tasks = list(queue.get("tasks") or [])
    start = max(0, args.offset)
    selected = tasks[start:start + max(0, args.limit)]
    records = [research_task_v2(task, max(0.0, args.throttle)) for task in selected]
    payload = {
        "schema_version": "nevada-pca-operational-primary-research-v2.0.0",
        "queue_task_count": len(tasks),
        "attempted": len(selected),
        "identity_verified": sum(1 for row in records if row.get("identity_verified") is True),
        "source_not_found": sum(1 for row in records if row.get("research_status") == "SOURCE_NOT_FOUND"),
        "candidates_not_identity_verified": sum(1 for row in records if row.get("research_status") == "CANDIDATES_NOT_IDENTITY_VERIFIED"),
        "discovery_methods": sorted({method for row in records for method in row.get("candidate_discovery_methods") or []}),
        "records": records,
        "policy": "Research output is staging evidence only. No staged row can alter production recommendations until promoted through a separate identity/field-evidence gate.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "attempted": payload["attempted"],
        "identity_verified": payload["identity_verified"],
        "source_not_found": payload["source_not_found"],
        "candidates_not_identity_verified": payload["candidates_not_identity_verified"],
        "discovery_methods": payload["discovery_methods"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
