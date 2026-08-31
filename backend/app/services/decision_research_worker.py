from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests

from app.database import SessionLocal
from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentQueueItem, AgentWorker
from app.services.decision_agent_bridge import QUEUE_TYPE
from app.services.facility_parameter_service import get_canonical_facility_index
from app.services.provider_housing_runtime import get_provider_housing_evidence
from app.services.public_reputation_runtime import get_public_reputation
from app.services.semantic_evidence_ai import capability_map, interpret_facility_evidence_with_ai

_TIMEOUT = 12
_RUN_LOCK = threading.Lock()
_LOG = logging.getLogger(__name__)
_SKIP_DOMAINS = ("aplaceformom.com", "caring.com", "seniorly.com", "yelp.com", "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "google.com", "mapquest.com")
_REGULATORY_DOMAINS = ("nvdpbh.aithent.com", "myhealthfacilitylicense.nv.gov", "dpbh.nv.gov", "health.nv.gov")

# Keyword families are retained only as diagnostic continuity when semantic evidence AI
# is disabled/unavailable and is NOT required. They are not the authoritative production
# interpretation path.
_SOCIAL_TERMS = ("activities", "activity calendar", "social events", "daily events", "engagement", "outings", "clubs", "fitness", "art studio", "movie theater", "cinema", "games", "live music", "community events", "life enrichment", "classes", "lectures")
_MEDICATION_TERMS = ("medication management", "medication assistance", "medication reminders", "medication administration", "manage medications", "medication support")
_ADL_TERMS = ("bathing", "dressing", "activities of daily living", "personal care", "assistance with daily living")
_TRANSPORT_TERMS = ("transportation", "scheduled transportation", "transport service")
_DINING_TERMS = ("restaurant-style dining", "restaurant style dining", "all-day dining", "dining room", "chef")
_REHAB_TERMS = ("rehabilitation", "physical therapy", "occupational therapy", "therapy services", "short-term rehab", "short term rehab", "post-acute rehabilitation")
_COUPLE_TERMS = ("second person", "second occupant", "double occupancy", "couples", "spouse", "two residents", "additional occupant")
_OUTSIDE_CARE_TERMS = ("outside caregiver", "private caregiver", "private duty", "home care agency", "third-party care", "third party care", "outside care")
_CONTINUUM_TERMS = ("continuum of care", "life plan community", "independent living", "assisted living", "skilled nursing", "higher level of care", "levels of care")


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _fetch(url: str) -> tuple[str, int]:
    response = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0 OPTIME Decision Evidence/1.0"}, allow_redirects=True)
    return response.text or "", int(response.status_code)


def _facility_tokens(facility_name: str) -> List[str]:
    stop = {"assisted", "living", "memory", "care", "senior", "home", "the", "and"}
    return [t for t in _norm(facility_name).split() if len(t) >= 4 and t not in stop][:5]


def _search_result_urls(query: str) -> List[tuple[str, str]]:
    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    body, status = _fetch(search_url)
    if status != 200:
        return []
    matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, flags=re.IGNORECASE | re.DOTALL)
    out: List[tuple[str, str]] = []
    for link, anchor in matches:
        url = unquote(parse_qs(urlparse(link).query).get("uddg", [link])[0])
        out.append((url, unescape(re.sub(r"<[^>]+>", " ", anchor))))
    return out


def _candidate_official_url(facility_name: str, city: str, canonical_id: str) -> Optional[str]:
    canonical = get_canonical_facility_index().get(canonical_id) or {}
    for key in ("website", "official_website"):
        value = str(canonical.get(key) or "").strip()
        if value.startswith("http"):
            return value
    query = f"{facility_name} {city or 'Las Vegas'} NV senior living official"
    try:
        matches = _search_result_urls(query)
    except requests.RequestException:
        return None
    name_tokens = _facility_tokens(facility_name)
    for url, anchor in matches:
        domain = urlparse(url).netloc.lower()
        if not domain or any(domain.endswith(skip) for skip in _SKIP_DOMAINS):
            continue
        haystack = _norm(url + " " + anchor)
        required = 1 if len(name_tokens) <= 1 else 2
        if name_tokens and sum(1 for token in name_tokens if token in haystack) < required:
            continue
        return url
    return None


def _candidate_regulatory_url(facility_name: str, city: str) -> Optional[str]:
    query = f'"{facility_name}" {city or "Las Vegas"} Nevada HCQC inspection license'
    try:
        matches = _search_result_urls(query)
    except requests.RequestException:
        return None
    name_tokens = _facility_tokens(facility_name)
    for url, anchor in matches:
        domain = urlparse(url).netloc.lower()
        if not any(domain == allowed or domain.endswith("." + allowed) for allowed in _REGULATORY_DOMAINS):
            continue
        haystack = _norm(url + " " + anchor)
        required = 1 if len(name_tokens) <= 1 else 2
        if name_tokens and sum(1 for token in name_tokens if token in haystack) < required:
            continue
        return url
    return None


def _strip_html(body: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return _norm(unescape(text))


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(_norm(term) in text for term in terms)


def _identity_matches(text: str, facility_name: str, city: str) -> bool:
    tokens = _facility_tokens(facility_name)
    required = 1 if len(tokens) <= 1 else 2
    name_match = not tokens or sum(1 for token in tokens if token in text) >= required
    city_norm = _norm(city or "Las Vegas")
    location_match = "las vegas" in text or (city_norm and city_norm in text)
    return bool(name_match and location_match)


def _verified_registry_overlay(canonical_id: str) -> Dict[str, Any]:
    canonical = dict(get_canonical_facility_index().get(canonical_id) or {})
    if not canonical:
        return {}
    canonical.setdefault("canonical_facility_id", canonical_id)
    provider = get_provider_housing_evidence(canonical)
    if provider.get("provider_housing_evidence"):
        canonical["provider_housing_evidence"] = provider["provider_housing_evidence"]
        canonical["aliases"] = provider.get("provider_aliases") or canonical.get("aliases") or []
        p = provider["provider_housing_evidence"]
        for key in ("address", "city", "state", "zip"):
            value = p.get(key)
            if value and str(value).upper() != "UNKNOWN":
                canonical[key] = value
    if provider.get("life_plan_primary_evidence"):
        canonical["life_plan_primary_evidence"] = provider["life_plan_primary_evidence"]
    reputation = get_public_reputation(canonical)
    return {"provider": provider, "reputation": reputation}


def _apply_verified_registry_evidence(research: Dict[str, Any], canonical_id: str, dimension: str) -> None:
    overlay = _verified_registry_overlay(canonical_id)
    provider = overlay.get("provider") if isinstance(overlay.get("provider"), dict) else {}
    provider_record = provider.get("provider_housing_evidence") if isinstance(provider.get("provider_housing_evidence"), dict) else {}
    evidence = provider_record.get("evidence") if isinstance(provider_record.get("evidence"), dict) else {}
    if evidence:
        research["official_identity_verified"] = True
        source_url = str(provider_record.get("source_url") or "").strip()
        if source_url and source_url.upper() != "UNKNOWN":
            research["source_url"] = source_url
        research["social_engagement_verified"] = evidence.get("social_engagement_verified") is True
        research["medication_support_verified"] = evidence.get("medication_support_verified") is True
        research["adl_support_verified"] = evidence.get("adl_support_verified") is True
        research["transportation_verified"] = evidence.get("transportation_verified") is True
        research["dining_verified"] = evidence.get("dining_verified") is True
        research["rehab_verified"] = evidence.get("rehab_verified") is True
        research["pt_ot_verified"] = evidence.get("pt_ot_verified") is True or evidence.get("pt_ot_external_path_verified") is True
        research["couple_coresidence_verified"] = evidence.get("couple_coresidence_verified") is True or evidence.get("couple_unit_possible") is True
        research["outside_care_allowed_verified"] = evidence.get("outside_care_allowed_verified") is True
        research["continuum_of_care_verified"] = evidence.get("continuum_of_care_verified") is True
        research["verified_registry_used"] = True
        research["evidence_interpretation_mode"] = "GOVERNED_REGISTRY_EVIDENCE"
    reputation = overlay.get("reputation") if isinstance(overlay.get("reputation"), dict) else {}
    if reputation.get("identity_verified") is True:
        research["public_rating"] = reputation.get("rating", "UNKNOWN")
        research["public_review_count"] = reputation.get("review_count", "UNKNOWN")
        research["public_reputation_source"] = reputation.get("source", "UNKNOWN")
        research["public_reputation_identity_verified"] = True
    else:
        research["public_reputation_identity_verified"] = False


def _apply_semantic_capabilities(research: Dict[str, Any], interpretation: Dict[str, Any]) -> bool:
    if interpretation.get("status") != "AI_SEMANTIC_EVIDENCE_INTERPRETED":
        return False
    capabilities = capability_map(interpretation)
    research["semantic_evidence_interpretation"] = interpretation
    research["evidence_interpretation_mode"] = "AI_SEMANTIC_GUARDIAN"

    def sufficient(key: str) -> bool:
        item = capabilities.get(key) or {}
        return item.get("guardian_must_sufficient") is True

    research["social_engagement_verified"] = sufficient("SOCIAL_ENGAGEMENT")
    research["medication_support_verified"] = sufficient("MEDICATION_SUPPORT")
    research["adl_support_verified"] = sufficient("ADL_SUPPORT")
    research["transportation_verified"] = sufficient("TRANSPORTATION")
    research["dining_verified"] = sufficient("DINING")
    research["rehab_verified"] = sufficient("REHAB")
    research["pt_ot_verified"] = sufficient("REHAB") and (capabilities.get("REHAB") or {}).get("level") in {"ONSITE_THERAPY", "SKILLED_REHAB"}
    research["couple_coresidence_verified"] = sufficient("COUPLE_CORESIDENCE")
    research["outside_care_allowed_verified"] = sufficient("OUTSIDE_CARE")
    research["continuum_of_care_verified"] = sufficient("CONTINUUM_OF_CARE")
    return True


def _apply_keyword_fallback(research: Dict[str, Any], text: str) -> None:
    research["evidence_interpretation_mode"] = "KEYWORD_FALLBACK_DIAGNOSTIC_ONLY"
    research["social_engagement_verified"] = _contains_any(text, _SOCIAL_TERMS)
    # Reminder-only wording is deliberately excluded from medication MUST fallback.
    medication_strong_terms = tuple(term for term in _MEDICATION_TERMS if term != "medication reminders")
    research["medication_support_verified"] = _contains_any(text, medication_strong_terms)
    research["adl_support_verified"] = _contains_any(text, _ADL_TERMS)
    research["transportation_verified"] = _contains_any(text, _TRANSPORT_TERMS)
    research["dining_verified"] = _contains_any(text, _DINING_TERMS)
    research["rehab_verified"] = _contains_any(text, _REHAB_TERMS)
    research["pt_ot_verified"] = _contains_any(text, ("physical therapy", "occupational therapy"))
    research["couple_coresidence_verified"] = _contains_any(text, _COUPLE_TERMS)
    research["outside_care_allowed_verified"] = _contains_any(text, _OUTSIDE_CARE_TERMS)
    research["continuum_of_care_verified"] = _contains_any(text, _CONTINUUM_TERMS)


def _persist_record(db, *, agent_key: str, canonical_id: str, facility_name: str, source_url: str, payload: Dict[str, Any]) -> None:
    latest = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == agent_key, AgentKnowledgeRecord.entity_key == canonical_id, AgentKnowledgeRecord.record_type == "las_vegas_decision_evidence").order_by(AgentKnowledgeRecord.id.desc()).first()
    encoded = json.dumps(payload, sort_keys=True)
    if latest is not None and latest.payload_json == encoded:
        return
    verified = [key for key, value in payload.items() if key.endswith("_verified") and value is True]
    summary = f"Las Vegas decision evidence checked for {facility_name}: {', '.join(verified) if verified else 'no requested public claim verified'}"
    if payload.get("regulatory_source_verified") is True:
        source = "NEVADA_HCQC_ALIS"
    elif payload.get("official_identity_verified") is True:
        source = "OFFICIAL_PROVIDER_WEBSITE"
    else:
        source = "PUBLIC_RESEARCH_UNVERIFIED_IDENTITY"
    db.add(AgentKnowledgeRecord(agent_key=agent_key, record_type="las_vegas_decision_evidence", entity_key=canonical_id, summary=summary, payload_json=encoded, confidence=0.9 if payload.get("regulatory_source_verified") is True else (0.82 if verified else 0.65), source=source))


def _process_item(db, item: AgentQueueItem) -> Dict[str, Any]:
    payload = json.loads(item.payload_json or "{}")
    canonical_id = str(payload.get("canonical_facility_id") or "")
    facility_name = str(payload.get("facility_name") or canonical_id)
    city = str(payload.get("city") or "LAS VEGAS")
    dimension = str(payload.get("dimension") or "")
    requested = [str(x) for x in payload.get("requested_parameters") or []]
    source_url = _candidate_regulatory_url(facility_name, city) if dimension == "facility_quality_safety" else _candidate_official_url(facility_name, city, canonical_id)
    research: Dict[str, Any] = {
        "market": "las-vegas", "canonical_facility_id": canonical_id, "facility_name": facility_name,
        "dimension": dimension, "requested_parameters": requested, "research_completed": True,
        "source_url": source_url, "observed_at": datetime.now(timezone.utc).isoformat(),
        "official_identity_verified": False, "regulatory_source_verified": False, "regulatory_parameters_verified": [],
        "social_engagement_verified": False, "medication_support_verified": False, "adl_support_verified": False,
        "transportation_verified": False, "dining_verified": False, "rehab_verified": False, "pt_ot_verified": False,
        "couple_coresidence_verified": False, "outside_care_allowed_verified": False, "continuum_of_care_verified": False,
        "public_rating": "UNKNOWN", "public_review_count": "UNKNOWN", "public_reputation_source": "UNKNOWN",
        "evidence_interpretation_mode": "UNRESOLVED",
    }
    if dimension != "facility_quality_safety":
        _apply_verified_registry_evidence(research, canonical_id, dimension)
        if research.get("source_url"):
            source_url = str(research["source_url"])
    if source_url and not research.get("verified_registry_used"):
        try:
            body, status = _fetch(source_url)
            research["http_status"] = status
            if status == 200:
                text = _strip_html(body)
                identity_ok = _identity_matches(text, facility_name, city)
                domain = urlparse(source_url).netloc.lower()
                if dimension == "facility_quality_safety":
                    research["regulatory_source_verified"] = bool(identity_ok and any(domain == allowed or domain.endswith("." + allowed) for allowed in _REGULATORY_DOMAINS))
                else:
                    research["official_identity_verified"] = identity_ok
                    if identity_ok:
                        interpretation = interpret_facility_evidence_with_ai(
                            facility_name=facility_name,
                            city=city,
                            source_url=source_url,
                            source_text=text,
                            requested_parameters=requested,
                        )
                        if not _apply_semantic_capabilities(research, interpretation):
                            _apply_keyword_fallback(research, text)
        except requests.RequestException as exc:
            research["research_error"] = exc.__class__.__name__
    _persist_record(db, agent_key=str(item.agent_key or "provider_intelligence"), canonical_id=canonical_id, facility_name=facility_name, source_url=source_url or "", payload=research)
    return research


def _reconcile_worker_delivery_metrics(db, remaining: int) -> None:
    workers = db.query(AgentWorker).filter(AgentWorker.queue_type == QUEUE_TYPE).all()
    for worker in workers:
        key = str(worker.agent_key or "")
        total = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.agent_key == key).count()
        done = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.agent_key == key, AgentQueueItem.status == "DONE").count()
        failed = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.agent_key == key, AgentQueueItem.status == "FAILED").count()
        knowledge = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == key, AgentKnowledgeRecord.record_type == "las_vegas_decision_evidence").count()
        useful = db.query(AgentKnowledgeRecord).filter(
            AgentKnowledgeRecord.agent_key == key,
            AgentKnowledgeRecord.record_type == "las_vegas_decision_evidence",
            AgentKnowledgeRecord.source.in_(["OFFICIAL_PROVIDER_WEBSITE", "NEVADA_HCQC_ALIS"]),
        ).count()
        delivery_coverage = round((useful / knowledge) * 100.0, 2) if knowledge else 0.0
        worker.last_run = datetime.now(timezone.utc)
        worker.items_processed = done + failed
        worker.items_added = done
        worker.errors = failed
        worker.knowledge_records = knowledge
        worker.coverage = delivery_coverage
        pending_for_worker = total - done - failed
        if pending_for_worker > 0 or remaining > 0:
            worker.status = "QUEUED"
            worker.last_error = None
        elif done > 0 and useful == 0:
            worker.status = "DEGRADED"
            worker.last_error = "FIELD_DELIVERY_ZERO: tasks completed but no governed evidence reached decision fields"
        else:
            worker.status = "IDLE"
            worker.last_error = None


def _queue_item_priority(item: AgentQueueItem) -> int:
    try:
        payload = json.loads(item.payload_json or "{}")
    except (TypeError, ValueError):
        return 0
    value = payload.get("research_priority")
    return int(value) if isinstance(value, (int, float)) else 0


def _priority_ordered_pending_items(db, limit: int) -> List[AgentQueueItem]:
    """Spend the bounded per-call research budget on what matters most first: a
    dimension that can flip MUST eligibility for a candidate near the front of its
    research pool (see decision_agent_bridge.py's research_priority) outranks a
    NICE-tier dimension or a candidate unlikely to be displayed. Pulls a wider
    candidate window than `limit` (oldest-first, so nothing starves indefinitely
    across repeated worker kicks) and sorts that window by priority in Python, since
    priority lives inside payload_json rather than its own indexed column.
    """
    fetch_limit = min(300, max(1, limit) * 5)
    candidates = (
        db.query(AgentQueueItem)
        .filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "PENDING")
        .order_by(AgentQueueItem.created_at.asc(), AgentQueueItem.id.asc())
        .limit(fetch_limit)
        .all()
    )
    candidates.sort(key=lambda item: -_queue_item_priority(item))
    return candidates[:limit]


def process_pending_decision_research(limit: int = 20) -> Dict[str, Any]:
    if not _RUN_LOCK.acquire(blocking=False):
        return {"status": "ALREADY_RUNNING", "processed": 0, "succeeded": 0, "failed": 0, "remaining": None, "market": "las-vegas"}
    db = SessionLocal()
    processed = succeeded = failed = 0
    run = AgentJobRun(agent_key="decision_evidence_research", status="RUNNING")
    db.add(run); db.commit(); db.refresh(run)
    try:
        items = _priority_ordered_pending_items(db, max(1, int(limit)))
        for item in items:
            item.status = "RUNNING"; item.started_at = datetime.now(timezone.utc); item.attempts = int(item.attempts or 0) + 1; db.commit(); processed += 1
            try:
                result = _process_item(db, item)
                item.status = "DONE"; item.finished_at = datetime.now(timezone.utc)
                positive = any(result.get(k) is True for k in ("social_engagement_verified", "medication_support_verified", "adl_support_verified", "transportation_verified", "dining_verified", "rehab_verified", "pt_ot_verified", "couple_coresidence_verified", "outside_care_allowed_verified", "continuum_of_care_verified", "regulatory_source_verified", "public_reputation_identity_verified"))
                item.error_message = None if positive else "RESEARCH_COMPLETED_NO_REQUESTED_PUBLIC_CLAIM_VERIFIED"; succeeded += 1
            except Exception as exc:
                _LOG.exception("decision evidence item failed id=%s", item.id)
                if int(item.attempts or 0) >= int(item.max_attempts or 3): item.status = "FAILED"; item.finished_at = datetime.now(timezone.utc)
                else: item.status = "PENDING"
                item.error_message = f"{exc.__class__.__name__}: {str(exc)[:300]}"; failed += 1
            db.commit()
        run.status = "SUCCESS" if failed == 0 else ("PARTIAL" if succeeded else "FAILED")
        run.finished_at = datetime.now(timezone.utc); run.items_processed = processed; run.items_added = succeeded; run.errors = failed
        remaining = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "PENDING").count()
        _reconcile_worker_delivery_metrics(db, remaining)
        db.commit()
        return {"status": run.status, "processed": processed, "succeeded": succeeded, "failed": failed, "remaining": remaining, "market": "las-vegas"}
    except Exception:
        _LOG.exception("decision evidence worker run failed"); raise
    finally:
        db.close(); _RUN_LOCK.release()


if __name__ == "__main__":
    print(json.dumps(process_pending_decision_research(), sort_keys=True))
