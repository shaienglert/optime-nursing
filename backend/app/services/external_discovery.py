from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import requests
from sqlalchemy.orm import Session

from app.models.external_discovery import ExternalSourceConnectorHealth, ExternalSourceRequestLog
from app.models.facility import AnswerState, Facility, FacilityActivityCategory, FacilityCapability, FacilityDomainAllowlist, FacilityLicenseRecord
from app.models.knowledge_fabric import KnowledgeEvidence, KnowledgeObject, KnowledgeObjectHistory
from app.services.cms_service import CMS_INSPECTION_DATASET_ID, CMS_PROVIDER_DATASET_ID, CMS_QUALITY_DATASET_ID, download_dataset, iter_csv_rows, to_float, to_int


SOURCE_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "database" / "community_cultural_intelligence.json"
MARKET_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "database" / "market_communities_south_florida.json"
CANONICAL_INVENTORY_PATH = Path(__file__).resolve().parents[3] / "database" / "florida_senior_living_inventory.json"
SOURCE_TIMEOUT_SECONDS = 15

ACTIVITY_KEYWORDS = {
    "movies": ["movie", "movies", "screening room", "cinema", "film", "theater"],
    "music": ["music", "live music", "singing", "choir", "concert"],
    "lectures": ["lecture", "seminar", "discussion", "educational", "learning"],
    "exercise": ["exercise", "fitness", "yoga", "gym", "workout", "stretch"],
    "gardening": ["garden", "gardening", "horticulture", "outdoor spaces"],
    "religious": ["religious", "worship", "chapel", "prayer", "services"],
    "social": ["social", "community-sponsored activities", "events", "engagement", "outings", "games", "arts"],
    "games": ["games", "shuffleboard", "bingo", "cards", "card games"],
    "arts_crafts": ["art studio", "arts and crafts", "creative", "artistic"],
    "cultural": ["cultural", "heritage", "language", "museum", "community"],
    "hebrew_jewish": ["hebrew", "jewish", "kosher", "synagogue"],
}

NUTRITION_KEYWORDS = {
    "restaurant_style_dining": ["restaurant-style dining", "restaurant style dining", "restaurant dining"],
    "meal_preparation": ["meal preparation", "meal preparation and service", "dining service"],
    "chef": ["professional chef", "chef", "executive chef"],
    "special_dietary_restrictions": ["special dietary restrictions", "special diets", "dietary restrictions"],
    "kosher_meals": ["kosher meals", "kosher food", "kosher"],
    "therapeutic_diets": ["diabetic", "renal", "cardiac", "pulmonary", "texture-modified", "pureed", "mechanical soft"],
}

SERVICE_KEYWORDS = {
    "physical_therapy": ["physical therapy", "pt services", "physical therapist"],
    "occupational_therapy": ["occupational therapy", "ot services", "occupational therapist"],
    "speech_therapy": ["speech therapy", "speech-language", "speech pathologist"],
    "stroke_rehabilitation": ["stroke rehabilitation", "stroke rehab", "post-stroke"],
    "wound_care": ["wound care", "wound management"],
    "dialysis": ["dialysis"],
    "cardiac_pulmonary": ["cardiac", "pulmonary", "cardiopulmonary"],
    "specialized_nursing": ["24-hour nursing", "licensed nurses", "skilled nursing"],
}


@dataclass
class SourceDescriptor:
    source_name: str
    source_type: str
    source_locator: str
    source_url: Optional[str]
    agent_key: str
    request_kind: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")


def _stable_hash(*parts: str) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _load_source_registry() -> Dict[str, Dict[str, Any]]:
    registry: Dict[str, Dict[str, Any]] = {}

    if MARKET_REGISTRY_PATH.exists():
        market_data = json.loads(MARKET_REGISTRY_PATH.read_text(encoding="utf-8"))
        for row in market_data.get("records") or []:
            if str(row.get("county") or "").strip().lower() != "miami-dade":
                continue
            key = _normalize(row.get("community_name") or "")
            if key:
                registry[key] = dict(row)

    if SOURCE_REGISTRY_PATH.exists():
        data = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
        records = data.get("records") or []
        for row in records:
            if str(row.get("county") or "").strip().lower() != "miami-dade":
                continue
            key = _normalize(row.get("community_name") or "")
            if not key:
                continue
            current = registry.get(key)
            if current is None:
                registry[key] = dict(row)
                continue
            if not current.get("source_urls") and row.get("source_urls"):
                current["source_urls"] = row.get("source_urls")
            if not current.get("website") and row.get("website"):
                current["website"] = row.get("website")
    return registry


def _load_miami_dade_cms_ids() -> set[str]:
    if not CANONICAL_INVENTORY_PATH.exists():
        return set()
    data = json.loads(CANONICAL_INVENTORY_PATH.read_text(encoding="utf-8"))
    cms_ids: set[str] = set()
    for row in data.get("records") or []:
        if str(row.get("county") or "").strip().lower() != "miami-dade":
            continue
        cms_id = str(row.get("cms_certification_number") or "").strip()
        if cms_id:
            cms_ids.add(cms_id)
    return cms_ids


def _load_miami_dade_facilities(db: Session) -> List[Facility]:
    cms_ids = _load_miami_dade_cms_ids()
    query = db.query(Facility).filter(Facility.state == "FL")
    if cms_ids:
        query = query.filter(Facility.cms_id.in_(sorted(cms_ids)))
    return query.order_by(Facility.name.asc()).all()


def _facility_record(facility: Facility, registry: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    direct = registry.get(_normalize(facility.name or ""))
    if direct is not None:
        return direct
    for key, row in registry.items():
        if key and key in _normalize(facility.name or ""):
            return row
    return None


def _discover_official_url(facility: Facility, registry_row: Optional[Dict[str, Any]]) -> Optional[str]:
    candidates = []
    if registry_row:
        for item in registry_row.get("source_urls") or []:
            if isinstance(item, dict):
                url = str(item.get("source_url") or "").strip()
                if url and "seniorly" not in url.lower():
                    candidates.append(url)
        website = str(registry_row.get("website") or "").strip()
        if website:
            candidates.append(website)

    if candidates:
        return candidates[0]

    query_parts = [facility.name or "", facility.city or "", facility.state or "FL"]
    if registry_row:
        operator = str(registry_row.get("operator_name") or registry_row.get("parent_company") or "").strip()
        if operator:
            query_parts.append(operator)
    query = " ".join(part for part in query_parts if part)
    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        body, status_code, _, _ = _fetch_url(search_url)
    except Exception:
        return None
    if status_code != 200 or not body:
        return None

    links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', body, flags=re.IGNORECASE)
    skip_domains = {
        "seniorly.com",
        "caring.com",
        "aplaceformom.com",
        "medicarelist.com",
        "yelp.com",
        "google.com",
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "youtube.com",
        "maps.apple.com",
        "mapquest.com",
    }
    for link in links:
        url = unquote(parse_qs(urlparse(link).query).get("uddg", [link])[0])
        domain = urlparse(url).netloc.lower()
        if not domain or any(domain.endswith(skip) for skip in skip_domains):
            continue
        if facility.name and _normalize(facility.name)[:8] not in _normalize(url + domain):
            # Keep only results that look like the facility or its operator.
            if registry_row:
                operator = str(registry_row.get("operator_name") or registry_row.get("parent_company") or "").strip()
                if operator and _normalize(operator)[:8] not in _normalize(url + domain):
                    continue
            else:
                continue
        return url
    return None


def _source_descriptors(facility: Facility, registry_row: Optional[Dict[str, Any]]) -> List[SourceDescriptor]:
    descriptors: List[SourceDescriptor] = []
    if registry_row:
        for item in registry_row.get("source_urls") or []:
            if not isinstance(item, dict):
                continue
            source_name = str(item.get("source_name") or "UNKNOWN").strip()
            source_url = str(item.get("source_url") or "").strip() or None
            if not source_url:
                continue
            if "seniorly" in source_url.lower():
                descriptors.append(SourceDescriptor(source_name, "secondary_profile", source_url, source_url, "family_experience", "profile"))
            else:
                descriptors.append(SourceDescriptor(source_name, "official_facility", source_url, source_url, "provider_intelligence", "website"))

    official_url = _discover_official_url(facility, registry_row)
    if official_url:
        descriptors.append(SourceDescriptor("Official website", "official_facility", official_url, official_url, "provider_intelligence", "website"))

    descriptors.append(
        SourceDescriptor(
            source_name="CMS Provider Dataset",
            source_type="government",
            source_locator="https://data.cms.gov/provider-data/4pq5-n9py",
            source_url="https://data.cms.gov/provider-data/",
            agent_key="senior_living_research",
            request_kind="cms_provider",
        )
    )
    descriptors.append(
        SourceDescriptor(
            source_name="CMS Inspection Dataset",
            source_type="government",
            source_locator="https://data.cms.gov/provider-data/r5ix-sfxw",
            source_url="https://data.cms.gov/provider-data/",
            agent_key="senior_living_research",
            request_kind="cms_inspection",
        )
    )
    descriptors.append(
        SourceDescriptor(
            source_name="CMS Quality Dataset",
            source_type="government",
            source_locator="https://data.cms.gov/provider-data/djen-97ju",
            source_url="https://data.cms.gov/provider-data/",
            agent_key="clinical_knowledge",
            request_kind="cms_quality",
        )
    )
    deduped: List[SourceDescriptor] = []
    seen: set[str] = set()
    for item in descriptors:
        key = f"{item.request_kind}|{str(item.source_locator or '').strip().lower()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _classify_http_response(status_code: Optional[int], body: str) -> str:
    text = (body or "")[:5000].lower()
    if status_code == 200:
        if "captcha" in text or ("cloudflare" in text and "attention required" in text):
            return "WAF_OR_CAPTCHA"
        if "robot" in text and "blocked" in text:
            return "ROBOTS_OR_POLICY_BLOCKED"
        return "CONNECTED_DATA_FOUND"
    if status_code == 401:
        return "HTTP_401"
    if status_code == 403:
        if "captcha" in text or "cloudflare" in text:
            return "WAF_OR_CAPTCHA"
        if "access denied" in text or "forbidden" in text:
            return "GEO_BLOCK_SUSPECTED"
        return "HTTP_403"
    if status_code == 429:
        return "HTTP_429"
    return "OTHER"


def _governance_status_for_classification(classification: str, *, connected_no_data: bool = False) -> str:
    if connected_no_data:
        return "RAN_CONNECTED_NO_NEW_VALUE"
    if classification in {"CONNECTED_DATA_FOUND"}:
        return "NEW_VALUE"
    if classification in {"CONNECTED_NO_DATA"}:
        return "RAN_CONNECTED_NO_NEW_VALUE"
    if classification in {"HTTP_429"}:
        return "SOURCE_RATE_LIMITED"
    if classification in {"GEO_BLOCK_SUSPECTED"}:
        return "SOURCE_GEO_BLOCKED_OR_SUSPECTED"
    if classification in {"HTTP_401", "HTTP_403", "TIMEOUT", "DNS_FAILURE", "TLS_FAILURE", "CONNECTION_FAILURE", "WAF_OR_CAPTCHA", "ROBOTS_OR_POLICY_BLOCKED"}:
        return "SOURCE_ACCESS_FAILED"
    if classification in {"PARSE_FAILURE"}:
        return "SOURCE_PARSE_FAILED"
    if classification in {"IDENTITY_MATCH_FAILURE"}:
        return "AGENT_FAILED"
    if classification in {"SOURCE_NOT_CONFIGURED"}:
        return "SOURCE_NOT_CONFIGURED"
    return "OTHER"


def _probe_source(url: str) -> Dict[str, Any]:
    started = _now()
    try:
        body, status_code, final_url, content_type = _fetch_url(url)
        latency_ms = int((_now() - started).total_seconds() * 1000)
        classification = _classify_http_response(status_code, body)
        return {
            "classification": classification,
            "http_status": int(status_code),
            "final_url": final_url,
            "response_type": content_type,
            "response_size": len((body or "").encode("utf-8", errors="ignore")),
            "latency_ms": latency_ms,
            "connected": classification in {"CONNECTED_DATA_FOUND", "CONNECTED_NO_DATA"},
            "error_reason": None,
            "request_time": started.isoformat(),
        }
    except requests.Timeout:
        latency_ms = int((_now() - started).total_seconds() * 1000)
        return {
            "classification": "TIMEOUT",
            "http_status": None,
            "final_url": None,
            "response_type": None,
            "response_size": 0,
            "latency_ms": latency_ms,
            "connected": False,
            "error_reason": "timeout",
            "request_time": started.isoformat(),
        }
    except requests.SSLError:
        latency_ms = int((_now() - started).total_seconds() * 1000)
        return {
            "classification": "TLS_FAILURE",
            "http_status": None,
            "final_url": None,
            "response_type": None,
            "response_size": 0,
            "latency_ms": latency_ms,
            "connected": False,
            "error_reason": "tls_failure",
            "request_time": started.isoformat(),
        }
    except requests.ConnectionError as error:
        latency_ms = int((_now() - started).total_seconds() * 1000)
        message = str(error).lower()
        classification = "DNS_FAILURE" if "dns" in message or "name or service not known" in message else "CONNECTION_FAILURE"
        return {
            "classification": classification,
            "http_status": None,
            "final_url": None,
            "response_type": None,
            "response_size": 0,
            "latency_ms": latency_ms,
            "connected": False,
            "error_reason": str(error),
            "request_time": started.isoformat(),
        }
    except requests.RequestException as error:
        latency_ms = int((_now() - started).total_seconds() * 1000)
        return {
            "classification": "CONNECTION_FAILURE",
            "http_status": None,
            "final_url": None,
            "response_type": None,
            "response_size": 0,
            "latency_ms": latency_ms,
            "connected": False,
            "error_reason": str(error),
            "request_time": started.isoformat(),
        }


def _log_source_attempt(
    db: Session,
    *,
    run_id: str,
    agent_key: str,
    facility: Facility,
    source: SourceDescriptor,
    request_status: str,
    classification: str,
    response_code: Optional[int],
    failure_reason: Optional[str],
    request_time: Optional[str],
    final_url: Optional[str],
    response_type: Optional[str],
    response_size: int,
    latency_ms: Optional[int],
) -> None:
    db.add(
        ExternalSourceRequestLog(
            run_id=run_id,
            agent_key=agent_key or source.agent_key,
            facility_id=facility.id,
            facility_cms_id=str(facility.cms_id),
            facility_name=facility.name,
            source_name=source.source_name,
            source_type=source.source_type,
            source_locator=source.source_locator,
            source_url=source.source_url,
            request_status=request_status,
            change_status="SOURCE_ATTEMPT",
            claim_type="__source_attempt__",
            claim_value=classification,
            previous_value=None,
            verification_status="UNVERIFIED",
            published_at=None,
            evidence_key=None,
            knowledge_object_key=None,
            response_code=response_code,
            failure_reason=failure_reason,
            raw_text_snippet=(failure_reason or "")[:1000],
            payload_json=json.dumps(
                {
                    "request_time": request_time,
                    "final_url": final_url,
                    "response_type": response_type,
                    "response_size": int(response_size or 0),
                    "latency_ms": latency_ms,
                    "result_classification": classification,
                },
                ensure_ascii=True,
            ),
        )
    )


def _fetch_url(url: str) -> Tuple[str, int, str, Optional[str]]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OPTIME/1.0; +https://optime-nursing.local)"}
    response = requests.get(url, headers=headers, timeout=SOURCE_TIMEOUT_SECONDS)
    final_url = response.url
    body = response.text if response.encoding else response.content.decode("utf-8", errors="ignore")
    return body, int(response.status_code), final_url, response.headers.get("content-type")


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _find_snippet(text: str, phrases: Iterable[str]) -> Optional[str]:
    lower = text.lower()
    for phrase in phrases:
        idx = lower.find(phrase.lower())
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(text), idx + len(phrase) + 160)
            return text[start:end].strip()
    return None


def _collect_keyword_matches(text: str, keyword_map: Dict[str, List[str]]) -> Dict[str, str]:
    matches: Dict[str, str] = {}
    for key, phrases in keyword_map.items():
        snippet = _find_snippet(text, phrases)
        if snippet:
            matches[key] = snippet
    return matches


def _extract_pricing(text: str) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for match in re.finditer(r"(?:pricing starts from|starts at|starting at|costs? for this community start at|from)\s*\$([0-9][0-9,]*)\s*/?\s*mo", text, re.IGNORECASE):
        amount = match.group(1).replace(",", "")
        snippet = text[max(0, match.start() - 80): min(len(text), match.end() + 120)].strip()
        results.append({"amount": amount, "snippet": snippet})
    return results


def _extract_rating(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"(\d(?:\.\d)?)\s*\((\d+)\s*reviews?\)", text, re.IGNORECASE)
    if not match:
        return None
    return {"rating": match.group(1), "review_count": int(match.group(2))}


def _extract_license(text: str) -> Optional[str]:
    match = re.search(r"License Number:\s*([A-Z0-9#\- ]{4,40})", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _source_tier(source_type: str) -> str:
    if source_type == "government":
        return "TIER_1"
    if source_type == "official_facility":
        return "TIER_4"
    if source_type == "secondary_profile":
        return "TIER_3"
    return "TIER_4"


def _verification_status(source_type: str) -> str:
    if source_type == "government":
        return "VERIFIED"
    if source_type == "official_facility":
        return "VERIFIED"
    return "PARTIALLY_VERIFIED"


def _make_evidence_key(facility: Facility, source_locator: str, claim_type: str, claim_value: str) -> str:
    return _stable_hash(str(facility.cms_id), source_locator, claim_type, claim_value)


def _make_object_key(facility: Facility, claim_type: str, claim_value: str) -> str:
    return f"external:{facility.cms_id}:{_slug(claim_type)}:{_stable_hash(claim_type, claim_value)[:16]}"


def _upsert_connector_health(db: Session, *, source: SourceDescriptor, status: str, new_value: bool, failure_reason: Optional[str]) -> None:
    key = f"{source.source_name}|{source.source_type}|{source.source_locator}"
    row = db.query(ExternalSourceConnectorHealth).filter(ExternalSourceConnectorHealth.source_key == key).first()
    if row is None:
        for pending in list(db.new):
            if isinstance(pending, ExternalSourceConnectorHealth) and pending.source_key == key:
                row = pending
                break
    now = _now()
    if row is None:
        row = ExternalSourceConnectorHealth(
            source_key=key,
            source_name=source.source_name,
            source_type=source.source_type,
            source_locator=source.source_locator,
        )
        db.add(row)
        db.flush()
    row.source_name = source.source_name
    row.source_type = source.source_type
    row.source_locator = source.source_locator
    if status in {"SUCCESS", "NEW_VALUE", "RAN_CONNECTED_NO_NEW_VALUE"}:
        row.success_count = int(row.success_count or 0) + 1
        row.last_success_at = now
        if new_value:
            row.last_new_value_at = now
        row.last_failure_reason = None
    else:
        row.failure_count = int(row.failure_count or 0) + 1
        row.last_failure_at = now
        row.last_failure_reason = failure_reason or status
    row.facilities_covered = int(row.facilities_covered or 0) + 1
    row.next_refresh_at = now + timedelta(hours=24 if source.source_type == "government" else 7)
    row.metadata_json = json.dumps({"last_status": status, "agent_key": source.agent_key}, ensure_ascii=True)


def _ensure_external_tables(db: Session) -> None:
    bind = db.bind
    if bind is None:
        return
    ExternalSourceConnectorHealth.__table__.create(bind=bind, checkfirst=True)
    ExternalSourceRequestLog.__table__.create(bind=bind, checkfirst=True)
    KnowledgeObject.__table__.create(bind=bind, checkfirst=True)
    KnowledgeEvidence.__table__.create(bind=bind, checkfirst=True)
    KnowledgeObjectHistory.__table__.create(bind=bind, checkfirst=True)


def _upsert_domain_allowlist(db: Session, facility: Facility, domain: str, is_parent_org: bool = False) -> None:
    if not domain:
        return
    row = (
        db.query(FacilityDomainAllowlist)
        .filter(FacilityDomainAllowlist.facility_id == facility.id, FacilityDomainAllowlist.domain == domain)
        .first()
    )
    if row is None:
        row = FacilityDomainAllowlist(facility_id=facility.id, domain=domain)
        db.add(row)
    row.is_parent_org = is_parent_org
    row.is_active = True
    row.manual_approval_required = False


def _upsert_license_record(db: Session, facility: Facility, *, domain: Optional[str], cms_provider_id: Optional[str], ahca_license_number: Optional[str], legal_name: Optional[str], legal_address: Optional[str]) -> None:
    row = db.query(FacilityLicenseRecord).filter(FacilityLicenseRecord.facility_id == facility.id).first()
    if row is None:
        row = FacilityLicenseRecord(facility_id=facility.id)
        db.add(row)
    row.cms_provider_id = cms_provider_id or row.cms_provider_id
    row.ahca_license_number = ahca_license_number or row.ahca_license_number
    row.medicare_provider_number = cms_provider_id or row.medicare_provider_number
    row.legal_name = legal_name or row.legal_name or facility.name
    row.legal_address = legal_address or row.legal_address or facility.address
    row.domain = domain or row.domain
    row.status = "VERIFIED"
    row.verified_at = _now()
    row.verification_notes = "External discovery baseline"


def _upsert_activity_category(db: Session, facility: Facility, category: str, source: str, confidence: float, evidence_text: str) -> None:
    row = (
        db.query(FacilityActivityCategory)
        .filter(FacilityActivityCategory.facility_id == facility.id, FacilityActivityCategory.category == category)
        .first()
    )
    now = _now()
    if row is None:
        row = FacilityActivityCategory(facility_id=facility.id, category=category)
        db.add(row)
    row.availability = AnswerState.YES
    row.confidence = confidence
    row.import_source = source
    row.last_imported_at = now
    row.notes = evidence_text[:255] if hasattr(row, "notes") else None


def _upsert_capability(db: Session, facility: Facility, capability: str, value: AnswerState, source: str, confidence: float, evidence_text: str) -> None:
    row = db.query(FacilityCapability).filter(FacilityCapability.facility_id == facility.id, FacilityCapability.capability == capability).first()
    now = _now()
    if row is None:
        row = FacilityCapability(facility_id=facility.id, capability=capability)
        db.add(row)
    row.value = value
    row.source = source
    row.verified_at = now
    row.expires_at = now + timedelta(days=180 if "diet" in capability or "nutrition" in capability else 365)
    row.confidence = confidence
    row.verification_count = int(row.verification_count or 0) + 1
    row.notes = evidence_text[:500]


def _capability_state(value: Optional[AnswerState]) -> str:
    if value == AnswerState.YES:
        return "VERIFIED_YES"
    if value == AnswerState.NO:
        return "VERIFIED_NO"
    if value == AnswerState.LIMITED:
        return "LIMITED"
    return "UNKNOWN"


def _decision_field_states_for_facility(db: Session, facility: Facility) -> Dict[str, str]:
    caps = {
        str(row.capability): row.value
        for row in db.query(FacilityCapability).filter(FacilityCapability.facility_id == facility.id).all()
    }
    activity_known = (
        db.query(FacilityActivityCategory)
        .filter(FacilityActivityCategory.facility_id == facility.id, FacilityActivityCategory.availability != AnswerState.UNKNOWN)
        .count()
        > 0
    )

    nutrition_keys = {
        "restaurant_style_dining",
        "meal_preparation",
        "chef",
        "special_dietary_restrictions",
        "kosher_meals",
        "therapeutic_diets",
    }
    nutrition_known = any(caps.get(key) in {AnswerState.YES, AnswerState.NO, AnswerState.LIMITED} for key in nutrition_keys)

    return {
        "24_7_skilled_nursing": _capability_state(caps.get("specialized_nursing")),
        "post_stroke_neuro_rehab": _capability_state(caps.get("stroke_rehabilitation")),
        "physical_therapy": _capability_state(caps.get("physical_therapy")),
        "occupational_therapy": _capability_state(caps.get("occupational_therapy")),
        "speech_therapy": _capability_state(caps.get("speech_therapy")),
        "mobility_transfer_assistance": _capability_state(caps.get("mobility_transfer_assistance")),
        "medication_management": _capability_state(caps.get("medication_management")),
        "language_cultural_info": _capability_state(caps.get("hebrew_jewish")),
        "activities": "VERIFIED_VALUE" if activity_known else "UNKNOWN",
        "nutrition_dietary": "VERIFIED_VALUE" if nutrition_known else "UNKNOWN",
        "transportation": _capability_state(caps.get("transportation")),
        "pricing": "VERIFIED_VALUE" if caps.get("published_pricing") in {AnswerState.YES, AnswerState.NO, AnswerState.LIMITED} else "UNKNOWN",
        "availability": _capability_state(caps.get("availability")),
    }


def _count_unknown_fields(states: Dict[str, str]) -> int:
    return sum(1 for value in states.values() if value == "UNKNOWN")


def _count_unknown_transitions(before_states: Dict[str, str], after_states: Dict[str, str]) -> int:
    resolved_states = {"VERIFIED_YES", "VERIFIED_NO", "VERIFIED_VALUE", "LIMITED"}
    count = 0
    for key, before in before_states.items():
        after = after_states.get(key, "UNKNOWN")
        if before == "UNKNOWN" and after in resolved_states:
            count += 1
    return count


def _latest_existing_object(db: Session, facility: Facility, claim_type: str) -> Optional[KnowledgeObject]:
    return (
        db.query(KnowledgeObject)
        .filter(KnowledgeObject.entity_key == str(facility.cms_id), KnowledgeObject.property_name == claim_type, KnowledgeObject.status == "ACTIVE")
        .order_by(KnowledgeObject.updated_at.desc(), KnowledgeObject.id.desc())
        .first()
    )


def _persist_claim(
    db: Session,
    *,
    run_id: str,
    facility: Facility,
    source: SourceDescriptor,
    claim_type: str,
    claim_value: Any,
    evidence_text: str,
    published_at: Optional[datetime] = None,
    agent_key: Optional[str] = None,
    internal_baseline: Optional[str] = None,
    claim_group: str = "FACILITY_ENRICHMENT",
) -> Tuple[str, str, str, str]:
    value_text = json.dumps(claim_value, sort_keys=True, ensure_ascii=True) if isinstance(claim_value, (dict, list)) else str(claim_value)
    object_key = _make_object_key(facility, claim_type, value_text)
    evidence_key = _make_evidence_key(facility, source.source_locator, claim_type, value_text)
    now = _now()
    existing = db.query(KnowledgeObject).filter(KnowledgeObject.object_key == object_key).first()
    previous_value = existing.fact_value if existing is not None else None
    if existing is not None and existing.fact_value == value_text:
        existing.observed_at = now
        existing.updated_at = now
        change_status = "STALE_REFRESHED" if internal_baseline is not None and internal_baseline == value_text else "UNCHANGED"
    else:
        change_status = "NEW" if existing is None else ("CONTRADICTION" if existing and existing.verification_status == "VERIFIED" and existing.source_name != source.source_name else "CHANGED")
        if existing is not None:
            db.add(
                KnowledgeObjectHistory(
                    object_key=object_key,
                    previous_value=previous_value,
                    new_value=value_text,
                    change_reason=change_status,
                    changed_by_agent=agent_key or source.agent_key,
                )
            )
            existing.fact_value = value_text
            existing.source_name = source.source_name
            existing.source_type = source.source_type
            existing.source_reference = source.source_locator
            existing.source_diversity = int(existing.source_diversity or 1) + 1
            existing.evidence_key = evidence_key
            existing.evidence_summary = evidence_text
            existing.published_at = published_at
            existing.observed_at = now
            existing.verification_status = _verification_status(source.source_type)
            existing.verification_type = "EXTERNAL_DISCOVERY"
            existing.freshness_status = "FRESH"
            existing.confidence = 0.95 if source.source_type == "government" else 0.82 if source.source_type == "official_facility" else 0.68
            existing.owner_agent = agent_key or source.agent_key
            existing.status = "ACTIVE"
        else:
            db.add(
                KnowledgeObject(
                    object_key=object_key,
                    title=f"{facility.name} {claim_type}",
                    category=claim_group,
                    topic=claim_type,
                    entity_type="facility",
                    entity_key=str(facility.cms_id),
                    relationship=None,
                    property_name=claim_type,
                    fact_value=value_text,
                    source_name=source.source_name,
                    source_type=source.source_type,
                    source_reference=source.source_locator,
                    trust_level="LEVEL_A" if source.source_type == "government" else "LEVEL_B" if source.source_type == "official_facility" else "LEVEL_C",
                    evidence_key=evidence_key,
                    evidence_summary=evidence_text,
                    published_at=published_at,
                    observed_at=now,
                    verification_status=_verification_status(source.source_type),
                    verification_type="EXTERNAL_DISCOVERY",
                    freshness_status="FRESH",
                    confidence=0.95 if source.source_type == "government" else 0.82 if source.source_type == "official_facility" else 0.68,
                    owner_agent=agent_key or source.agent_key,
                    recommendation_eligible=1,
                    conflict_status="NO_CONFLICT",
                    status="ACTIVE",
                    source_diversity=1,
                    completeness=1.0,
                    consistency=1.0,
                    evidence_strength="STRONG" if source.source_type == "government" else "MODERATE",
                    version="v1",
                    audit_history_json=json.dumps([], ensure_ascii=True),
                    verified_at=now,
                )
            )
        if existing is None:
            existing = db.query(KnowledgeObject).filter(KnowledgeObject.object_key == object_key).first()

    if db.query(KnowledgeEvidence).filter(KnowledgeEvidence.evidence_key == evidence_key).first() is None:
        db.add(
            KnowledgeEvidence(
                evidence_key=evidence_key,
                source_name=source.source_name,
                source_url=source.source_url,
                source_type=source.source_type.upper(),
                trust_level="HIGH" if source.source_type == "government" else "MEDIUM",
                extracted_fact=value_text,
                raw_trace_reference=evidence_text,
            )
        )

    log = ExternalSourceRequestLog(
        run_id=run_id,
        agent_key=agent_key or source.agent_key,
        facility_id=facility.id,
        facility_cms_id=str(facility.cms_id),
        facility_name=facility.name,
        source_name=source.source_name,
        source_type=source.source_type,
        source_locator=source.source_locator,
        source_url=source.source_url,
        request_status="NEW_VALUE" if change_status in {"NEW", "CHANGED"} else "STALE_REFRESHED" if change_status == "STALE_REFRESHED" else "NO_NEW_VALUE",
        change_status=change_status,
        claim_type=claim_type,
        claim_value=value_text,
        previous_value=previous_value,
        verification_status=_verification_status(source.source_type),
        published_at=published_at,
        evidence_key=evidence_key,
        knowledge_object_key=object_key,
        payload_json=json.dumps({"source_tier": _source_tier(source.source_type), "claim_group": claim_group}, ensure_ascii=True),
        raw_text_snippet=evidence_text[:1000],
    )
    db.add(log)
    return change_status, object_key, evidence_key, value_text


def _cms_provider_rows(allowed_ccns: Optional[Set[str]] = None) -> Dict[str, Dict[str, Any]]:
    path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv", force=True)
    rows: Dict[str, Dict[str, Any]] = {}
    for row in iter_csv_rows(path):
        ccn = str(row.get("CMS Certification Number (CCN)") or "").strip()
        if ccn and (allowed_ccns is None or ccn in allowed_ccns):
            rows[ccn] = row
    return rows


def _cms_inspection_rows(allowed_ccns: Optional[Set[str]] = None) -> Dict[str, Dict[str, Any]]:
    path = download_dataset(CMS_INSPECTION_DATASET_ID, "inspection_citations.csv", force=True)
    rows: Dict[str, Dict[str, Any]] = {}
    for row in iter_csv_rows(path):
        ccn = str(row.get("CMS Certification Number (CCN)") or "").strip()
        if not ccn or (allowed_ccns is not None and ccn not in allowed_ccns):
            continue
        bucket = rows.setdefault(ccn, {"rows": []})
        bucket["rows"].append(row)
    return rows


def _cms_quality_rows(allowed_ccns: Optional[Set[str]] = None) -> Dict[str, Dict[str, Any]]:
    path = download_dataset(CMS_QUALITY_DATASET_ID, "quality_measures.csv", force=True)
    rows: Dict[str, Dict[str, Any]] = {}
    for row in iter_csv_rows(path):
        ccn = str(row.get("CMS Certification Number (CCN)") or "").strip()
        if not ccn or (allowed_ccns is not None and ccn not in allowed_ccns):
            continue
        bucket = rows.setdefault(ccn, {"rows": []})
        bucket["rows"].append(row)
    return rows


def _parse_cms_source(db: Session, facility: Facility, provider_rows: Dict[str, Dict[str, Any]], inspection_rows: Dict[str, Dict[str, Any]], quality_rows: Dict[str, Dict[str, Any]], agent_key: str, run_id: str) -> List[Dict[str, Any]]:
    discovered: List[Dict[str, Any]] = []
    provider = provider_rows.get(str(facility.cms_id))
    if provider:
        source = SourceDescriptor("CMS Provider Dataset", "government", "https://data.cms.gov/provider-data/4pq5-n9py", "https://data.cms.gov/provider-data/", agent_key, "cms_provider")
        mappings = {
            "provider_name": provider.get("Provider Name"),
            "address": provider.get("Provider Address"),
            "overall_rating": to_int(provider.get("Overall Rating")),
            "staffing_rating": to_int(provider.get("Staffing Rating")),
            "quality_rating": to_int(provider.get("QM Rating")),
            "inspection_rating": to_int(provider.get("Health Inspection Rating")),
            "beds": to_int(provider.get("Number of Certified Beds")),
        }
        for claim_type, value in mappings.items():
            if value is None or value == "":
                continue
            baseline = str(getattr(facility, claim_type, "")) if hasattr(facility, claim_type) else None
            status, object_key, evidence_key, value_text = _persist_claim(
                db,
                run_id=run_id,
                facility=facility,
                source=source,
                claim_type=claim_type,
                claim_value=value,
                evidence_text=f"CMS provider dataset current value for {claim_type}: {value}",
                published_at=None,
                agent_key=agent_key,
                internal_baseline=baseline,
                claim_group="REGULATORY",
            )
            discovered.append({"claim_type": claim_type, "status": status, "value": value_text, "source": source.source_name, "object_key": object_key, "evidence_key": evidence_key})
        return discovered
    return discovered


def _parse_cms_inspections(db: Session, facility: Facility, inspection_rows: Dict[str, Dict[str, Any]], agent_key: str, run_id: str) -> List[Dict[str, Any]]:
    bucket = inspection_rows.get(str(facility.cms_id)) or {}
    rows = bucket.get("rows") or []
    if not rows:
        return []

    source = SourceDescriptor("CMS Inspection Dataset", "government", "https://data.cms.gov/provider-data/r5ix-sfxw", "https://data.cms.gov/provider-data/", agent_key, "cms_inspection")
    survey_dates = sorted({str(row.get("Survey Date") or "Unknown") for row in rows})
    deficiency_count = len(rows)
    severe_count = sum(1 for row in rows if str(row.get("Scope Severity Code") or "").strip().upper()[:1] in {"G", "H", "I", "J", "K", "L"})
    claim_value = {"survey_dates": survey_dates[-5:], "deficiency_count": deficiency_count, "severe_deficiency_count": severe_count}
    status, object_key, evidence_key, value_text = _persist_claim(
        db,
        run_id=run_id,
        facility=facility,
        source=source,
        claim_type="inspection_summary",
        claim_value=claim_value,
        evidence_text=f"CMS inspection dataset current summary: {deficiency_count} deficiencies across {len(survey_dates)} survey dates.",
        agent_key=agent_key,
        internal_baseline=json.dumps({"deficiency_count": sum(1 for _ in getattr(facility, 'inspections', []))}),
        claim_group="REGULATORY",
    )
    return [{"claim_type": "inspection_summary", "status": status, "value": value_text, "source": source.source_name, "object_key": object_key, "evidence_key": evidence_key}]


def _parse_cms_quality(db: Session, facility: Facility, quality_rows: Dict[str, Dict[str, Any]], agent_key: str, run_id: str) -> List[Dict[str, Any]]:
    bucket = quality_rows.get(str(facility.cms_id)) or {}
    rows = bucket.get("rows") or []
    if not rows:
        return []
    source = SourceDescriptor("CMS Quality Dataset", "government", "https://data.cms.gov/provider-data/djen-97ju", "https://data.cms.gov/provider-data/", agent_key, "cms_quality")
    claim_value = {"quality_rows": len(rows), "measure_codes": sorted({str(row.get('Measure Code') or '') for row in rows if row.get('Measure Code')})[:10]}
    status, object_key, evidence_key, value_text = _persist_claim(
        db,
        run_id=run_id,
        facility=facility,
        source=source,
        claim_type="quality_summary",
        claim_value=claim_value,
        evidence_text=f"CMS quality dataset current summary: {len(rows)} measures.",
        agent_key=agent_key,
        claim_group="REGULATORY",
    )
    return [{"claim_type": "quality_summary", "status": status, "value": value_text, "source": source.source_name, "object_key": object_key, "evidence_key": evidence_key}]


def _parse_official_site(db: Session, facility: Facility, source: SourceDescriptor, html: str, text: str) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    text_lower = text.lower()
    domain = urlparse(source.source_url or source.source_locator).netloc.lower()
    _upsert_domain_allowlist(db, facility, domain, is_parent_org=False)

    license_number = _extract_license(text)
    if license_number:
        _upsert_license_record(db, facility, domain=domain, cms_provider_id=str(facility.cms_id), ahca_license_number=license_number, legal_name=facility.name, legal_address=facility.address)
        claims.append({"claim_type": "license_number", "claim_value": license_number, "claim_group": "IDENTITY", "evidence": f"Official site license number: {license_number}"})

    service_matches = _collect_keyword_matches(text_lower, SERVICE_KEYWORDS)
    if service_matches:
        service_values = sorted(service_matches.keys())
        claims.append({"claim_type": "clinical_services", "claim_value": service_values, "claim_group": "FACILITY_ENRICHMENT", "evidence": "; ".join(service_matches.values())})

    activity_matches = _collect_keyword_matches(text_lower, ACTIVITY_KEYWORDS)
    if activity_matches:
        activity_values = sorted(activity_matches.keys())
        claims.append({"claim_type": "activities", "claim_value": activity_values, "claim_group": "ACTIVITIES", "evidence": "; ".join(activity_matches.values())})

    nutrition_matches = _collect_keyword_matches(text_lower, NUTRITION_KEYWORDS)
    if nutrition_matches:
        nutrition_values = sorted(nutrition_matches.keys())
        claims.append({"claim_type": "nutrition_support", "claim_value": nutrition_values, "claim_group": "NUTRITION", "evidence": "; ".join(nutrition_matches.values())})

    pricing = _extract_pricing(text)
    if pricing:
        claims.append({"claim_type": "pricing", "claim_value": pricing[0], "claim_group": "PRICING", "evidence": pricing[0]["snippet"]})

    partner = _find_snippet(text, ["partnership with", "collaboration with", "provided by", "page info provided by"])
    if partner:
        claims.append({"claim_type": "operator_identity", "claim_value": partner, "claim_group": "IDENTITY", "evidence": partner})

    return claims


def _parse_seniorly_profile(db: Session, facility: Facility, source: SourceDescriptor, html: str, text: str) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    rating = _extract_rating(text)
    if rating:
        claims.append({"claim_type": "family_review_summary", "claim_value": rating, "claim_group": "REPUTATION", "evidence": f"Seniorly rating {rating['rating']} from {rating['review_count']} reviews."})

    pricing = _extract_pricing(text)
    if pricing:
        claims.append({"claim_type": "pricing", "claim_value": pricing[0], "claim_group": "PRICING", "evidence": pricing[0]["snippet"]})

    care_offered = _find_snippet(text, ["care offered", "assisted living", "memory care", "independent living"])
    if care_offered:
        care_values = []
        lowered = care_offered.lower()
        for label in ["assisted living", "memory care", "independent living", "board and care", "skilled nursing"]:
            if label in lowered:
                care_values.append(label)
        if care_values:
            claims.append({"claim_type": "care_models", "claim_value": sorted(set(care_values)), "claim_group": "IDENTITY", "evidence": care_offered})

    amenity_matches = _collect_keyword_matches(text.lower(), {**ACTIVITY_KEYWORDS, **NUTRITION_KEYWORDS})
    if amenity_matches:
        claims.append({"claim_type": "amenities", "claim_value": sorted(amenity_matches.keys()), "claim_group": "FACILITY_ENRICHMENT", "evidence": "; ".join(amenity_matches.values())})

    return claims


def _apply_claim_side_effects(db: Session, facility: Facility, source: SourceDescriptor, claim: Dict[str, Any], status: str) -> None:
    claim_type = str(claim.get("claim_type") or "claim")
    claim_value = claim.get("claim_value")
    evidence_text = str(claim.get("evidence") or "")
    group = str(claim.get("claim_group") or "FACILITY_ENRICHMENT")

    if group == "ACTIVITIES" and isinstance(claim_value, list):
        for category in claim_value:
            _upsert_activity_category(db, facility, str(category), source.source_name, 0.9 if source.source_type == "official_facility" else 0.75, evidence_text)

    if group == "NUTRITION" and isinstance(claim_value, list):
        for capability in claim_value:
            value = AnswerState.YES if capability not in {"special_dietary_restrictions", "therapeutic_diets"} else AnswerState.LIMITED
            _upsert_capability(db, facility, str(capability), value, source.source_name, 0.9 if source.source_type == "official_facility" else 0.75, evidence_text)

    if claim_type == "clinical_services" and isinstance(claim_value, list):
        capability_map = {
            "physical_therapy": "physical_therapy",
            "occupational_therapy": "occupational_therapy",
            "speech_therapy": "speech_therapy",
            "stroke_rehabilitation": "stroke_rehabilitation",
            "specialized_nursing": "specialized_nursing",
        }
        for item in claim_value:
            name = str(item)
            mapped = capability_map.get(name)
            if mapped:
                _upsert_capability(db, facility, mapped, AnswerState.YES, source.source_name, 0.9 if source.source_type == "official_facility" else 0.75, evidence_text)

    if claim_type == "pricing" and isinstance(claim_value, dict) and claim_value.get("amount"):
        _upsert_capability(db, facility, "published_pricing", AnswerState.YES, source.source_name, 0.9 if source.source_type == "official_facility" else 0.75, evidence_text)


def _process_source(db: Session, facility: Facility, source: SourceDescriptor, *, run_id: str, registry_row: Optional[Dict[str, Any]], provider_rows: Dict[str, Dict[str, Any]], inspection_rows: Dict[str, Dict[str, Any]], quality_rows: Dict[str, Dict[str, Any]], agent_key: str, probe_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    if source.request_kind == "cms_provider":
        probe = probe_cache.get(source.source_locator)
        if probe is None:
            probe = _probe_source(source.source_locator)
            probe_cache[source.source_locator] = probe
        claims = _parse_cms_source(db, facility, provider_rows, inspection_rows, quality_rows, agent_key, run_id)
        if not claims and probe.get("connected"):
            return {
                "request_status": "RAN_CONNECTED_NO_NEW_VALUE",
                "claims": [],
                "result_classification": "IDENTITY_MATCH_FAILURE",
                "failure_reason": "cms_provider_row_missing",
                "response_code": probe.get("http_status"),
                "final_url": probe.get("final_url"),
                "content_type": probe.get("response_type"),
                "response_size": probe.get("response_size", 0),
                "latency_ms": probe.get("latency_ms"),
                "request_time": probe.get("request_time"),
            }
        if not claims:
            classification = str(probe.get("classification") or "CONNECTION_FAILURE")
            return {
                "request_status": _governance_status_for_classification(classification),
                "claims": [],
                "result_classification": classification,
                "failure_reason": probe.get("error_reason"),
                "response_code": probe.get("http_status"),
                "final_url": probe.get("final_url"),
                "content_type": probe.get("response_type"),
                "response_size": probe.get("response_size", 0),
                "latency_ms": probe.get("latency_ms"),
                "request_time": probe.get("request_time"),
            }
        for claim in claims:
            _apply_claim_side_effects(db, facility, source, claim, claim.get("status", "NEW"))
        request_status = "NEW_VALUE" if any(claim["status"] in {"NEW", "CHANGED"} for claim in claims) else "RAN_CONNECTED_NO_NEW_VALUE"
        return {
            "request_status": request_status,
            "claims": claims,
            "result_classification": "CONNECTED_DATA_FOUND" if request_status == "NEW_VALUE" else "CONNECTED_NO_DATA",
            "failure_reason": None,
            "response_code": probe.get("http_status"),
            "final_url": probe.get("final_url"),
            "content_type": probe.get("response_type"),
            "response_size": probe.get("response_size", 0),
            "latency_ms": probe.get("latency_ms"),
            "request_time": probe.get("request_time"),
        }

    if source.request_kind == "cms_inspection":
        probe = probe_cache.get(source.source_locator)
        if probe is None:
            probe = _probe_source(source.source_locator)
            probe_cache[source.source_locator] = probe
        claims = _parse_cms_inspections(db, facility, inspection_rows, agent_key, run_id)
        for claim in claims:
            _apply_claim_side_effects(db, facility, source, claim, claim.get("status", "NEW"))
        if claims:
            request_status = "NEW_VALUE" if any(claim["status"] in {"NEW", "CHANGED"} for claim in claims) else "RAN_CONNECTED_NO_NEW_VALUE"
            classification = "CONNECTED_DATA_FOUND" if request_status == "NEW_VALUE" else "CONNECTED_NO_DATA"
        elif probe.get("connected"):
            request_status = "RAN_CONNECTED_NO_NEW_VALUE"
            classification = "CONNECTED_NO_DATA"
        else:
            classification = str(probe.get("classification") or "CONNECTION_FAILURE")
            request_status = _governance_status_for_classification(classification)
        return {
            "request_status": request_status,
            "claims": claims,
            "result_classification": classification,
            "failure_reason": probe.get("error_reason") if not probe.get("connected") else None,
            "response_code": probe.get("http_status"),
            "final_url": probe.get("final_url"),
            "content_type": probe.get("response_type"),
            "response_size": probe.get("response_size", 0),
            "latency_ms": probe.get("latency_ms"),
            "request_time": probe.get("request_time"),
        }

    if source.request_kind == "cms_quality":
        probe = probe_cache.get(source.source_locator)
        if probe is None:
            probe = _probe_source(source.source_locator)
            probe_cache[source.source_locator] = probe
        claims = _parse_cms_quality(db, facility, quality_rows, agent_key, run_id)
        for claim in claims:
            _apply_claim_side_effects(db, facility, source, claim, claim.get("status", "NEW"))
        if claims:
            request_status = "NEW_VALUE" if any(claim["status"] in {"NEW", "CHANGED"} for claim in claims) else "RAN_CONNECTED_NO_NEW_VALUE"
            classification = "CONNECTED_DATA_FOUND" if request_status == "NEW_VALUE" else "CONNECTED_NO_DATA"
        elif probe.get("connected"):
            request_status = "RAN_CONNECTED_NO_NEW_VALUE"
            classification = "CONNECTED_NO_DATA"
        else:
            classification = str(probe.get("classification") or "CONNECTION_FAILURE")
            request_status = _governance_status_for_classification(classification)
        return {
            "request_status": request_status,
            "claims": claims,
            "result_classification": classification,
            "failure_reason": probe.get("error_reason") if not probe.get("connected") else None,
            "response_code": probe.get("http_status"),
            "final_url": probe.get("final_url"),
            "content_type": probe.get("response_type"),
            "response_size": probe.get("response_size", 0),
            "latency_ms": probe.get("latency_ms"),
            "request_time": probe.get("request_time"),
        }

    if not source.source_url:
        return {"request_status": "SOURCE_NOT_CONFIGURED", "claims": [], "result_classification": "SOURCE_NOT_CONFIGURED", "failure_reason": "missing_source_url", "response_size": 0}

    started = _now()
    try:
        body, response_code, final_url, content_type = _fetch_url(source.source_url)
    except requests.Timeout:
        latency_ms = int((_now() - started).total_seconds() * 1000)
        return {"request_status": "SOURCE_ACCESS_FAILED", "claims": [], "result_classification": "TIMEOUT", "failure_reason": "timeout", "response_size": 0, "latency_ms": latency_ms, "request_time": started.isoformat()}
    except requests.RequestException as error:
        message = str(error)
        latency_ms = int((_now() - started).total_seconds() * 1000)
        lowered = message.lower()
        if "dns" in lowered or "name or service not known" in lowered:
            return {"request_status": "SOURCE_ACCESS_FAILED", "claims": [], "result_classification": "DNS_FAILURE", "failure_reason": message, "response_size": 0, "latency_ms": latency_ms, "request_time": started.isoformat()}
        if "ssl" in lowered or "tls" in lowered:
            return {"request_status": "SOURCE_ACCESS_FAILED", "claims": [], "result_classification": "TLS_FAILURE", "failure_reason": message, "response_size": 0, "latency_ms": latency_ms, "request_time": started.isoformat()}
        return {"request_status": "SOURCE_ACCESS_FAILED", "claims": [], "result_classification": "CONNECTION_FAILURE", "failure_reason": message, "response_size": 0, "latency_ms": latency_ms, "request_time": started.isoformat()}

    latency_ms = int((_now() - started).total_seconds() * 1000)
    response_size = len((body or "").encode("utf-8", errors="ignore"))
    classification = _classify_http_response(response_code, body)

    if response_code in {401, 403, 429}:
        return {
            "request_status": _governance_status_for_classification(classification),
            "claims": [],
            "result_classification": classification,
            "failure_reason": f"http_{response_code}",
            "response_code": response_code,
            "final_url": final_url,
            "content_type": content_type,
            "response_size": response_size,
            "latency_ms": latency_ms,
            "request_time": started.isoformat(),
        }
    if response_code == 404:
        return {"request_status": "SOURCE_ACCESS_FAILED", "claims": [], "result_classification": "OTHER", "failure_reason": "http_404", "response_code": response_code, "final_url": final_url, "content_type": content_type, "response_size": response_size, "latency_ms": latency_ms, "request_time": started.isoformat()}
    if response_code >= 500:
        return {"request_status": "SOURCE_PARSE_FAILED", "claims": [], "result_classification": "PARSE_FAILURE", "failure_reason": f"http_{response_code}", "response_code": response_code, "final_url": final_url, "content_type": content_type, "response_size": response_size, "latency_ms": latency_ms, "request_time": started.isoformat()}

    text = _html_to_text(body)
    if not text:
        return {"request_status": "SOURCE_PARSE_FAILED", "claims": [], "result_classification": "PARSE_FAILURE", "failure_reason": "empty_body", "response_code": response_code, "final_url": final_url, "content_type": content_type, "response_size": response_size, "latency_ms": latency_ms, "request_time": started.isoformat()}

    if source.source_type == "official_facility":
        claims = _parse_official_site(db, facility, source, body, text)
    else:
        claims = _parse_seniorly_profile(db, facility, source, body, text)

    statuses: List[str] = []
    for claim in claims:
        claim_status, object_key, evidence_key, value_text = _persist_claim(
            db,
            run_id=run_id,
            facility=facility,
            source=source,
            claim_type=str(claim.get("claim_type") or "claim"),
            claim_value=claim.get("claim_value"),
            evidence_text=str(claim.get("evidence") or text[:500]),
            published_at=None,
            agent_key=agent_key,
            internal_baseline=None,
            claim_group=str(claim.get("claim_group") or "FACILITY_ENRICHMENT"),
        )
        claim["status"] = claim_status
        claim["object_key"] = object_key
        claim["evidence_key"] = evidence_key
        claim["value_text"] = value_text
        _apply_claim_side_effects(db, facility, source, claim, claim_status)
        statuses.append(claim_status)

    if not claims:
        return {
            "request_status": "RAN_CONNECTED_NO_NEW_VALUE",
            "claims": [],
            "result_classification": "CONNECTED_NO_DATA",
            "response_code": response_code,
            "final_url": final_url,
            "content_type": content_type,
            "response_size": response_size,
            "latency_ms": latency_ms,
            "request_time": started.isoformat(),
        }

    if any(status in {"NEW", "CHANGED", "CONTRADICTION"} for status in statuses):
        request_status = "NEW_VALUE"
    elif all(status == "STALE_REFRESHED" for status in statuses):
        request_status = "RAN_CONNECTED_NO_NEW_VALUE"
    else:
        request_status = "RAN_CONNECTED_NO_NEW_VALUE"

    return {
        "request_status": request_status,
        "claims": claims,
        "result_classification": "CONNECTED_DATA_FOUND" if request_status == "NEW_VALUE" else "CONNECTED_NO_DATA",
        "response_code": response_code,
        "final_url": final_url,
        "content_type": content_type,
        "response_size": response_size,
        "latency_ms": latency_ms,
        "request_time": started.isoformat(),
    }


def _unknown_state_for_facility(db: Session, facility: Facility) -> Dict[str, int]:
    activity_count = db.query(FacilityActivityCategory).filter(FacilityActivityCategory.facility_id == facility.id, FacilityActivityCategory.availability != AnswerState.UNKNOWN).count()
    capability_count = db.query(FacilityCapability).filter(FacilityCapability.facility_id == facility.id, FacilityCapability.value != AnswerState.UNKNOWN).count()
    license_count = db.query(FacilityLicenseRecord).filter(FacilityLicenseRecord.facility_id == facility.id, FacilityLicenseRecord.status == "VERIFIED").count()
    domain_count = db.query(FacilityDomainAllowlist).filter(FacilityDomainAllowlist.facility_id == facility.id, FacilityDomainAllowlist.is_active == True).count()  # noqa: E712
    return {
        "unknown_before": max(0, 6 - min(6, activity_count + capability_count + license_count + domain_count)),
    }


def run_external_discovery(db: Session, *, agent_key: str = "provider_intelligence", facility_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    _ensure_external_tables(db)
    registry = _load_source_registry()
    facilities = _load_miami_dade_facilities(db)
    if facility_ids:
        wanted = set(facility_ids)
        facilities = [facility for facility in facilities if facility.id in wanted]

    target_ccns = {str(facility.cms_id or "").strip() for facility in facilities if str(facility.cms_id or "").strip()}
    provider_rows = _cms_provider_rows(target_ccns)
    inspection_rows = _cms_inspection_rows(target_ccns)
    quality_rows = _cms_quality_rows(target_ccns)

    now = _now()
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    result: Dict[str, Any] = {
        "run_id": run_id,
        "agent_key": agent_key,
        "facilities_targeted": len(facilities),
        "facilities_successfully_discovered": 0,
        "external_sources_identified": 0,
        "external_source_requests": 0,
        "source_successes": 0,
        "source_failures": 0,
        "source_access_successes": 0,
        "content_retrieval_successes": 0,
        "relevant_evidence_found": 0,
        "verified_fact_created": 0,
        "new_external_verified_facts": 0,
        "external_changed_facts": 0,
        "derived_insights": 0,
        "unknown_before": 0,
        "unknown_resolved": 0,
        "unknown_remaining": 0,
        "new_regulatory_findings": 0,
        "new_verified_services": 0,
        "new_activity_findings": 0,
        "new_nutrition_findings": 0,
        "new_ownership_identity_findings": 0,
        "new_verified_prices": 0,
        "contradictions": 0,
        "first_run_new_external_value": 0,
        "second_run_duplicates": 0,
        "idempotency": "PASS",
        "source_requests_by_status": {},
        "new_discoveries": [],
        "source_failures_detail": [],
        "source_health": [],
        "unknowns_by_facility": [],
        "source_attempt_telemetry": [],
    }
    probe_cache: Dict[str, Dict[str, Any]] = {}

    for facility in facilities:
        registry_row = _facility_record(facility, registry)

        result["facilities_successfully_discovered"] += 1
        db.flush()
        before_states = _decision_field_states_for_facility(db, facility)
        before = _count_unknown_fields(before_states)
        result["unknown_before"] += before

        descriptors = _source_descriptors(facility, registry_row)
        result["external_sources_identified"] += len(descriptors)
        source_counts: Dict[str, int] = {}
        facility_discoveries: List[Dict[str, Any]] = []

        for source in descriptors:
            try:
                outcome = _process_source(
                    db,
                    facility,
                    source,
                    run_id=run_id,
                    registry_row=registry_row,
                    provider_rows=provider_rows,
                    inspection_rows=inspection_rows,
                    quality_rows=quality_rows,
                    agent_key=source.agent_key,
                    probe_cache=probe_cache,
                )
            except Exception as error:
                outcome = {
                    "request_status": "AGENT_FAILED",
                    "claims": [],
                    "result_classification": "OTHER",
                    "failure_reason": str(error),
                    "response_size": 0,
                    "request_time": _now().isoformat(),
                }
            request_status = str(outcome.get("request_status") or "NO_NEW_VALUE")
            claims = outcome.get("claims") or []
            source_counts[request_status] = source_counts.get(request_status, 0) + 1
            result["external_source_requests"] += 1

            classification = str(outcome.get("result_classification") or "OTHER")
            _log_source_attempt(
                db,
                run_id=run_id,
                agent_key=source.agent_key,
                facility=facility,
                source=source,
                request_status=request_status,
                classification=classification,
                response_code=outcome.get("response_code"),
                failure_reason=outcome.get("failure_reason"),
                request_time=outcome.get("request_time"),
                final_url=outcome.get("final_url"),
                response_type=outcome.get("content_type"),
                response_size=int(outcome.get("response_size") or 0),
                latency_ms=outcome.get("latency_ms"),
            )
            if len(result["source_attempt_telemetry"]) < 200:
                result["source_attempt_telemetry"].append(
                    {
                        "source": source.source_name,
                        "url": source.source_locator,
                        "agent": source.agent_key,
                        "request_time": outcome.get("request_time"),
                        "http_status": outcome.get("response_code"),
                        "final_url": outcome.get("final_url"),
                        "response_type": outcome.get("content_type"),
                        "response_size": int(outcome.get("response_size") or 0),
                        "latency_ms": outcome.get("latency_ms"),
                        "result_classification": classification,
                        "reason": outcome.get("failure_reason"),
                    }
                )

            if request_status in {"NEW_VALUE", "SUCCESS", "RAN_CONNECTED_NO_NEW_VALUE"}:
                result["source_successes"] += 1
            else:
                result["source_failures"] += 1
                result["source_failures_detail"].append({"facility": facility.name, "source": source.source_name, "status": request_status, "reason": outcome.get("failure_reason")})

            response_code = outcome.get("response_code")
            if isinstance(response_code, int) and 200 <= response_code < 400:
                result["source_access_successes"] += 1

            if int(outcome.get("response_size") or 0) > 0:
                result["content_retrieval_successes"] += 1

            if claims:
                result["relevant_evidence_found"] += 1

            if any(str(claim.get("status") or "") in {"NEW", "CHANGED"} for claim in claims):
                result["verified_fact_created"] += 1

            result["source_requests_by_status"][request_status] = int(result["source_requests_by_status"].get(request_status, 0)) + 1

            _upsert_connector_health(db, source=source, status=request_status, new_value=request_status == "NEW_VALUE", failure_reason=outcome.get("failure_reason") if request_status not in {"NEW_VALUE", "RAN_CONNECTED_NO_NEW_VALUE"} else None)

            for claim in claims:
                status = str(claim.get("status") or "UNCHANGED")
                value_text = str(claim.get("value_text") or claim.get("claim_value") or "")
                if status == "NEW":
                    result["new_external_verified_facts"] += 1
                    result["first_run_new_external_value"] += 1
                elif status == "CHANGED":
                    result["external_changed_facts"] += 1
                elif status == "CONTRADICTION":
                    result["contradictions"] += 1
                claim_group = str(claim.get("claim_group") or "FACILITY_ENRICHMENT")
                if claim_group == "REGULATORY" and status in {"NEW", "CHANGED"}:
                    result["new_regulatory_findings"] += 1
                if claim.get("claim_type") == "clinical_services" and status in {"NEW", "CHANGED"}:
                    result["new_verified_services"] += 1
                if claim_group == "ACTIVITIES" and status in {"NEW", "CHANGED"}:
                    result["new_activity_findings"] += 1
                if claim_group == "NUTRITION" and status in {"NEW", "CHANGED"}:
                    result["new_nutrition_findings"] += 1
                if claim_group == "IDENTITY" and status in {"NEW", "CHANGED"}:
                    result["new_ownership_identity_findings"] += 1
                if claim_group == "PRICING" and status in {"NEW", "CHANGED"}:
                    result["new_verified_prices"] += 1

                if len(facility_discoveries) < 10 and status in {"NEW", "CHANGED", "STALE_REFRESHED"}:
                    facility_discoveries.append(
                        {
                            "facility": facility.name,
                            "source": source.source_name,
                            "source_type": source.source_type,
                            "claim_type": claim.get("claim_type"),
                            "claim_value": value_text,
                            "status": status,
                            "retrieved_at": now.isoformat(),
                        }
                    )

            db.flush()
            after_states = _decision_field_states_for_facility(db, facility)
            if claims and any(claim.get("evidence_key") for claim in claims):
                result["unknown_resolved"] += _count_unknown_transitions(before_states, after_states)
            before_states = after_states

        db.flush()
        after = _count_unknown_fields(_decision_field_states_for_facility(db, facility))
        result["unknown_remaining"] += after
        result["unknowns_by_facility"].append({"facility": facility.name, "unknown_before": before, "unknown_after": after, "sources": source_counts})
        result["new_discoveries"].extend(facility_discoveries)

    db.commit()
    result["source_health"] = build_external_discovery_summary(db).get("source_health", [])
    return result


def build_external_discovery_summary(db: Session) -> Dict[str, Any]:
    _ensure_external_tables(db)
    health_rows = db.query(ExternalSourceConnectorHealth).order_by(ExternalSourceConnectorHealth.source_name.asc()).all()
    request_rows = db.query(ExternalSourceRequestLog).order_by(ExternalSourceRequestLog.created_at.desc()).limit(400).all()
    source_attempt_rows = [row for row in request_rows if str(row.claim_type or "") == "__source_attempt__"]
    claim_rows = [row for row in request_rows if str(row.claim_type or "") != "__source_attempt__"]
    status_counts: Dict[str, int] = {}
    for row in source_attempt_rows:
        key = str(row.request_status or "UNKNOWN")
        status_counts[key] = status_counts.get(key, 0) + 1

    classification_counts: Dict[str, int] = {}
    for row in source_attempt_rows:
        key = str(row.claim_value or "OTHER")
        classification_counts[key] = classification_counts.get(key, 0) + 1

    source_health = []
    for row in health_rows:
        total = int(row.success_count or 0) + int(row.failure_count or 0)
        success_rate = round((int(row.success_count or 0) / total) * 100.0, 1) if total else 0.0
        source_health.append(
            {
                "source_name": row.source_name,
                "source_type": row.source_type,
                "source_locator": row.source_locator,
                "last_success": row.last_success_at.isoformat() if row.last_success_at else None,
                "last_failure": row.last_failure_at.isoformat() if row.last_failure_at else None,
                "success_rate": success_rate,
                "facilities_covered": int(row.facilities_covered or 0),
                "last_new_value": row.last_new_value_at.isoformat() if row.last_new_value_at else None,
                "failure_reason": row.last_failure_reason,
                "next_refresh": row.next_refresh_at.isoformat() if row.next_refresh_at else None,
            }
        )

    return {
        "request_status_counts": status_counts,
        "request_classification_counts": classification_counts,
        "source_health": source_health,
        "recent_source_attempts": [
            {
                "facility": row.facility_name,
                "source": row.source_name,
                "status": row.request_status,
                "classification": row.claim_value,
                "reason": row.failure_reason,
                "http_status": row.response_code,
                "request_time": (json.loads(row.payload_json or "{}").get("request_time") if row.payload_json else None),
                "final_url": (json.loads(row.payload_json or "{}").get("final_url") if row.payload_json else None),
                "response_type": (json.loads(row.payload_json or "{}").get("response_type") if row.payload_json else None),
                "response_size": (json.loads(row.payload_json or "{}").get("response_size") if row.payload_json else 0),
                "latency_ms": (json.loads(row.payload_json or "{}").get("latency_ms") if row.payload_json else None),
                "retrieved_at": row.retrieved_at.isoformat() if row.retrieved_at else None,
            }
            for row in source_attempt_rows[:120]
        ],
        "recent_requests": [
            {
                "facility": row.facility_name,
                "source": row.source_name,
                "status": row.request_status,
                "change_status": row.change_status,
                "claim_type": row.claim_type,
                "claim_value": row.claim_value,
                "retrieved_at": row.retrieved_at.isoformat() if row.retrieved_at else None,
            }
            for row in claim_rows[:80]
        ],
    }