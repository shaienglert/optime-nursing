from __future__ import annotations

import argparse
import json
import re
import time
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests


UNKNOWN = "UNKNOWN"
TIMEOUT = 12
USER_AGENT = "Mozilla/5.0 OPTIME Nursing PCA Research/1.0"
SKIP_DOMAINS = (
    "aplaceformom.com", "caring.com", "seniorly.com", "yelp.com", "facebook.com",
    "instagram.com", "linkedin.com", "youtube.com", "google.com", "mapquest.com",
    "yellowpages.com", "bbb.org", "indeed.com", "glassdoor.com",
)
GENERIC_NAME_TOKENS = {
    "home", "care", "health", "healthcare", "personal", "services", "service", "agency",
    "senior", "seniors", "llc", "inc", "the", "of", "and", "in", "at", "las", "vegas",
}
LANGUAGE_TOKENS = {
    "spanish": "Spanish", "hebrew": "Hebrew", "russian": "Russian", "tagalog": "Tagalog",
    "filipino": "Filipino", "mandarin": "Mandarin", "cantonese": "Cantonese",
    "french": "French", "arabic": "Arabic", "korean": "Korean", "vietnamese": "Vietnamese",
}


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def digits(value: Any) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def strip_html(body: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def agency_tokens(name: str) -> list[str]:
    return [
        token for token in norm(name).split()
        if len(token) >= 4 and token not in GENERIC_NAME_TOKENS
    ][:6]


def fetch(url: str) -> tuple[str, int, str]:
    response = requests.get(
        url,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
        allow_redirects=True,
    )
    return response.text or "", int(response.status_code), str(response.url)


def search_result_urls(query: str) -> list[tuple[str, str]]:
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    body, status, _ = fetch(url)
    if status != 200:
        return []
    matches = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        body,
        flags=re.I | re.S,
    )
    out: list[tuple[str, str]] = []
    for link, anchor in matches:
        decoded = unquote(parse_qs(urlparse(link).query).get("uddg", [link])[0])
        out.append((decoded, strip_html(anchor)))
    return out


def identity_matches(text: str, task: dict[str, Any]) -> bool:
    haystack = norm(text)
    tokens = agency_tokens(str(task.get("agency_name") or ""))
    required = 1 if len(tokens) <= 1 else 2
    name_ok = not tokens or sum(1 for token in tokens if token in haystack) >= required

    city = norm(task.get("city"))
    location_ok = bool(city and city in haystack) or "las vegas" in haystack or "henderson" in haystack

    phone = digits(task.get("phone"))
    phone_ok = bool(len(phone) >= 7 and phone[-7:] in digits(text))

    address = norm(task.get("address"))
    address_parts = address.split()
    street_number = address_parts[0] if address_parts and address_parts[0].isdigit() else ""
    street_tokens = [p for p in address_parts[1:] if len(p) >= 4][:2]
    address_ok = bool(street_number and street_number in haystack and any(t in haystack for t in street_tokens))

    license_root = digits(str(task.get("license_number") or "").split("-")[0])
    license_ok = bool(license_root and re.search(rf"\b{re.escape(license_root)}\s*(?:pcs|personal care)", haystack))

    return bool((name_ok and location_ok) or phone_ok or address_ok or license_ok)


def same_domain_links(base_url: str, body: str) -> list[str]:
    base = urlparse(base_url)
    if not base.netloc:
        return []
    preferred_tokens = (
        "personal-care", "personal_care", "services", "care-services", "home-care",
        "pricing", "cost", "rates", "about", "contact", "faq",
    )
    links: list[str] = []
    seen: set[str] = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', body, flags=re.I):
        absolute = urljoin(base_url, unescape(href))
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != base.netloc.lower():
            continue
        lowered = absolute.lower()
        if not any(token in lowered for token in preferred_tokens):
            continue
        cleaned = absolute.split("#", 1)[0]
        if cleaned not in seen:
            seen.add(cleaned)
            links.append(cleaned)
        if len(links) >= 6:
            break
    return links


def _contains(text: str, *terms: str) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _minimum_hours(text: str) -> int | str:
    patterns = (
        r"(?:minimum|min\.?)[^\d]{0,20}(\d{1,2})\s*(?:hour|hr)s?",
        r"(\d{1,2})\s*[- ]?hour\s+(?:minimum|min\.)",
        r"minimum\s+(?:visit|shift)[^\d]{0,20}(\d{1,2})\s*(?:hour|hr)s?",
    )
    lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.I)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 24:
                return value
    return UNKNOWN


def _minimum_minutes(text: str) -> int | str:
    patterns = (
        r"(?:minimum|min\.?)[^\d]{0,20}(\d{2,3})\s*(?:minute|min)s?",
        r"(\d{2,3})\s*[- ]?minute\s+(?:minimum|min\.)",
    )
    lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower, flags=re.I)
        if match:
            value = int(match.group(1))
            if 15 <= value <= 720:
                return value
    return UNKNOWN


def _published_hourly_candidates(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for match in re.finditer(r"\$\s*(\d{2,3}(?:\.\d{1,2})?)\s*(?:/|per\s+)(?:hour|hr)\b", text, flags=re.I):
        value = float(match.group(1))
        if value < 10 or value > 250:
            continue
        start, end = max(0, match.start() - 120), min(len(text), match.end() + 160)
        context = re.sub(r"\s+", " ", text[start:end]).strip()
        candidates.append({"amount_usd_per_hour": value, "context": context})
        if len(candidates) >= 5:
            break
    return candidates


def extract_operational_facts(text: str) -> dict[str, Any]:
    lower = text.lower()
    languages = sorted({label for token, label in LANGUAGE_TOKENS.items() if token in lower})
    employee_model: Any = UNKNOWN
    if re.search(r"\bw[- ]?2\s+employees?\b", lower):
        employee_model = "W2_EMPLOYEES"
    elif re.search(r"\b1099\s+(?:caregivers?|contractors?)\b", lower):
        employee_model = "1099_CONTRACTORS"

    return {
        "bathing_assistance": _contains(lower, "bathing", "shower assistance", "showering assistance", "bath assistance"),
        "dressing_assistance": _contains(lower, "dressing assistance", "help with dressing", "getting dressed", "dressing and grooming"),
        "transfer_assistance": _contains(lower, "transfer assistance", "transferring", "safe transfers", "mobility assistance"),
        "medication_reminders": _contains(lower, "medication reminders", "medicine reminders"),
        "meal_preparation": _contains(lower, "meal preparation", "prepare meals", "meal prep"),
        "light_housekeeping": _contains(lower, "light housekeeping", "housekeeping"),
        "minimum_billable_hours": _minimum_hours(text),
        "minimum_visit_minutes": _minimum_minutes(text),
        "published_hourly_rate_candidates": _published_hourly_candidates(text),
        "hourly_rate_for_requested_schedule": UNKNOWN,
        "employment_model": employee_model,
        "liability_insurance_verified": True if _contains(lower, "licensed bonded and insured", "licensed, bonded and insured", "bonded and insured") else UNKNOWN,
        "workers_comp_verified": True if _contains(lower, "workers compensation", "workers' compensation", "workers comp") else UNKNOWN,
        "background_check_verified": True if _contains(lower, "criminal background check", "background checked", "background-checked", "background screening") else UNKNOWN,
        "fixed_caregiver_possible": True if _contains(lower, "same caregiver", "consistent caregiver", "regular caregiver") else UNKNOWN,
        "availability_status": "24_7_SERVICE_AVAILABLE" if _contains(lower, "24/7", "24 hours a day", "around the clock") else UNKNOWN,
        "languages": languages,
    }


def candidate_primary_url(task: dict[str, Any]) -> str | None:
    query = str(task.get("official_source_discovery_query") or "").strip()
    if not query:
        query = f'"{task.get("agency_name")}" {task.get("city")} NV official home care'
    try:
        results = search_result_urls(query)
    except requests.RequestException:
        return None
    name_tokens = agency_tokens(str(task.get("agency_name") or ""))
    for url, anchor in results:
        domain = urlparse(url).netloc.lower()
        if not domain or any(domain == skip or domain.endswith("." + skip) for skip in SKIP_DOMAINS):
            continue
        haystack = norm(f"{url} {anchor}")
        required = 1 if len(name_tokens) <= 1 else 2
        if name_tokens and sum(1 for token in name_tokens if token in haystack) < required:
            continue
        return url
    return None


def research_task(task: dict[str, Any], *, throttle: float = 0.0) -> dict[str, Any]:
    source_url = candidate_primary_url(task)
    result: dict[str, Any] = {
        "agency_id": task.get("agency_id") or UNKNOWN,
        "agency_name": task.get("agency_name") or UNKNOWN,
        "license_number": task.get("license_number") or UNKNOWN,
        "license_status": task.get("license_status") or UNKNOWN,
        "address": task.get("address") or UNKNOWN,
        "city": task.get("city") or UNKNOWN,
        "state": task.get("state") or "NV",
        "zip": task.get("zip") or UNKNOWN,
        "phone": task.get("phone") or UNKNOWN,
        "primary_source_url": source_url or UNKNOWN,
        "identity_verified": False,
        "research_status": "SOURCE_NOT_FOUND" if not source_url else "PENDING_FETCH",
        "serves_las_vegas_valley": UNKNOWN,
        "source_pages": [],
    }
    if not source_url:
        return result

    try:
        body, status, final_url = fetch(source_url)
    except requests.RequestException as exc:
        result["research_status"] = f"FETCH_ERROR_{exc.__class__.__name__}"
        return result
    result["http_status"] = status
    result["primary_source_url"] = final_url
    if status != 200:
        result["research_status"] = f"HTTP_{status}"
        return result

    page_texts = [strip_html(body)]
    pages = [final_url]
    if identity_matches(page_texts[0], task):
        result["identity_verified"] = True
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
        if not result["identity_verified"] and identity_matches(child_text, task):
            result["identity_verified"] = True

    result["source_pages"] = pages
    if not result["identity_verified"]:
        result["research_status"] = "PRIMARY_SOURCE_IDENTITY_NOT_VERIFIED"
        return result

    combined = " ".join(page_texts)
    facts = extract_operational_facts(combined)
    result.update(facts)
    result["serves_las_vegas_valley"] = True if any(
        token in combined.lower() for token in ("las vegas", "north las vegas", "henderson", "clark county")
    ) else UNKNOWN
    result["research_status"] = "PRIMARY_SOURCE_VERIFIED"
    result["policy"] = "Only explicit primary-source facts are populated. Missing operational facts remain UNKNOWN; published rates are contextual evidence and never become the requested-schedule rate automatically."
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default="reports/NEVADA_PCA_OPERATIONAL_RESEARCH_QUEUE.json")
    ap.add_argument("--output", default="reports/NEVADA_PCA_OPERATIONAL_PRIMARY_RESEARCH.json")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--throttle", type=float, default=0.1)
    args = ap.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    tasks = list(queue.get("tasks") or [])
    selected = tasks[max(0, args.offset): max(0, args.offset) + max(0, args.limit)]
    records = []
    for task in selected:
        records.append(research_task(task, throttle=max(0.0, args.throttle)))
        if args.throttle:
            time.sleep(args.throttle)

    payload = {
        "schema_version": "nevada-pca-operational-primary-research-v1.0.0",
        "queue_task_count": len(tasks),
        "attempted": len(selected),
        "identity_verified": sum(1 for row in records if row.get("identity_verified") is True),
        "source_not_found": sum(1 for row in records if row.get("research_status") == "SOURCE_NOT_FOUND"),
        "records": records,
        "policy": "Research output is evidence staging only. It does not automatically overwrite governed operational evidence or affect recommendations until identity and field-level evidence pass review/gates.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("attempted", "identity_verified", "source_not_found")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
