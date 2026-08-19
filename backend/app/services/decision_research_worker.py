from __future__ import annotations

import json
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

_TIMEOUT = 12
_RUN_LOCK = threading.Lock()
_SKIP_DOMAINS = ("aplaceformom.com", "caring.com", "seniorly.com", "yelp.com", "facebook.com", "instagram.com", "linkedin.com", "youtube.com", "google.com", "mapquest.com")
_SOCIAL_TERMS = ("activities", "activity calendar", "social events", "daily events", "engagement", "outings", "clubs", "fitness", "art studio", "movie theater", "cinema", "games", "live music", "community events", "life enrichment")
_MEDICATION_TERMS = ("medication management", "medication assistance", "medication reminders", "medication administration", "manage medications", "medication support")
_TRANSPORT_TERMS = ("transportation", "scheduled transportation", "transport service")
_DINING_TERMS = ("restaurant-style dining", "restaurant style dining", "all-day dining", "dining room", "chef")


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _fetch(url: str) -> tuple[str, int]:
    response = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0 OPTIME Decision Evidence/1.0"}, allow_redirects=True)
    return response.text or "", int(response.status_code)


def _facility_tokens(facility_name: str) -> List[str]:
    stop = {"assisted", "living", "memory", "care", "senior", "home", "the", "and"}
    return [t for t in _norm(facility_name).split() if len(t) >= 4 and t not in stop][:5]


def _candidate_official_url(facility_name: str, city: str, canonical_id: str) -> Optional[str]:
    canonical = get_canonical_facility_index().get(canonical_id) or {}
    for key in ("website", "official_website"):
        value = str(canonical.get(key) or "").strip()
        if value.startswith("http"):
            return value
    query = f"{facility_name} {city or 'Las Vegas'} NV assisted living official"
    search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        body, status = _fetch(search_url)
    except requests.RequestException:
        return None
    if status != 200:
        return None
    matches = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, flags=re.IGNORECASE | re.DOTALL)
    name_tokens = _facility_tokens(facility_name)
    for link, anchor in matches:
        url = unquote(parse_qs(urlparse(link).query).get("uddg", [link])[0])
        domain = urlparse(url).netloc.lower()
        if not domain or any(domain.endswith(skip) for skip in _SKIP_DOMAINS):
            continue
        haystack = _norm(url + " " + unescape(re.sub(r"<[^>]+>", " ", anchor)))
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


def _persist_record(db, *, agent_key: str, canonical_id: str, facility_name: str, source_url: str, payload: Dict[str, Any]) -> None:
    latest = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == agent_key, AgentKnowledgeRecord.entity_key == canonical_id, AgentKnowledgeRecord.record_type == "las_vegas_decision_evidence").order_by(AgentKnowledgeRecord.id.desc()).first()
    encoded = json.dumps(payload, sort_keys=True)
    if latest is not None and latest.payload_json == encoded:
        return
    verified = [key for key, value in payload.items() if key.endswith("_verified") and value is True]
    summary = f"Las Vegas decision evidence checked for {facility_name}: {', '.join(verified) if verified else 'no requested public claim verified'}"
    source = "OFFICIAL_PROVIDER_WEBSITE" if payload.get("official_identity_verified") is True else "PUBLIC_RESEARCH_UNVERIFIED_IDENTITY"
    db.add(AgentKnowledgeRecord(agent_key=agent_key, record_type="las_vegas_decision_evidence", entity_key=canonical_id, summary=summary, payload_json=encoded, confidence=0.82 if verified else 0.65, source=source))


def _process_item(db, item: AgentQueueItem) -> Dict[str, Any]:
    payload = json.loads(item.payload_json or "{}")
    canonical_id = str(payload.get("canonical_facility_id") or "")
    facility_name = str(payload.get("facility_name") or canonical_id)
    city = str(payload.get("city") or "LAS VEGAS")
    requested = [str(x) for x in payload.get("requested_parameters") or []]
    source_url = _candidate_official_url(facility_name, city, canonical_id)
    research: Dict[str, Any] = {"market": "las-vegas", "canonical_facility_id": canonical_id, "facility_name": facility_name, "requested_parameters": requested, "research_completed": True, "source_url": source_url, "observed_at": datetime.now(timezone.utc).isoformat(), "official_identity_verified": False, "social_engagement_verified": False, "medication_support_verified": False, "transportation_verified": False, "dining_verified": False}
    if source_url:
        try:
            body, status = _fetch(source_url)
            research["http_status"] = status
            if status == 200:
                text = _strip_html(body)
                identity_ok = _identity_matches(text, facility_name, city)
                research["official_identity_verified"] = identity_ok
                if identity_ok:
                    research["social_engagement_verified"] = _contains_any(text, _SOCIAL_TERMS)
                    research["medication_support_verified"] = _contains_any(text, _MEDICATION_TERMS)
                    research["transportation_verified"] = _contains_any(text, _TRANSPORT_TERMS)
                    research["dining_verified"] = _contains_any(text, _DINING_TERMS)
        except requests.RequestException as exc:
            research["research_error"] = exc.__class__.__name__
    _persist_record(db, agent_key=str(item.agent_key or "provider_intelligence"), canonical_id=canonical_id, facility_name=facility_name, source_url=source_url or "", payload=research)
    return research


def process_pending_decision_research(limit: int = 20) -> Dict[str, Any]:
    if not _RUN_LOCK.acquire(blocking=False):
        return {"status": "ALREADY_RUNNING", "processed": 0, "succeeded": 0, "failed": 0, "remaining": None, "market": "las-vegas"}
    db = SessionLocal()
    processed = succeeded = failed = 0
    run = AgentJobRun(agent_key="decision_evidence_research", status="RUNNING")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        items: List[AgentQueueItem] = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "PENDING").order_by(AgentQueueItem.created_at.asc()).limit(max(1, int(limit))).all()
        for item in items:
            item.status = "RUNNING"
            item.started_at = datetime.now(timezone.utc)
            item.attempts = int(item.attempts or 0) + 1
            db.commit()
            processed += 1
            try:
                result = _process_item(db, item)
                item.status = "DONE"
                item.finished_at = datetime.now(timezone.utc)
                item.error_message = None if any(result.get(k) is True for k in ("social_engagement_verified", "medication_support_verified", "transportation_verified", "dining_verified")) else "RESEARCH_COMPLETED_NO_REQUESTED_PUBLIC_CLAIM_VERIFIED"
                succeeded += 1
            except Exception as exc:
                if int(item.attempts or 0) >= int(item.max_attempts or 3):
                    item.status = "FAILED"
                    item.finished_at = datetime.now(timezone.utc)
                else:
                    item.status = "PENDING"
                item.error_message = exc.__class__.__name__
                failed += 1
            db.commit()
        run.status = "SUCCESS" if failed == 0 else ("PARTIAL" if succeeded else "FAILED")
        run.finished_at = datetime.now(timezone.utc)
        run.items_processed = processed
        run.items_added = succeeded
        run.errors = failed
        workers = db.query(AgentWorker).filter(AgentWorker.queue_type == QUEUE_TYPE).all()
        remaining = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "PENDING").count()
        for worker in workers:
            worker.last_run = datetime.now(timezone.utc)
            worker.status = "IDLE" if remaining == 0 else "QUEUED"
            worker.items_processed = int(worker.items_processed or 0) + processed
            worker.items_added = int(worker.items_added or 0) + succeeded
            worker.errors = int(worker.errors or 0) + failed
        db.commit()
        return {"status": run.status, "processed": processed, "succeeded": succeeded, "failed": failed, "remaining": remaining, "market": "las-vegas"}
    finally:
        db.close()
        _RUN_LOCK.release()


if __name__ == "__main__":
    print(json.dumps(process_pending_decision_research(), sort_keys=True))
