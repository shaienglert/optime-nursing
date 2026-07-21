from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote_plus

import requests

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "backend" / "optime_nursing.db"
REPORTS = ROOT / "reports"
COMMUNITY_INTEL = ROOT / "database" / "community_cultural_intelligence.json"
FL_INVENTORY = ROOT / "database" / "florida_senior_living_inventory.json"

AUDIT_MD = REPORTS / "FULL_SOURCE_CONNECTIVITY_AUDIT.md"
AUDIT_JSON = REPORTS / "FULL_SOURCE_CONNECTIVITY_AUDIT.json"
MATRIX_MD = REPORTS / "SOURCE_CONNECTIVITY_MATRIX.md"

TIMEOUT_SECONDS = 15
USER_AGENT = "Mozilla/5.0 (compatible; OPTIME-Source-Audit/1.0; +https://optime-nursing.local)"
ALLOWED_STATUSES = {
    "CONNECTED_REAL_DATA",
    "CONNECTED_NO_USEFUL_DATA",
    "GEO_BLOCKED_OR_SUSPECTED",
    "RATE_LIMITED",
    "AUTH_REQUIRED",
    "BOT_CHALLENGE",
    "ACCESS_DENIED",
    "ENDPOINT_BROKEN",
    "DNS_OR_NETWORK_FAILURE",
    "TIMEOUT",
    "NOT_TESTABLE_WITH_CURRENT_CONFIG",
}
SOURCE_SUCCESS_STATES = {"NEW_VALUE", "SUCCESS", "RAN_CONNECTED_NO_NEW_VALUE"}


@dataclass
class SourceCase:
    source_name: str
    organization: str
    category: str
    endpoint: str
    access_method: str
    criticality: str
    connector_implemented: str
    connector_functional: str
    used_by_optime: str
    action_required_hint: str
    test_kind: str
    metadata: dict[str, Any]


class FetchError(Exception):
    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch(url: str, *, timeout: int = TIMEOUT_SECONDS, headers: Optional[dict[str, str]] = None, stream: bool = False) -> requests.Response:
    hdrs = {"User-Agent": USER_AGENT}
    if headers:
        hdrs.update(headers)
    try:
        return requests.get(url, timeout=timeout, headers=hdrs, stream=stream, allow_redirects=True)
    except requests.Timeout as exc:
        raise FetchError("TIMEOUT", str(exc)) from exc
    except requests.ConnectionError as exc:
        raise FetchError("DNS_OR_NETWORK_FAILURE", str(exc)) from exc
    except requests.RequestException as exc:
        raise FetchError("ENDPOINT_BROKEN", str(exc)) from exc


def classify_http_response(response: requests.Response, text: str) -> tuple[str, str]:
    body = (text or "")[:10000].lower()
    if response.status_code == 429:
        return "RATE_LIMITED", "HTTP 429"
    if response.status_code == 401:
        return "AUTH_REQUIRED", "HTTP 401"
    if response.status_code == 403:
        if "captcha" in body or "cloudflare" in body or "attention required" in body:
            return "BOT_CHALLENGE", "403 with challenge markers"
        if "access denied" in body or "forbidden" in body or "blocked" in body:
            return "GEO_BLOCKED_OR_SUSPECTED", "403/access denied"
        return "ACCESS_DENIED", "HTTP 403"
    if response.status_code == 404:
        return "ENDPOINT_BROKEN", "HTTP 404"
    if response.status_code >= 500:
        return "ENDPOINT_BROKEN", f"HTTP {response.status_code}"
    if response.status_code >= 400:
        return "ACCESS_DENIED", f"HTTP {response.status_code}"
    if "captcha" in body or "cloudflare" in body or "attention required" in body:
        return "BOT_CHALLENGE", "Challenge page"
    return "", ""


def read_csv_sample(download_url: str, *, max_bytes: int = 800_000) -> tuple[list[str], list[dict[str, str]], int]:
    response = fetch(download_url, stream=True)
    chunks: list[bytes] = []
    bytes_read = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        chunks.append(chunk)
        bytes_read += len(chunk)
        if bytes_read >= max_bytes:
            break
    raw = b"".join(chunks).decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(raw))
    rows: list[dict[str, str]] = []
    try:
        for index, row in enumerate(reader):
            rows.append({str(k): str(v) for k, v in row.items()})
            if index >= 399:
                break
    except csv.Error:
        pass
    return list(reader.fieldnames or []), rows, bytes_read


def test_cms_dataset(dataset_id: str, purpose: str, required_fields: list[str], record_predicate: Callable[[dict[str, str]], bool], record_desc: str) -> dict[str, Any]:
    started = time.perf_counter()
    meta_url = f"https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{dataset_id}"
    try:
        meta_resp = fetch(meta_url)
        meta_text = meta_resp.text
        status, reason = classify_http_response(meta_resp, meta_text)
        if status:
            return build_result(False, False, status, meta_url, meta_resp.status_code, reason, time.perf_counter() - started, "metastore access failed", None)
        meta = meta_resp.json()
        distributions = meta.get("distribution") or []
        download_url = str(distributions[0].get("downloadURL")) if distributions else ""
        if not download_url:
            return build_result(True, False, "ENDPOINT_BROKEN", meta_url, meta_resp.status_code, "No distribution URL", time.perf_counter() - started, "metastore missing downloadURL", None)

        fields, rows, bytes_read = read_csv_sample(download_url)
        if not rows:
            return build_result(True, False, "CONNECTED_NO_USEFUL_DATA", download_url, 200, "No CSV rows parsed from sample", time.perf_counter() - started, f"fields={len(fields)} bytes={bytes_read}", None)

        missing_fields = [field for field in required_fields if field not in fields]
        if missing_fields:
            return build_result(True, False, "CONNECTED_NO_USEFUL_DATA", download_url, 200, f"Missing required fields: {missing_fields}", time.perf_counter() - started, f"fields={fields[:20]}", None)

        record = next((row for row in rows if record_predicate(row)), rows[0])
        evidence = {
            "dataset_title": meta.get("title"),
            "download_url": download_url,
            "sample_record": {key: record.get(key) for key in required_fields[:8]},
            "record_type": record_desc,
            "rows_scanned": len(rows),
            "bytes_read": bytes_read,
            "purpose": purpose,
        }
        return build_result(True, True, "CONNECTED_REAL_DATA", download_url, 200, "Useful real dataset rows retrieved", time.perf_counter() - started, json.dumps(evidence, ensure_ascii=False), record_desc)
    except FetchError as exc:
        return build_result(False, False, exc.status, meta_url, None, exc.reason, time.perf_counter() - started, exc.reason, None)
    except Exception as exc:  # noqa: BLE001
        return build_result(False, False, "ENDPOINT_BROKEN", meta_url, None, str(exc), time.perf_counter() - started, str(exc), None)


def test_html_source(url: str, *, useful_patterns: list[str], useless_patterns: Optional[list[str]] = None, sample_desc: str = "HTML content") -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = fetch(url)
        text = response.text
        status, reason = classify_http_response(response, text)
        if status:
            return build_result(response.ok, False, status, str(response.url), response.status_code, reason, time.perf_counter() - started, reason, None)
        plain = html_to_text(text)
        lower = plain.lower()
        for pattern in useless_patterns or []:
            if pattern.lower() in lower:
                return build_result(True, False, "CONNECTED_NO_USEFUL_DATA", str(response.url), response.status_code, f"Found useless content marker: {pattern}", time.perf_counter() - started, plain[:400], None)
        found = next((pattern for pattern in useful_patterns if pattern.lower() in lower), None)
        if found:
            return build_result(True, True, "CONNECTED_REAL_DATA", str(response.url), response.status_code, f"Found useful content marker: {found}", time.perf_counter() - started, plain[:700], sample_desc)
        return build_result(True, False, "CONNECTED_NO_USEFUL_DATA", str(response.url), response.status_code, "Connected but expected content markers not found", time.perf_counter() - started, plain[:700], None)
    except FetchError as exc:
        return build_result(False, False, exc.status, url, None, exc.reason, time.perf_counter() - started, exc.reason, None)
    except Exception as exc:  # noqa: BLE001
        return build_result(False, False, "ENDPOINT_BROKEN", url, None, str(exc), time.perf_counter() - started, str(exc), None)


def build_result(network_access: bool, real_data: bool, final_status: str, tested_endpoint: str, http_status: Optional[int], error_reason: str, duration: float, evidence: str, example_record_type: Optional[str]) -> dict[str, Any]:
    if final_status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported status: {final_status}")
    return {
        "network_access": "YES" if network_access else "NO",
        "real_data_retrieval": "YES" if real_data else "NO",
        "tested_endpoint": tested_endpoint,
        "http_status": http_status,
        "response_content_evidence": evidence,
        "example_record_type": example_record_type,
        "duration_seconds": round(duration, 2),
        "final_status": final_status,
        "error_or_block_reason": error_reason,
    }


def load_previous_status_map() -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    if not DB_PATH.exists():
        return mapping
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute(
        """
        select source_name, source_locator, request_status
        from external_source_request_logs
        where claim_type='__source_attempt__'
        order by id desc
        """
    ).fetchall()
    for source_name, source_locator, request_status in rows:
        key = (str(source_name), str(source_locator))
        if key not in mapping:
            mapping[key] = str(request_status)
    conn.close()
    return mapping


def load_previous_blocked_official_sites() -> tuple[list[dict[str, str]], Optional[dict[str, str]]]:
    failures: list[dict[str, str]] = []
    success_sample: Optional[dict[str, str]] = None
    if not DB_PATH.exists():
        return failures, success_sample
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    targeted_run = "20260720T222246Z"
    fail_rows = cur.execute(
        """
        select facility_name, facility_cms_id, source_locator, request_status
        from external_source_request_logs
        where run_id=? and claim_type='__source_attempt__' and source_name='Official website' and request_status not in ('NEW_VALUE','SUCCESS','RAN_CONNECTED_NO_NEW_VALUE')
        order by facility_name asc
        """,
        (targeted_run,),
    ).fetchall()
    for facility_name, cms_id, source_locator, request_status in fail_rows:
        failures.append({
            "facility_name": str(facility_name),
            "cms_id": str(cms_id),
            "url": str(source_locator),
            "previous_status": str(request_status),
        })
    row = cur.execute(
        """
        select facility_name, facility_cms_id, source_locator, request_status
        from external_source_request_logs
        where run_id=? and claim_type='__source_attempt__' and source_name='Official website' and request_status in ('NEW_VALUE','SUCCESS','RAN_CONNECTED_NO_NEW_VALUE')
        order by id asc
        limit 1
        """,
        (targeted_run,),
    ).fetchone()
    if row:
        success_sample = {
            "facility_name": str(row[0]),
            "cms_id": str(row[1]),
            "url": str(row[2]),
            "previous_status": str(row[3]),
        }
    conn.close()
    return failures, success_sample


def load_seniorly_sample_url() -> Optional[str]:
    if not COMMUNITY_INTEL.exists():
        return None
    payload = json.loads(COMMUNITY_INTEL.read_text(encoding="utf-8"))
    for row in payload.get("records") or []:
        for item in row.get("source_urls") or []:
            if isinstance(item, dict):
                url = str(item.get("source_url") or "")
                if "seniorly.com" in url.lower():
                    return url
    return None


def load_ahca_sample_url() -> Optional[str]:
    if not FL_INVENTORY.exists():
        return None
    payload = json.loads(FL_INVENTORY.read_text(encoding="utf-8"))
    for row in payload.get("records") or []:
        url = str(row.get("license_profile_url") or "").strip()
        if url:
            return url
    return None


def auth_env_present(names: list[str]) -> bool:
    return any(bool(os.getenv(name)) for name in names)


def test_google_reviews() -> dict[str, Any]:
    api_keys = ["GOOGLE_PLACES_API_KEY"]
    if not auth_env_present(api_keys):
        return build_result(True, False, "NOT_TESTABLE_WITH_CURRENT_CONFIG", "https://www.google.com/maps", None, f"Missing required auth: {api_keys}", 0.0, "Current repo references API-key-backed access but env is absent", None)
    return test_html_source("https://www.google.com/maps", useful_patterns=["Google Maps"], sample_desc="Google Maps landing content")


def test_auth_optional_site(url: str, auth_names: list[str], label: str) -> dict[str, Any]:
    if not auth_env_present(auth_names):
        started = time.perf_counter()
        try:
            response = fetch(url)
            text = response.text
            status, reason = classify_http_response(response, text)
            if status:
                return build_result(response.ok, False, status, str(response.url), response.status_code, reason, time.perf_counter() - started, reason, None)
            return build_result(True, False, "NOT_TESTABLE_WITH_CURRENT_CONFIG", str(response.url), response.status_code, f"Landing page reachable but {label} connector auth missing: {auth_names}", time.perf_counter() - started, html_to_text(text)[:300], None)
        except FetchError as exc:
            return build_result(False, False, exc.status, url, None, exc.reason, time.perf_counter() - started, exc.reason, None)
    return test_html_source(url, useful_patterns=[label], sample_desc=f"{label} public content")


def make_inventory() -> list[SourceCase]:
    previous_failures, success_sample = load_previous_blocked_official_sites()
    seniorly = load_seniorly_sample_url() or "https://www.seniorly.com/"
    ahca_sample = load_ahca_sample_url() or "https://ahca.myflorida.com/health-facility-and-provider-search"

    inventory: list[SourceCase] = [
        SourceCase("CMS Provider Dataset (4pq5-n9py)", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/4pq5-n9py", "CMS metastore API + CSV distribution", "CRITICAL", "YES", "YES", "YES", "None if accessible", "cms_provider", {}),
        SourceCase("CMS Inspection Dataset (r5ix-sfxw)", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/r5ix-sfxw", "CMS metastore API + CSV distribution", "CRITICAL", "YES", "YES", "YES", "None if accessible", "cms_inspection", {}),
        SourceCase("CMS Quality Dataset (djen-97ju)", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/djen-97ju", "CMS metastore API + CSV distribution", "CRITICAL", "YES", "YES", "YES", "None if accessible", "cms_quality", {}),
        SourceCase("CMS Survey Dataset (svdt-c123)", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/svdt-c123", "CMS metastore API + CSV distribution", "SECONDARY", "PARTIAL", "PARTIAL", "PARTIAL", "Needed if survey-level usage is expected", "cms_survey", {}),
        SourceCase("CMS Staffing/PBJ Fields", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/4pq5-n9py", "Provider dataset staffing-related fields", "CRITICAL", "YES", "YES", "YES", "Confirm staffing fields remain populated", "cms_staffing", {}),
        SourceCase("CMS Ownership Fields", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/4pq5-n9py", "Provider dataset ownership-related fields", "CRITICAL", "PARTIAL", "PARTIAL", "PARTIAL", "No direct dedicated ownership connector", "cms_ownership", {}),
        SourceCase("CMS Penalties/Fines Fields", "CMS", "FEDERAL/CMS", "https://data.cms.gov/provider-data/dataset/4pq5-n9py", "Provider dataset penalty-related fields", "CRITICAL", "PARTIAL", "PARTIAL", "PARTIAL", "No dedicated live penalties connector", "cms_penalties", {}),
        SourceCase("Medicare Care Compare", "Medicare", "FEDERAL/MEDICARE", "https://www.medicare.gov/care-compare/", "Public web app", "CRITICAL", "NO", "NO", "MENTIONED", "Would require explicit connector/search path", "html", {"useful_patterns": ["care compare", "find and compare providers"], "useless_patterns": ["enable javascript"]}),
        SourceCase("Florida AHCA Portal", "Florida AHCA", "FLORIDA", "https://ahca.myflorida.com/", "Public website", "CRITICAL", "PARTIAL", "NO", "MENTIONED", "Would require live AHCA connector", "html", {"useful_patterns": ["agency for health care administration", "health care facility"], "useless_patterns": []}),
        SourceCase("Florida AHCA License Profile Sample", "Florida AHCA", "FLORIDA", ahca_sample, "Public facility/license profile page", "CRITICAL", "PARTIAL", "NO", "MENTIONED", "Would require parsing and facility mapping", "html", {"useful_patterns": ["license", "provider", "facility"], "useless_patterns": []}),
        SourceCase("Official Facility Website Sample - Prior Success", "Facility Website", "FACILITY_PRIMARY", success_sample["url"] if success_sample else "https://biscaynerehab.com/", "Registry-backed official facility URL", "CRITICAL", "YES", "PARTIAL", "YES", "Monitor variability by domain", "official_site", {"facility_name": success_sample["facility_name"] if success_sample else "BISCAYNE HEALTH AND REHABILITATION CENTER", "previous_status": success_sample["previous_status"] if success_sample else "RAN_CONNECTED_NO_NEW_VALUE"}),
        SourceCase("Seniorly Sample Profile", "Seniorly", "REPUTATION/PROFILE", seniorly, "Public profile page", "SECONDARY", "YES", "PARTIAL", "YES", "Profile parsing remains shallow", "seniorly", {"useful_patterns": ["reviews", "pricing", "care offered"], "useless_patterns": []}),
        SourceCase("Google Reviews / Maps", "Google", "REVIEWS/REPUTATION", "https://www.google.com/maps", "API-key-backed or public maps page", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Auth/config missing for real connector", "google_reviews", {}),
        SourceCase("Yelp", "Yelp", "REVIEWS/REPUTATION", "https://www.yelp.com/", "Public web or API", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Auth/config missing for real connector", "auth_optional_site", {"auth": ["YELP_API_KEY"], "label": "Yelp"}),
        SourceCase("Facebook", "Meta", "REVIEWS/REPUTATION", "https://www.facebook.com/", "Public web or Graph API", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Token missing for real connector", "auth_optional_site", {"auth": ["FACEBOOK_ACCESS_TOKEN"], "label": "Facebook"}),
        SourceCase("Instagram", "Meta", "REVIEWS/REPUTATION", "https://www.instagram.com/", "Public web or API", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Token missing for real connector", "auth_optional_site", {"auth": ["INSTAGRAM_ACCESS_TOKEN"], "label": "Instagram"}),
        SourceCase("LinkedIn", "LinkedIn", "REVIEWS/REPUTATION", "https://www.linkedin.com/", "Public web or API", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Auth missing for real connector", "auth_optional_site", {"auth": ["LINKEDIN_API_KEY", "LINKEDIN_ACCESS_TOKEN"], "label": "LinkedIn"}),
        SourceCase("Indeed", "Indeed", "REVIEWS/REPUTATION", "https://www.indeed.com/", "Public web or API", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Auth missing for real connector", "auth_optional_site", {"auth": ["INDEED_API_KEY"], "label": "Indeed"}),
        SourceCase("Glassdoor", "Glassdoor", "REVIEWS/REPUTATION", "https://www.glassdoor.com/", "Public web or API", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "Auth missing for real connector", "auth_optional_site", {"auth": ["GLASSDOOR_API_KEY"], "label": "Glassdoor"}),
        SourceCase("Local News (Google News)", "Google News", "NEWS/PUBLIC_WEB", f"https://news.google.com/search?q={quote_plus('Florida nursing home')}", "Public search page", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "No dedicated article ingestion connector", "html", {"useful_patterns": ["nursing", "florida", "home"], "useless_patterns": []}),
        SourceCase("Press Releases (PRNewswire)", "PR Newswire", "NEWS/PUBLIC_WEB", "https://www.prnewswire.com/", "Public website", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "No dedicated press-release ingestion connector", "html", {"useful_patterns": ["press release", "news releases"], "useless_patterns": []}),
        SourceCase("Public Court Records (CourtListener)", "CourtListener", "LEGAL/REGULATORY", f"https://www.courtlistener.com/?q={quote_plus('Florida nursing home')}", "Public search page", "SECONDARY", "PARTIAL", "NO", "PARTIAL", "No live legal ingestion connector", "html", {"useful_patterns": ["courtlistener", "cases", "opinions"], "useless_patterns": []}),
        SourceCase("Caring.com", "Caring.com", "REVIEWS/REPUTATION", "https://www.caring.com/", "Public website only", "SECONDARY", "NO", "NO", "MENTIONED", "No configured connector or endpoint", "html", {"useful_patterns": ["senior living", "reviews"], "useless_patterns": []}),
        SourceCase("A Place for Mom", "A Place for Mom", "REVIEWS/REPUTATION", "https://www.aplaceformom.com/", "Public website only", "SECONDARY", "NO", "NO", "MENTIONED", "No configured connector or endpoint", "html", {"useful_patterns": ["senior living", "care options"], "useless_patterns": []}),
        SourceCase("SeniorAdvisor", "SeniorAdvisor", "REVIEWS/REPUTATION", "https://www.senioradvisor.com/", "Public website only", "SECONDARY", "NO", "NO", "MENTIONED", "No configured connector or endpoint", "html", {"useful_patterns": ["senior", "reviews"], "useless_patterns": []}),
        SourceCase("BBB", "Better Business Bureau", "OTHER", "https://www.bbb.org/", "Public website only", "SECONDARY", "NO", "NO", "NO", "Source marked unconfigured in repo audits", "html", {"useful_patterns": ["better business bureau"], "useless_patterns": []}),
        SourceCase("Reddit", "Reddit", "OTHER", "https://www.reddit.com/", "Public website only", "SECONDARY", "NO", "NO", "NO", "Source marked unconfigured in repo audits", "html", {"useful_patterns": ["reddit"], "useless_patterns": []}),
        SourceCase("Public Event Calendars", "Various", "OTHER", "N/A", "Conceptual source only; no concrete configured endpoint", "SECONDARY", "NO", "NO", "MENTIONED", "Needs endpoint inventory before testing", "not_testable", {}),
    ]

    for idx, failure in enumerate(previous_failures, start=1):
        inventory.append(
            SourceCase(
                f"Official Facility Website Sample - Prior Failure {idx}",
                "Facility Website",
                "FACILITY_PRIMARY",
                failure["url"],
                "Previously blocked/rate-limited registry-backed facility URL",
                "CRITICAL",
                "YES",
                "PARTIAL",
                "YES",
                "Monitor if current network environment restores access",
                "official_site",
                {"facility_name": failure["facility_name"], "previous_status": failure["previous_status"], "cms_id": failure["cms_id"]},
            )
        )

    return inventory


def evaluate_source(case: SourceCase, previous_map: dict[tuple[str, str], str]) -> dict[str, Any]:
    started_at = now_iso()
    previous_status = case.metadata.get("previous_status") or previous_map.get((case.source_name.replace(" Sample - Prior Success", "").replace(" Sample - Prior Failure 1", "").replace(" Sample - Prior Failure 2", "").replace(" Sample - Prior Failure 3", ""), case.endpoint)) or previous_map.get((case.source_name, case.endpoint)) or "UNKNOWN"

    print(f"[{case.source_name}] START")

    if case.test_kind == "not_testable":
        result = build_result(False, False, "NOT_TESTABLE_WITH_CURRENT_CONFIG", case.endpoint, None, case.action_required_hint, 0.0, case.action_required_hint, None)
    elif case.test_kind == "cms_provider":
        result = test_cms_dataset(
            "4pq5-n9py",
            "Provider master facility records",
            ["CMS Certification Number (CCN)", "Provider Name", "Ownership Type", "Number of Certified Beds"],
            lambda row: bool(row.get("CMS Certification Number (CCN)")) and bool(row.get("Provider Name")),
            "Real provider master record",
        )
    elif case.test_kind == "cms_inspection":
        result = test_cms_dataset(
            "r5ix-sfxw",
            "Inspection and deficiency rows",
            ["CMS Certification Number (CCN)", "Provider Name", "Deficiency Prefix", "Deficiency Category"],
            lambda row: bool(row.get("CMS Certification Number (CCN)")) and bool(row.get("Deficiency Category")),
            "Real deficiency/inspection row",
        )
    elif case.test_kind == "cms_quality":
        result = test_cms_dataset(
            "djen-97ju",
            "Quality measure rows",
            ["CMS Certification Number (CCN)", "Provider Name", "Measure Code", "Measure Description"],
            lambda row: bool(row.get("CMS Certification Number (CCN)")) and bool(row.get("Measure Code")),
            "Real quality-measure row",
        )
    elif case.test_kind == "cms_survey":
        result = test_cms_dataset(
            "svdt-c123",
            "Survey dataset",
            ["CMS Certification Number (CCN)"],
            lambda row: bool(row.get("CMS Certification Number (CCN)")),
            "Real survey row",
        )
    elif case.test_kind == "cms_staffing":
        result = test_cms_dataset(
            "4pq5-n9py",
            "PBJ-derived staffing fields in provider dataset",
            ["CMS Certification Number (CCN)", "Reported RN Staffing Hours per Resident per Day", "Reported Total Nurse Staffing Hours per Resident per Day"],
            lambda row: bool(row.get("Reported RN Staffing Hours per Resident per Day") or row.get("Reported Total Nurse Staffing Hours per Resident per Day")),
            "Real staffing-related provider row",
        )
    elif case.test_kind == "cms_ownership":
        result = test_cms_dataset(
            "4pq5-n9py",
            "Ownership fields in provider dataset",
            ["CMS Certification Number (CCN)", "Ownership Type"],
            lambda row: bool(row.get("Ownership Type")),
            "Real ownership field row",
        )
    elif case.test_kind == "cms_penalties":
        result = test_cms_dataset(
            "4pq5-n9py",
            "Penalty/fine-related fields in provider dataset",
            ["CMS Certification Number (CCN)", "Number of Fines", "Total Amount of Fines in Dollars"],
            lambda row: bool(row.get("Number of Fines") not in {None, ""}) and bool(row.get("Total Amount of Fines in Dollars") not in {None, ""}),
            "Real penalties/fines field row",
        )
    elif case.test_kind == "html":
        result = test_html_source(case.endpoint, useful_patterns=case.metadata.get("useful_patterns", []), useless_patterns=case.metadata.get("useless_patterns", []), sample_desc=f"{case.source_name} content")
    elif case.test_kind == "official_site":
        patterns = ["skilled nursing", "rehabilitation", "therapy", "care"]
        result = test_html_source(case.endpoint, useful_patterns=patterns, useless_patterns=["access denied", "attention required"], sample_desc=f"Official facility content for {case.metadata.get('facility_name', 'facility')}")
    elif case.test_kind == "seniorly":
        result = test_html_source(case.endpoint, useful_patterns=case.metadata.get("useful_patterns", []), useless_patterns=case.metadata.get("useless_patterns", []), sample_desc="Seniorly profile content")
    elif case.test_kind == "google_reviews":
        result = test_google_reviews()
    elif case.test_kind == "auth_optional_site":
        result = test_auth_optional_site(case.endpoint, case.metadata.get("auth", []), case.metadata.get("label", case.source_name))
    else:
        result = build_result(False, False, "NOT_TESTABLE_WITH_CURRENT_CONFIG", case.endpoint, None, f"Unsupported test kind: {case.test_kind}", 0.0, f"Unsupported test kind: {case.test_kind}", None)

    changed = "YES" if previous_status != "UNKNOWN" and previous_status != result["final_status"] else "NO"
    access_restored = previous_status in {"SOURCE_GEO_BLOCKED_OR_SUSPECTED", "SOURCE_ACCESS_FAILED", "SOURCE_RATE_LIMITED", "ACCESS_DENIED", "TIMEOUT"} and result["final_status"] == "CONNECTED_REAL_DATA"

    action_required = "YES"
    if result["final_status"] == "CONNECTED_REAL_DATA" and case.connector_implemented == "YES" and case.connector_functional == "YES":
        action_required = "NO"
    elif result["final_status"] == "CONNECTED_REAL_DATA" and case.connector_functional in {"NO", "PARTIAL"}:
        action_required = "YES"
    elif result["final_status"] == "NOT_TESTABLE_WITH_CURRENT_CONFIG":
        action_required = "YES"

    enriched = {
        "source_name": case.source_name,
        "organization": case.organization,
        "category": case.category,
        "criticality": case.criticality,
        "exact_endpoint_tested": result["tested_endpoint"],
        "access_method": case.access_method,
        "test_timestamp_utc": started_at,
        "http_status": result["http_status"],
        "response_content_evidence": result["response_content_evidence"],
        "useful_real_data_retrieved": result["real_data_retrieval"],
        "example_dataset_or_record_type": result["example_record_type"],
        "duration_seconds": result["duration_seconds"],
        "final_status": result["final_status"],
        "exact_error_or_block_reason": result["error_or_block_reason"],
        "network_access": result["network_access"],
        "real_data_retrieval": result["real_data_retrieval"],
        "optime_connector_implemented": case.connector_implemented,
        "connector_currently_functional": case.connector_functional,
        "optime_ingestion_currently_uses_source": case.used_by_optime,
        "previous_status": previous_status,
        "changed_from_previous": changed,
        "access_restored_under_current_network_environment": "YES" if access_restored else "NO",
        "action_required": action_required,
        "action_required_hint": case.action_required_hint,
    }

    print(f"RESULT: {enriched['final_status']}")
    print(f"HTTP: {enriched['http_status']}")
    print(f"RECORDS/CONTENT VERIFIED: {enriched['useful_real_data_retrieved']}")
    print(f"DURATION: {enriched['duration_seconds']}s")
    return enriched


def sort_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status_rank = {
        "GEO_BLOCKED_OR_SUSPECTED": 0,
        "ACCESS_DENIED": 0,
        "BOT_CHALLENGE": 0,
        "DNS_OR_NETWORK_FAILURE": 0,
        "TIMEOUT": 0,
        "ENDPOINT_BROKEN": 0,
        "RATE_LIMITED": 1,
        "AUTH_REQUIRED": 2,
        "NOT_TESTABLE_WITH_CURRENT_CONFIG": 3,
        "CONNECTED_NO_USEFUL_DATA": 4,
        "CONNECTED_REAL_DATA": 5,
    }
    critical_rank = {"CRITICAL": 0, "SECONDARY": 1}
    return sorted(results, key=lambda row: (critical_rank.get(row["criticality"], 9), status_rank.get(row["final_status"], 9), row["source_name"]))


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {status: 0 for status in ALLOWED_STATUSES}
    for row in results:
        counts[row["final_status"]] += 1
    tested = sum(1 for row in results if row["final_status"] != "NOT_TESTABLE_WITH_CURRENT_CONFIG")
    blocked_count = counts["GEO_BLOCKED_OR_SUSPECTED"] + counts["ACCESS_DENIED"] + counts["BOT_CHALLENGE"] + counts["DNS_OR_NETWORK_FAILURE"]

    critical_available = [row["source_name"] for row in results if row["criticality"] == "CRITICAL" and row["final_status"] == "CONNECTED_REAL_DATA"]
    critical_unavailable = [row["source_name"] for row in results if row["criticality"] == "CRITICAL" and row["final_status"] != "CONNECTED_REAL_DATA"]
    restored = [row["source_name"] for row in results if row["access_restored_under_current_network_environment"] == "YES"]
    still_blocked = [row["source_name"] for row in results if row["final_status"] in {"GEO_BLOCKED_OR_SUSPECTED", "ACCESS_DENIED", "BOT_CHALLENGE", "DNS_OR_NETWORK_FAILURE", "TIMEOUT"}]
    connector_missing_broken = [row["source_name"] for row in results if row["network_access"] == "YES" and row["real_data_retrieval"] == "YES" and row["connector_currently_functional"] in {"NO", "PARTIAL"}]

    def area_status(names: list[str]) -> str:
        subset = [row for row in results if row["source_name"] in names]
        if not subset:
            return "NO"
        if all(row["final_status"] == "CONNECTED_REAL_DATA" for row in subset):
            return "YES"
        if any(row["final_status"] == "CONNECTED_REAL_DATA" for row in subset):
            return "PARTIAL"
        return "NO"

    cms_names = [
        "CMS Provider Dataset (4pq5-n9py)",
        "CMS Inspection Dataset (r5ix-sfxw)",
        "CMS Quality Dataset (djen-97ju)",
        "CMS Survey Dataset (svdt-c123)",
        "CMS Staffing/PBJ Fields",
        "CMS Ownership Fields",
        "CMS Penalties/Fines Fields",
        "Medicare Care Compare",
    ]
    florida_names = ["Florida AHCA Portal", "Florida AHCA License Profile Sample"]
    facility_names = [row["source_name"] for row in results if row["category"] == "FACILITY_PRIMARY"]
    review_names = [
        "Google Reviews / Maps",
        "Yelp",
        "Facebook",
        "Instagram",
        "LinkedIn",
        "Indeed",
        "Glassdoor",
        "Caring.com",
        "A Place for Mom",
        "SeniorAdvisor",
        "Seniorly Sample Profile",
    ]
    news_names = ["Local News (Google News)", "Press Releases (PRNewswire)"]
    legal_names = ["Public Court Records (CourtListener)"]

    readiness = "READY"
    if critical_unavailable:
        readiness = "PARTIALLY_READY"
    if any(name in critical_unavailable for name in ["CMS Provider Dataset (4pq5-n9py)", "CMS Inspection Dataset (r5ix-sfxw)", "CMS Quality Dataset (djen-97ju)"]):
        readiness = "NOT_READY"

    return {
        "total_sources_discovered": len(results),
        "total_sources_tested": tested,
        "connected_real_data": counts["CONNECTED_REAL_DATA"],
        "connected_no_useful_data": counts["CONNECTED_NO_USEFUL_DATA"],
        "blocked": blocked_count,
        "rate_limited": counts["RATE_LIMITED"],
        "auth_required": counts["AUTH_REQUIRED"],
        "broken": counts["ENDPOINT_BROKEN"],
        "timeout": counts["TIMEOUT"],
        "not_testable": counts["NOT_TESTABLE_WITH_CURRENT_CONFIG"],
        "counts_by_status": counts,
        "critical_sources_available": critical_available,
        "critical_sources_unavailable": critical_unavailable,
        "previously_blocked_now_accessible": restored,
        "still_geo_network_blocked": still_blocked,
        "accessible_but_connector_missing_broken": connector_missing_broken,
        "cms_medicare": area_status(cms_names),
        "cms_real_facility_data": "YES" if any(row["source_name"] == "CMS Provider Dataset (4pq5-n9py)" and row["final_status"] == "CONNECTED_REAL_DATA" for row in results) else "NO",
        "inspections_deficiencies": area_status(["CMS Inspection Dataset (r5ix-sfxw)"]),
        "staffing_pbj": area_status(["CMS Staffing/PBJ Fields"]),
        "penalties_fines": area_status(["CMS Penalties/Fines Fields"]),
        "ownership": area_status(["CMS Ownership Fields"]),
        "florida_ahca": area_status(florida_names),
        "facility_websites": area_status(facility_names),
        "reviews_reputation": area_status(review_names),
        "news_public_web": area_status(news_names),
        "legal_regulatory": area_status(legal_names),
        "large_scale_enrichment_readiness": readiness,
    }


def build_fix_queue(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    for row in results:
        if row["action_required"] != "YES":
            continue
        priority = "P0" if row["criticality"] == "CRITICAL" and row["final_status"] != "CONNECTED_REAL_DATA" else "P1" if row["criticality"] == "CRITICAL" else "P2"
        queue.append(
            {
                "priority": priority,
                "source": row["source_name"],
                "problem": row["final_status"],
                "why": row["exact_error_or_block_reason"],
                "action": row["action_required_hint"],
            }
        )
    order = {"P0": 0, "P1": 1, "P2": 2}
    return sorted(queue, key=lambda item: (order[item["priority"]], item["source"]))


def write_reports(results: list[dict[str, Any]], summary: dict[str, Any], queue: list[dict[str, str]]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": now_iso(),
        "summary": summary,
        "results": results,
        "critical_fix_queue": queue,
    }
    AUDIT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Full Source Connectivity Audit",
        "",
        f"- Generated: {payload['generated_at_utc']}",
        f"- Total sources discovered: {summary['total_sources_discovered']}",
        f"- Total sources tested: {summary['total_sources_tested']}",
        f"- Connected with verified real data: {summary['connected_real_data']}",
        "",
        "## Executive Summary",
        "",
        f"- CMS/Medicare: {summary['cms_medicare']}",
        f"- CMS real facility data: {summary['cms_real_facility_data']}",
        f"- Inspections/Deficiencies: {summary['inspections_deficiencies']}",
        f"- Staffing/PBJ: {summary['staffing_pbj']}",
        f"- Penalties/Fines: {summary['penalties_fines']}",
        f"- Ownership: {summary['ownership']}",
        f"- Florida AHCA: {summary['florida_ahca']}",
        f"- Facility Websites: {summary['facility_websites']}",
        f"- Reviews/Reputation: {summary['reviews_reputation']}",
        f"- News/Public Web: {summary['news_public_web']}",
        f"- Legal/Regulatory: {summary['legal_regulatory']}",
        f"- Large-scale enrichment readiness: {summary['large_scale_enrichment_readiness']}",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in summary["counts_by_status"].items():
        lines.append(f"- {status}: {count}")

    lines += ["", "## Source Results", "", "| Source | Category | Network | Real Data | Connector | Functional | Status | Previous | Action Required |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in results:
        lines.append(
            f"| {row['source_name']} | {row['category']} | {row['network_access']} | {row['real_data_retrieval']} | {row['optime_connector_implemented']} | {row['connector_currently_functional']} | {row['final_status']} | {row['previous_status']} | {row['action_required']} |"
        )

    lines += ["", "## Critical Fix Queue", ""]
    for item in queue:
        lines.append(f"- {item['priority']} | {item['source']} | {item['problem']} | {item['why']} | {item['action']}")

    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    matrix = [
        "# Source Connectivity Matrix",
        "",
        "| Source | Category | Network | Real Data | Connector | Current Status | Previous Status | Action Required |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in results:
        matrix.append(
            f"| {row['source_name']} | {row['category']} | {row['network_access']} | {row['real_data_retrieval']} | {row['optime_connector_implemented']} / {row['connector_currently_functional']} | {row['final_status']} | {row['previous_status']} | {row['action_required']} |"
        )
    MATRIX_MD.write_text("\n".join(matrix) + "\n", encoding="utf-8")


def main() -> None:
    inventory = make_inventory()
    previous_map = load_previous_status_map()
    results: list[dict[str, Any]] = []

    total = len(inventory)
    for index, case in enumerate(inventory, start=1):
        print(f"[SOURCE {index:02d}/{total:02d}] Testing {case.source_name}...")
        row = evaluate_source(case, previous_map)
        results.append(row)

    results = sort_results(results)
    summary = summarize(results)
    queue = build_fix_queue(results)

    if summary["total_sources_tested"] + summary["not_testable"] != summary["total_sources_discovered"]:
        raise RuntimeError("Source accounting mismatch: tested + not_testable != total discovered")

    write_reports(results, summary, queue)
    print(json.dumps({"summary": summary, "audit_md": str(AUDIT_MD), "audit_json": str(AUDIT_JSON), "matrix_md": str(MATRIX_MD)}, indent=2))


if __name__ == "__main__":
    main()
