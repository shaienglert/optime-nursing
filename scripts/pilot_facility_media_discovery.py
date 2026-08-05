#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import ssl
import base64
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, quote_plus, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.facility_media_resolution import (  # type: ignore  # noqa: E402
    evaluate_identity_candidate,
    extract_candidate_images,
    resolve_best_identity,
    select_primary_image,
)

CANONICAL_PATH = REPO_ROOT / "database" / "florida_facility_universe_canonical.json"
INVENTORY_PATH = REPO_ROOT / "database" / "florida_senior_living_inventory.json"
REGISTRY_PATH = REPO_ROOT / "database" / "facility_media_registry.json"
PILOT_REPORT_PATH = REPO_ROOT / "reports" / "facility_media_pilot_top20_miami.json"
GROUND_TRUTH_FIXTURE_PATH = REPO_ROOT / "database" / "facility_media_identity_regression_fixtures.json"
GROUND_TRUTH_REPORT_PATH = REPO_ROOT / "reports" / "facility_media_identity_regression_5.json"

DECISION_ENGINE_URL = "http://127.0.0.1:8000/decision-engine/recommendations"
FACILITIES_URL = "http://127.0.0.1:8000/facilities"

REQUEST_TIMEOUT = 12
DECISION_ENGINE_TIMEOUT = 30
USER_AGENT = "OPTIME-MediaPilot/1.0 (+https://optime.ai)"
REGRESSION_CANDIDATE_LIMIT = 40
TOP20_CANDIDATE_LIMIT = 8

GENERIC_DOMAIN_BLOCKLIST = {
    "census.gov",
    "data.cms.gov",
    "medicare.gov",
    "cms.gov",
    "ahca.myflorida.com",
    "quality.healthfinder.fl.gov",
    "aplaceformom.com",
    "caring.com",
    "seniorly.com",
    "seniorhousingnet.com",
    "assistedliving.org",
    "nursinghomes.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "bing.com",
    "duckduckgo.com",
}

NAME_STOPWORDS = {
    "the",
    "and",
    "at",
    "of",
    "center",
    "centre",
    "health",
    "care",
    "rehabilitation",
    "rehab",
    "nursing",
    "facility",
    "inc",
    "llc",
    "community",
    "communities",
    "home",
    "homes",
    "senior",
    "living",
    "skilled",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return normalize_spaces(lowered)


def norm_phone_digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", value or "")


def token_set(value: str) -> set[str]:
    return {
        token
        for token in normalize_text(value).split()
        if len(token) >= 3 and token not in NAME_STOPWORDS
    }


def core_name_tokens(value: str) -> List[str]:
    return [
        token
        for token in normalize_text(value).split()
        if len(token) >= 3 and token not in NAME_STOPWORDS and token not in {"health", "care", "center", "rehabilitation", "rehab", "nursing"}
    ]


def domain_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        return host[4:]
    return host


def is_blocked_domain(url: str) -> bool:
    domain = domain_of(url)
    for blocked in GENERIC_DOMAIN_BLOCKLIST:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True
    return False


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def fetch_url(url: str, accept: str = "text/html,*/*") -> Tuple[int, Dict[str, str], str]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        ssl_ctx = ssl.create_default_context()
        with urlopen(req, timeout=REQUEST_TIMEOUT, context=ssl_ctx) as response:
            status = int(getattr(response, "status", 200))
            headers = {k.lower(): v for k, v in response.headers.items()}
            content_type = headers.get("content-type", "")
            body_bytes = response.read()
    except URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            insecure_ctx = ssl._create_unverified_context()
            with urlopen(req, timeout=REQUEST_TIMEOUT, context=insecure_ctx) as response:
                status = int(getattr(response, "status", 200))
                headers = {k.lower(): v for k, v in response.headers.items()}
                content_type = headers.get("content-type", "")
                body_bytes = response.read()
        else:
            raise
    encoding_match = re.search(r"charset=([^;\s]+)", content_type, flags=re.I)
    encoding = encoding_match.group(1) if encoding_match else "utf-8"
    try:
        body = body_bytes.decode(encoding, errors="replace")
    except LookupError:
        body = body_bytes.decode("utf-8", errors="replace")
    return status, headers, body


def check_image_url(image_url: str) -> Tuple[bool, str, int]:
    try:
        req = Request(
            image_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "image/*,*/*;q=0.8",
                "Range": "bytes=0-0",
            },
        )
        ssl_ctx = ssl.create_default_context()
        with urlopen(req, timeout=REQUEST_TIMEOUT, context=ssl_ctx) as response:
            status = int(getattr(response, "status", 200))
            headers = {k.lower(): v for k, v in response.headers.items()}
            content_type = headers.get("content-type", "")
        if status >= 400:
            return False, "HTTP_ERROR", status
        if not content_type.lower().startswith("image/"):
            return False, "NOT_IMAGE", status
        return True, "OK", status
    except Exception as exc:  # pragma: no cover - network path
        text = str(exc).lower()
        if "403" in text:
            return False, "HOTLINK_BLOCKED", 403
        if "404" in text:
            return False, "HTTP_ERROR", 404
        return False, "FETCH_FAILED", 0


@dataclass
class FacilitySeed:
    canonical_facility_id: str
    facility_name: str
    city: str
    state: str
    address: str
    phone: str
    cms_ccn: str


def build_cms_to_canonical(canonical_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for item in canonical_payload.get("records", []):
        if not isinstance(item, dict):
            continue
        canonical_id = str(item.get("canonical_id") or "").strip()
        cms_ccn = str((item.get("source_identity_ids") or {}).get("cms_ccn") or "").strip()
        if canonical_id and cms_ccn:
            mapping[cms_ccn] = item
    return mapping


def get_top20_miami_seeds(cms_to_canonical: Dict[str, Dict[str, Any]]) -> List[FacilitySeed]:
    questionnaire_state = {
        "relationship": "Dad",
        "ageGroup": "80-84",
        "assistanceLevel": "24/7 support required",
        "memoryStatus": "No",
        "budget": 7000,
        "distanceFromFamily": "Balanced location",
        "notes": "Father, age 82, Miami, Florida, recent stroke, limited mobility, needs 24/7 nursing support, physical therapy, occupational therapy, speech therapy where appropriate, help with bathing, help with dressing, medication management, transfer assistance, mentally alert, no dementia. Goal: regain as much independence as possible.",
        "humanIntelligenceV2": {},
    }

    decision_payload = {
        "questionnaire_state": questionnaire_state,
        "natural_language_query": questionnaire_state["notes"],
        "limit": 50,
    }

    decision_result: Dict[str, Any] = {"results": []}
    decision_json = json.dumps(decision_payload).encode("utf-8")
    req = Request(
        DECISION_ENGINE_URL,
        data=decision_json,
        method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"},
    )
    ssl_ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=DECISION_ENGINE_TIMEOUT, context=ssl_ctx) as response:
            decision_result = json.loads(response.read().decode("utf-8"))
    except Exception:
        decision_result = {"results": []}

    picked: List[FacilitySeed] = []
    seen: set[str] = set()

    for result in decision_result.get("results", []):
        city = str(result.get("city") or "")
        if "miami" not in city.lower():
            continue
        canonical_id = str(result.get("canonical_facility_id") or "").strip()
        if not canonical_id or canonical_id in seen:
            continue
        cms_ccn = str((result.get("source_identity_ids") or {}).get("cms_ccn") or "").strip()
        canonical_row = cms_to_canonical.get(cms_ccn)
        address = str((canonical_row or {}).get("address") or "")
        phone = str((canonical_row or {}).get("phone") or "")
        picked.append(
            FacilitySeed(
                canonical_facility_id=canonical_id,
                facility_name=str(result.get("facility_name") or canonical_id),
                city=city,
                state=str(result.get("state") or "FL"),
                address=address,
                phone=phone,
                cms_ccn=cms_ccn,
            )
        )
        seen.add(canonical_id)
        if len(picked) == 20:
            return picked

    facilities_req = Request(f"{FACILITIES_URL}?q={quote_plus('miami')}", headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(facilities_req, timeout=REQUEST_TIMEOUT, context=ssl_ctx) as response:
        miami_list = json.loads(response.read().decode("utf-8"))

    for item in miami_list:
        cms_ccn = str(item.get("cms_id") or "").strip()
        canonical_row = cms_to_canonical.get(cms_ccn)
        if not canonical_row:
            continue
        canonical_id = str(canonical_row.get("canonical_id") or "").strip()
        if not canonical_id or canonical_id in seen:
            continue
        picked.append(
            FacilitySeed(
                canonical_facility_id=canonical_id,
                facility_name=str(item.get("name") or canonical_id),
                city=str(item.get("city") or ""),
                state=str(item.get("state") or "FL"),
                address=str(item.get("address") or str(canonical_row.get("address") or "")),
                phone=str(item.get("phone") or str(canonical_row.get("phone") or "")),
                cms_ccn=cms_ccn,
            )
        )
        seen.add(canonical_id)
        if len(picked) == 20:
            break

    return picked


def extract_urls_from_duckduckgo(query: str) -> List[str]:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        status, _, body = fetch_url(url)
    except Exception:
        return []
    if status >= 400:
        return []

    links: List[str] = []
    for href in re.findall(r'href="([^"]+)"', body, flags=re.I):
        if "/l/?" not in href:
            continue
        parsed = urlparse(href)
        query_args = parse_qs(parsed.query)
        target = (query_args.get("uddg") or [""])[0]
        if target.startswith("http"):
            links.append(unescape(target))
    deduped: List[str] = []
    seen: set[str] = set()
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        deduped.append(link)
        if len(deduped) >= 6:
            break
    return deduped


def extract_urls_from_bing(query: str) -> List[str]:
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    try:
        status, _, body = fetch_url(url)
    except Exception:
        return []
    if status >= 400:
        return []

    def decode_bing_target(raw_link: str) -> str:
        link = unescape(raw_link.strip())
        parsed = urlparse(link)
        if not link.startswith("http"):
            return ""
        if domain_of(link).endswith("bing.com"):
            query_args = parse_qs(parsed.query)
            direct = (query_args.get("url") or [""])[0]
            if direct.startswith("http"):
                return unescape(direct)
            u_value = (query_args.get("u") or [""])[0]
            if u_value.startswith("a1") and len(u_value) > 2:
                encoded = u_value[2:]
                padding = "=" * ((4 - len(encoded) % 4) % 4)
                try:
                    decoded = base64.urlsafe_b64decode((encoded + padding).encode("ascii")).decode("utf-8", errors="replace")
                    if decoded.startswith("http"):
                        return decoded
                except Exception:
                    return ""
            return ""
        return link

    links: List[str] = []
    result_blocks = re.findall(
        r"<li[^>]+class=['\"][^'\"]*\bb_algo\b[^'\"]*['\"][^>]*>(.*?)</li>",
        body,
        flags=re.I | re.S,
    )
    for block in result_blocks:
        match = re.search(r"<h2[^>]*>.*?<a[^>]+href=['\"]([^'\"]+)['\"]", block, flags=re.I | re.S)
        if not match:
            continue
        target = decode_bing_target(match.group(1))
        if target.startswith("http"):
            links.append(target)
    deduped: List[str] = []
    seen: set[str] = set()
    for raw_link in links:
        link = raw_link
        if not link.startswith("http"):
            continue
        if link in seen:
            continue
        seen.add(link)
        deduped.append(unescape(link))
        if len(deduped) >= 20:
            break
    return deduped


class _YahooOrganicLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_results = False
        self.results_ol_depth = 0
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "ol" and "searchCenterMiddle" in attributes.get("class", ""):
            self.in_results = True
            self.results_ol_depth = 1
            return
        if self.in_results and tag == "ol":
            self.results_ol_depth += 1
        if self.in_results and tag == "a":
            href = unescape(attributes.get("href", "")).strip()
            if href.startswith("http"):
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self.in_results and tag == "ol":
            self.results_ol_depth -= 1
            if self.results_ol_depth <= 0:
                self.in_results = False


def extract_urls_from_yahoo(query: str) -> List[str]:
    url = f"https://search.yahoo.com/search?p={quote_plus(query)}"
    try:
        status, _, body = fetch_url(url)
    except Exception:
        return []
    if status >= 400:
        return []

    parser = _YahooOrganicLinkParser()
    parser.feed(body)
    deduped: List[str] = []
    seen: set[str] = set()
    for link in parser.links:
        domain = domain_of(link)
        if not domain or domain.endswith("search.yahoo.com") or link in seen:
            continue
        seen.add(link)
        deduped.append(link)
        if len(deduped) >= 20:
            break
    return deduped


def normalize_candidate_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def normalize_url_for_match(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parsed.path or "/").rstrip("/")
    return f"{host}{path}"


def parse_inventory_record(inventory_payload: Dict[str, Any], cms_ccn: str) -> Optional[Dict[str, Any]]:
    for row in inventory_payload.get("records", []):
        if str(row.get("cms_certification_number") or "").strip() == cms_ccn:
            return row
    return None


def build_domain_guess_candidates(seed: FacilitySeed) -> List[Tuple[str, str, bool]]:
    tokens = core_name_tokens(seed.facility_name)
    stems: List[str] = []
    if not tokens:
        return []

    joined_all = "".join(tokens)
    stems.append(f"{joined_all}rehab")
    stems.append(f"{joined_all}healthcare")
    stems.append(f"{joined_all}carecenter")
    stems.append(joined_all)

    first = tokens[0]
    stems.append(f"{first}hrc")
    stems.append(f"{first}rehab")
    stems.append(f"{first}carecenter")

    if len(tokens) >= 2:
        first_two = "".join(tokens[:2])
        acronym = "".join(token[0] for token in tokens[:2])
        stems.append(f"{acronym}rehab")
        stems.append(f"{acronym}hrc")
        stems.append(f"{first_two}rehab")
        stems.append(f"{first_two}healthcare")
        stems.append(f"{first_two}carecenter")
        stems.append(f"{first_two}hrc")

    deduped_stems: List[str] = []
    seen_stems: set[str] = set()
    for stem in stems:
        normalized = re.sub(r"[^a-z0-9]", "", stem.lower())
        if len(normalized) < 5 or normalized in seen_stems:
            continue
        seen_stems.add(normalized)
        deduped_stems.append(normalized)

    candidates: List[Tuple[str, str, bool]] = []
    for stem in deduped_stems:
        for template in [
            f"https://www.{stem}.com/",
            f"https://{stem}.com/",
            f"https://www.{stem}.net/",
            f"http://www.{stem}.net/",
        ]:
            candidates.append((template, "DIRECT_DOMAIN_GUESS", True))
    return candidates


def score_candidate_page(seed: FacilitySeed, page_text: str, candidate_domain_hint: bool) -> float:
    text = normalize_text(page_text)
    score = 0.0

    name_tokens = token_set(seed.facility_name)
    if name_tokens:
        matched = sum(1 for token in name_tokens if token in text)
        overlap = matched / max(len(name_tokens), 1)
        if overlap >= 0.8:
            score += 0.45
        elif overlap >= 0.6:
            score += 0.35
        elif overlap >= 0.45:
            score += 0.2

    if normalize_text(seed.city) and normalize_text(seed.city) in text:
        score += 0.12

    phone_digits = norm_phone_digits(seed.phone)
    if len(phone_digits) >= 7 and phone_digits[-7:] in re.sub(r"\D", "", page_text):
        score += 0.2

    address_tokens = normalize_text(seed.address).split()
    street_number = address_tokens[0] if address_tokens else ""
    if street_number and street_number in text:
        score += 0.1

    if len(address_tokens) >= 2 and address_tokens[1] in text:
        score += 0.08

    if candidate_domain_hint:
        score += 0.12

    return min(score, 1.0)


def load_ground_truth_fixtures() -> List[Dict[str, Any]]:
    payload = load_json(GROUND_TRUTH_FIXTURE_PATH)
    fixtures = payload.get("fixtures") or []
    return [item for item in fixtures if isinstance(item, dict)]


def build_seed_from_fixture(item: Dict[str, Any]) -> FacilitySeed:
    return FacilitySeed(
        canonical_facility_id=str(item.get("canonical_facility_id") or ""),
        facility_name=str(item.get("facility_name") or ""),
        city=str(item.get("city") or ""),
        state=str(item.get("state") or "FL"),
        address=str(item.get("address") or ""),
        phone=str(item.get("phone") or ""),
        cms_ccn=str(item.get("cms_ccn") or ""),
    )


def build_name_variants(seed: FacilitySeed) -> List[str]:
    base = seed.facility_name
    variants = {
        base,
        base.replace("HEALTHCARE", "HEALTH"),
        base.replace("HEALTH", "HEALTHCARE"),
        base.replace("REHAB", "REHABILITATION"),
        base.replace("REHABILITATION", "REHAB"),
    }
    return [item for item in variants if item and item != base]


def search_domain_has_identity_affinity(seed: FacilitySeed, inventory_row: Optional[Dict[str, Any]], candidate_url: str) -> bool:
    domain_labels = [label for label in domain_of(candidate_url).split(".") if label]
    host_root = domain_labels[-2] if len(domain_labels) >= 2 else (domain_labels[0] if domain_labels else "")
    if not host_root:
        return False
    compact_host = re.sub(r"[^a-z0-9]", "", host_root.lower())
    facility_tokens = core_name_tokens(seed.facility_name)
    operator_name = str((inventory_row or {}).get("parent_company") or (inventory_row or {}).get("operator_name") or "")
    operator_tokens = core_name_tokens(operator_name)
    identity_tokens = [token for token in [*facility_tokens, *operator_tokens] if len(token) >= 4]
    if any(token in compact_host for token in identity_tokens):
        return True
    if len(facility_tokens) >= 2:
        acronym = "".join(token[0] for token in facility_tokens[:2])
        if len(acronym) >= 2 and compact_host.startswith(acronym):
            return True
    return False


def extract_same_domain_pages(page_url: str, html: str) -> List[str]:
    parsed = urlparse(page_url)
    base_domain = domain_of(page_url)
    results: List[str] = []
    seen: set[str] = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        absolute = urljoin(page_url, href)
        if domain_of(absolute) != base_domain:
            continue
        path = (urlparse(absolute).path or "").lower()
        if not any(token in path for token in ["gallery", "photo", "photos", "activity", "activities", "about", "contact"]):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        results.append(absolute)
        if len(results) >= 4:
            break
    if not results and parsed.scheme and parsed.netloc:
        for suffix in ["/photo-gallery/", "/gallery/", "/photos/", "/activities/"]:
            guess = f"{parsed.scheme}://{parsed.netloc}{suffix}"
            if guess not in seen:
                results.append(guess)
                if len(results) >= 4:
                    break
    return results


def collect_candidates(
    seed: FacilitySeed,
    inventory_row: Optional[Dict[str, Any]],
    *,
    max_candidates: int,
) -> List[Tuple[str, str, bool]]:
    structured_candidates: List[Tuple[str, str, bool]] = []
    search_candidates: List[Tuple[str, str, bool]] = []

    if inventory_row:
        website = normalize_candidate_url(str(inventory_row.get("website") or ""))
        if website and not is_blocked_domain(website):
            structured_candidates.append((website, "STRUCTURED_WEBSITE", True))

        for source_url in inventory_row.get("source_urls") or []:
            candidate = normalize_candidate_url(str(source_url or ""))
            if not candidate or is_blocked_domain(candidate):
                continue
            structured_candidates.append((candidate, "STRUCTURED_SOURCE_URL", False))

    operator_name = str((inventory_row or {}).get("parent_company") or (inventory_row or {}).get("operator_name") or "").strip()
    search_queries = [
        f'"{seed.phone}"' if seed.phone else "",
        f'"{seed.facility_name}" "{seed.address}"',
        f'"{seed.facility_name}" "{seed.city}"',
        f'"{seed.facility_name}" official',
        f'"{operator_name}" "{seed.city}"' if operator_name else "",
    ]

    search_budget = max(1, max_candidates // 2)
    seen_search_domains: set[str] = set()
    for search_query in (query for query in search_queries if query):
        query_results = [
            *extract_urls_from_yahoo(search_query),
            *extract_urls_from_duckduckgo(search_query),
            *extract_urls_from_bing(search_query),
        ]
        for result_url in query_results:
            candidate = normalize_candidate_url(result_url)
            if not candidate or is_blocked_domain(candidate):
                continue
            if not search_domain_has_identity_affinity(seed, inventory_row, candidate):
                continue
            candidate_domain = domain_of(candidate)
            if not candidate_domain or candidate_domain in seen_search_domains:
                continue
            seen_search_domains.add(candidate_domain)
            search_candidates.append((candidate, "SEARCH_DISCOVERY", False))
            break
        if len(search_candidates) >= search_budget:
            break

    candidates = [
        *structured_candidates,
        *search_candidates,
        *build_domain_guess_candidates(seed),
    ]

    deduped: List[Tuple[str, str, bool]] = []
    seen: set[str] = set()
    for url, source_type, hint in candidates:
        if url in seen:
            continue
        seen.add(url)
        deduped.append((url, source_type, hint))
    return deduped[:max_candidates]


def resolve_official_identity(
    seed: FacilitySeed,
    inventory_row: Optional[Dict[str, Any]],
    *,
    max_candidates: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    checked_sources: List[Dict[str, Any]] = []
    evaluated: List[Dict[str, Any]] = []
    name_variants = build_name_variants(seed)
    operator_name = str((inventory_row or {}).get("operator_name") or "")

    for candidate_url, source_type, _ in collect_candidates(seed, inventory_row, max_candidates=max_candidates):
        try:
            status, _, body = fetch_url(candidate_url)
            checked_sources.append({"url": candidate_url, "source_type": source_type, "status": status})
            if status >= 400:
                continue
            evaluation = evaluate_identity_candidate(
                facility_name=seed.facility_name,
                name_variants=name_variants,
                address=seed.address,
                city=seed.city,
                state=seed.state,
                phone=seed.phone,
                cms_ccn=seed.cms_ccn,
                operator_name=operator_name,
                candidate_url=candidate_url,
                page_text=body,
                source_type=source_type,
            )
            evaluated.append(evaluation)
        except Exception:
            checked_sources.append({"url": candidate_url, "source_type": source_type, "status": "FETCH_FAILED"})

    return resolve_best_identity(evaluated), checked_sources


def discover_images_for_verified_identity(seed: FacilitySeed, official_page_url: str) -> Dict[str, Any]:
    try:
        _, _, body = fetch_url(official_page_url)
    except Exception:
        return {
            "primary_image_url": "",
            "image_source_url": official_page_url,
            "image_source_type": "",
            "image_status": "UNKNOWN",
            "verified_facility_specific": False,
            "image_match_evidence": {},
            "evaluated_image_count": 0,
        }

    images = extract_candidate_images(official_page_url, body)
    for child_url in extract_same_domain_pages(official_page_url, body):
        try:
            _, _, child_body = fetch_url(child_url)
            images.extend(extract_candidate_images(child_url, child_body))
        except Exception:
            continue

    return select_primary_image(images, facility_name=seed.facility_name, official_page_url=official_page_url)


def discover_media_for_facility(
    seed: FacilitySeed,
    inventory_row: Optional[Dict[str, Any]],
    *,
    max_candidates: int,
) -> Dict[str, Any]:
    identity_result, checked_sources = resolve_official_identity(seed, inventory_row, max_candidates=max_candidates)
    official_page_url = str(identity_result.get("official_facility_page_url") or "")

    image_result = {
        "primary_image_url": "",
        "image_source_url": "",
        "image_source_type": "",
        "image_status": "UNKNOWN",
        "verified_facility_specific": False,
        "image_match_evidence": {},
        "evaluated_image_count": 0,
    }
    if official_page_url and bool(identity_result.get("identity_verified")):
        image_result = discover_images_for_verified_identity(seed, official_page_url)

    image_probe_status = "NOT_CHECKED"
    image_probe_http_status = 0
    if image_result.get("primary_image_url"):
        ok, probe_status, http_status = check_image_url(str(image_result["primary_image_url"]))
        image_probe_status = "OK" if ok else probe_status
        image_probe_http_status = http_status

    overall_status = str(image_result.get("image_status") or "UNKNOWN")
    if overall_status == "UNKNOWN":
        overall_status = str(identity_result.get("identity_status") or "NOT_VERIFIED")

    return {
        "canonical_facility_id": seed.canonical_facility_id,
        "facility_name": seed.facility_name,
        "official_website_url": str(identity_result.get("official_website_url") or ""),
        "official_website": str(identity_result.get("official_website_url") or ""),
        "official_facility_page_url": official_page_url,
        "identity_status": str(identity_result.get("identity_status") or "NOT_VERIFIED"),
        "identity_verified": bool(identity_result.get("identity_verified")),
        "official_domain_verified": bool(identity_result.get("official_domain_verified")),
        "identity_match_evidence": identity_result.get("identity_match_evidence") or {},
        "primary_image_url": str(image_result.get("primary_image_url") or ""),
        "image_url": str(image_result.get("primary_image_url") or ""),
        "source_url": official_page_url if image_result.get("verified_facility_specific") else "",
        "image_source_url": str(image_result.get("image_source_url") or ""),
        "source_type": str(image_result.get("image_source_type") or ""),
        "image_source_type": str(image_result.get("image_source_type") or ""),
        "match_confidence": round(float((identity_result.get("identity_match_evidence") or {}).get("address_match_score") or 0.0), 3),
        "verified_facility_specific": bool(image_result.get("verified_facility_specific")),
        "verification_method": "official identity resolution before official-page image discovery",
        "last_verified": utc_now_iso(),
        "status": overall_status,
        "image_status": str(image_result.get("image_status") or "UNKNOWN"),
        "image_match_evidence": image_result.get("image_match_evidence") or {},
        "ambiguous_match": str(identity_result.get("identity_status") or "") == "AMBIGUOUS" or str(image_result.get("image_status") or "") == "AMBIGUOUS",
        "candidate_source_count": len(checked_sources),
        "checked_source_count": len(checked_sources),
        "checked_sources": checked_sources,
        "identity_candidates_checked": int(identity_result.get("identity_candidates_checked") or 0),
        "evaluated_image_count": int(image_result.get("evaluated_image_count") or 0),
        "image_probe_status": image_probe_status,
        "image_probe_http_status": image_probe_http_status,
    }


def merge_registry(existing_payload: Dict[str, Any], pilot_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    current_records = existing_payload.get("records") or []
    index: Dict[str, Dict[str, Any]] = {}
    for row in current_records:
        if isinstance(row, dict):
            key = str(row.get("canonical_facility_id") or "").strip()
            if key:
                index[key] = row

    for record in pilot_records:
        index[str(record["canonical_facility_id"])] = record

    merged = list(index.values())
    merged.sort(key=lambda item: str(item.get("canonical_facility_id") or ""))

    return {
        "generated_at_utc": utc_now_iso(),
        "status": "PILOT",
        "records": merged,
    }


def summarize(records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    records = list(records)
    identities_verified = sum(1 for row in records if row.get("identity_verified"))
    websites_matched = sum(1 for row in records if row.get("official_domain_verified"))
    verified_images = sum(1 for row in records if row.get("verified_facility_specific"))
    ambiguous = sum(1 for row in records if str(row.get("image_status") or "").upper() == "AMBIGUOUS")
    no_verified_image = sum(1 for row in records if str(row.get("image_status") or "").upper() == "UNKNOWN")
    wrong_domain_matches = sum(1 for row in records if str(row.get("identity_status") or "").upper() == "AMBIGUOUS")
    return {
        "facilities_checked": len(records),
        "official_identities_verified": identities_verified,
        "official_domains_found": websites_matched,
        "verified_facility_specific_images_found": verified_images,
        "ambiguous_images": ambiguous,
        "no_verified_image": no_verified_image,
        "wrong_domain_matches": wrong_domain_matches,
    }


def run_ground_truth_regression(cms_to_canonical: Dict[str, Dict[str, Any]], inventory_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    fixture_records: List[Dict[str, Any]] = []
    fixtures = load_ground_truth_fixtures()
    for index, fixture in enumerate(fixtures, start=1):
        seed = build_seed_from_fixture(fixture)
        print(f"REGRESSION {index}/{len(fixtures)}: {seed.canonical_facility_id} - {seed.facility_name}")
        inventory_row = parse_inventory_record(inventory_payload, seed.cms_ccn)
        record = discover_media_for_facility(seed, inventory_row, max_candidates=REGRESSION_CANDIDATE_LIMIT)
        expected_url = str(fixture.get("expected_official_url") or "").strip()
        actual_url = str(record.get("official_website_url") or "").strip()
        record["identity_regression_expected_url"] = expected_url
        record["identity_regression_pass"] = bool(actual_url and normalize_url_for_match(actual_url) == normalize_url_for_match(expected_url))
        record["expected_clear_official_image"] = bool(fixture.get("expected_clear_official_image"))
        fixture_records.append(record)
    return fixture_records


def main() -> None:
    canonical_payload = load_json(CANONICAL_PATH)
    inventory_payload = load_json(INVENTORY_PATH)

    cms_to_canonical = build_cms_to_canonical(canonical_payload)
    regression_records = run_ground_truth_regression(cms_to_canonical, inventory_payload)
    regression_summary = summarize(regression_records)
    regression_report = {
        "generated_at_utc": utc_now_iso(),
        "pilot": "ground_truth_regression_5",
        "summary": regression_summary,
        "records": regression_records,
    }
    save_json(GROUND_TRUTH_REPORT_PATH, regression_report)

    if regression_summary["official_identities_verified"] != 5 or regression_summary["wrong_domain_matches"] != 0:
        print("5-FACILITY IDENTITY REGRESSION FAILED")
        print("OFFICIAL IDENTITIES VERIFIED:", regression_summary["official_identities_verified"])
        print("WRONG-DOMAIN MATCHES:", regression_summary["wrong_domain_matches"])
        return

    top20 = get_top20_miami_seeds(cms_to_canonical)

    if len(top20) < 20:
        print(f"WARNING: pilot collected only {len(top20)} facilities (target 20)")

    pilot_records: List[Dict[str, Any]] = []
    for index, seed in enumerate(top20, start=1):
        print(f"TOP20 {index}/20: {seed.canonical_facility_id} - {seed.facility_name}")
        inventory_row = parse_inventory_record(inventory_payload, seed.cms_ccn)
        pilot_records.append(discover_media_for_facility(seed, inventory_row, max_candidates=TOP20_CANDIDATE_LIMIT))

    existing_registry = {"records": []}
    if REGISTRY_PATH.exists():
        existing_registry = load_json(REGISTRY_PATH)

    merged_registry = merge_registry(existing_registry, pilot_records)
    save_json(REGISTRY_PATH, merged_registry)

    summary = summarize(pilot_records)
    pilot_report = {
        "generated_at_utc": utc_now_iso(),
        "pilot": "top20_miami",
        "method": "identity-first official resolver, then official-page image discovery; decision-engine Miami-first, backfilled by /facilities?q=miami",
        "summary": summary,
        "records": pilot_records,
    }
    save_json(PILOT_REPORT_PATH, pilot_report)

    print("FACILITIES CHECKED:", summary["facilities_checked"])
    print("OFFICIAL IDENTITIES VERIFIED:", summary["official_identities_verified"])
    print("OFFICIAL DOMAINS FOUND:", summary["official_domains_found"])
    print("VERIFIED FACILITY-SPECIFIC IMAGES FOUND:", summary["verified_facility_specific_images_found"])
    print("AMBIGUOUS IMAGES:", summary["ambiguous_images"])
    print("NO VERIFIED IMAGE:", summary["no_verified_image"])
    print("WRONG-DOMAIN MATCHES:", summary["wrong_domain_matches"])


if __name__ == "__main__":
    main()
