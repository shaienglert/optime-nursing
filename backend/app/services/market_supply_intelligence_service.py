from __future__ import annotations

"""Weekly market-supply intelligence -- part of the Competitive Intelligence Agent's
scope (same AGENT_KEY, same AgentWorker/AgentJobRun/AgentKnowledgeRecord identity as
competitive_intelligence_service.py), but on its own weekly schedule: construction
starts, planned/actual facility openings, and reported occupancy rates don't move on
a 6-hour cadence the way a competitor's homepage copy might.

This is a best-effort weekly news digest, not a comprehensive permit database or a
NIC MAP subscription feed -- it finds real, live search results for a small set of
targeted industry queries, fetches the real article, and extracts only sentences
that actually contain the relevant keywords, with the real source URL attached. If a
week turns up nothing for a category, that is reported as exactly that -- zero
results is a true finding, not a fetch failure to paper over.

City/state extraction is a bounded regex heuristic ("City, ST" or "City, State
Name" patterns actually present in the text), not real NLP/NER -- it filters out
the most obvious false positives (street-address fragments, generic words) but can
still miss a real city or occasionally mislabel one. Treat city_state as a
best-effort pointer to go verify against source_url, not a guaranteed-accurate
structured field.
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
from app.models.competitive_intelligence import MarketSupplySignal
from app.services.competitive_intelligence_service import AGENT_KEY, _visible_text
from app.services.decision_research_worker import _fetch, _search_result_urls

logger = logging.getLogger(__name__)

_COMPETITOR_PLACEMENT_DOMAINS = (
    "aplaceformom.com",
    "caring.com",
    "seniorly.com",
)

# This list is intentionally separate from the general low-quality/social-source
# filter below.  Competitor sites may be observed by the dedicated competitive
# intelligence service, but they must never become evidence for an OPTIME article,
# market metric, facility claim, or recommendation.
_SKIP_DOMAINS = _COMPETITOR_PLACEMENT_DOMAINS + (
    "yelp.com", "facebook.com",
    "instagram.com", "linkedin.com", "youtube.com", "google.com", "pinterest.com",
    "indeed.com", "glassdoor.com", "reddit.com", "wikipedia.org",
)


def is_disallowed_article_source(url: str) -> bool:
    """Return whether a URL is barred from evidence or editorial use.

    Placement competitors are deliberately not a source class.  Their public
    pages can be monitored only by ``competitive_intelligence_service`` for
    competitor-change observation; they cannot support a factual claim anywhere
    customer-facing or decision-making.
    """
    domain = urlparse(url).netloc.lower().split(":", 1)[0]
    return bool(domain) and any(
        domain == blocked or domain.endswith(f".{blocked}")
        for blocked in _COMPETITOR_PLACEMENT_DOMAINS
    )

_MAX_RESULTS_PER_QUERY = 5

QUERIES: List[Dict[str, str]] = [
    {
        "category": "CONSTRUCTION_START",
        "query": "senior living community broke ground construction 2026",
        "keywords": ["broke ground", "groundbreaking", "began construction", "construction began", "construction is underway", "topped out"],
    },
    {
        "category": "PLANNED_OPENING",
        "query": "senior living community grand opening 2026",
        "keywords": ["grand opening", "now open", "opens its doors", "set to open", "opening in", "will open", "opened this"],
    },
    {
        "category": "OCCUPANCY_RATE",
        "query": "senior housing occupancy rate report 2026",
        "keywords": ["occupancy rate", "occupancy reached", "occupancy increased", "occupancy climbed", "percent occupied", "% occupied"],
    },
]

_US_STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC",
}
# Longest names first so "New York" matches before a hypothetical shorter overlapping name would.
_STATE_NAME_ALTERNATION = "|".join(re.escape(name) for name in sorted(_US_STATE_ABBR, key=len, reverse=True))

# "Austin, TX" -- a two-letter postal abbreviation right after the city.
_CITY_STATE_ABBR_RE = re.compile(r"\b([A-Z][a-zA-Z.]+(?:\s[A-Z][a-zA-Z.]+){0,2}),\s([A-Z]{2})\b")
# "Wapakoneta, Ohio" -- the far more common style in local/trade news, spelled out.
_CITY_STATE_NAME_RE = re.compile(
    rf"\b([A-Z][a-zA-Z.]+(?:\s[A-Z][a-zA-Z.]+){{0,2}}),\s({_STATE_NAME_ALTERNATION})\b"
)


@dataclass
class MarketSupplyItem:
    category: str
    headline: str
    snippet: str
    city_state: Optional[str]
    market_key: Optional[str]
    project_name: Optional[str]
    service_lines: Optional[str]
    units_or_beds: Optional[int]
    expected_opening: Optional[str]
    occupancy_rate: Optional[str]
    occupancy_period: Optional[str]
    evidence_status: str
    nursing_relevance: str
    source_url: str
    source_domain: str


def _sentence_with_keyword(text: str, keyword: str, radius: int = 140) -> Optional[str]:
    idx = text.lower().find(keyword.lower())
    if idx < 0:
        return None
    start = max(0, idx - radius)
    end = min(len(text), idx + len(keyword) + radius)
    return text[start:end].strip()


_NOT_A_CITY_WORDS = {
    "total", "approach", "report", "overview", "summary", "update", "news", "market",
    "senior", "living", "the", "grand", "phase", "state", "national", "overall",
    "google", "maps", "map", "view", "photo", "image", "source",
}
_STREET_SUFFIXES = {"ave", "ave.", "st", "st.", "rd", "rd.", "blvd", "blvd.", "dr", "dr.", "ln", "ln.", "ct", "ct.", "way"}
_VALID_STATE_ABBRS = set(_US_STATE_ABBR.values())


def _looks_like_city(candidate: str) -> bool:
    if any(ch.isdigit() for ch in candidate):
        return False
    words = [w.lower().rstrip(".,") for w in candidate.strip().split()]
    if any(w in _STREET_SUFFIXES or w in _NOT_A_CITY_WORDS for w in words):
        return False
    return True


def _find_city_state(text: str) -> Optional[str]:
    for match in _CITY_STATE_ABBR_RE.finditer(text):
        city, abbr = match.group(1).strip(), match.group(2)
        if abbr in _VALID_STATE_ABBRS and _looks_like_city(city):
            return f"{city}, {abbr}"
    for match in _CITY_STATE_NAME_RE.finditer(text):
        city = match.group(1).strip()
        if _looks_like_city(city):
            return f"{city}, {_US_STATE_ABBR[match.group(2)]}"
    return None


def _headline_from_html(html: str) -> str:
    from app.services.competitive_intelligence_service import _TITLE_RE, _STRIP_RE

    match = _TITLE_RE.search(html)
    if not match:
        return "(no page title found)"
    return _STRIP_RE.sub(" ", match.group(1)).strip()[:200] or "(no page title found)"


_UNITS_RE = re.compile(r"\b(\d{1,4})[- ]?(?:unit|units|bed|beds|residences)\b", re.IGNORECASE)
_OPENING_RE = re.compile(r"\b(?:open(?:ing|ed)?|completion|complete(?:d)?|move-?ins?)\b[^.]{0,100}?\b((?:early|late|spring|summer|fall|winter|Q[1-4])?\s*20\d{2})\b", re.IGNORECASE)
_OCCUPANCY_RE = re.compile(r"\boccupancy(?:\s+(?:rate|reached|rose|climbed|was))?[^.%]{0,70}?(\d{1,3}(?:\.\d+)?)\s*%", re.IGNORECASE)
_PERIOD_RE = re.compile(r"\b(?:Q[1-4]|first|second|third|fourth)\s+(?:quarter\s+(?:of\s+)?)?(20\d{2})\b", re.IGNORECASE)
_LAS_VEGAS_MARKET_TERMS = ("las vegas", "north las vegas", "henderson", "summerlin", "clark county")


def _project_name_from_headline(headline: str) -> Optional[str]:
    """A conservative label for the report, not a claimed facility identity."""
    cleaned = re.sub(r"\s*[|–—-]\s*[^|–—-]+$", "", headline).strip()
    if len(cleaned) < 4 or "senior" not in cleaned.lower():
        return None
    return cleaned[:300]


def _service_lines(text: str) -> Optional[str]:
    labels = []
    for phrase, label in (("skilled nursing", "SKILLED_NURSING"), ("assisted living", "ASSISTED_LIVING"), ("memory care", "MEMORY_CARE"), ("independent living", "INDEPENDENT_LIVING"), ("active adult", "ACTIVE_ADULT"), ("affordable", "AFFORDABLE_SENIOR_HOUSING")):
        if phrase in text.lower():
            labels.append(label)
    return ",".join(labels) if labels else None


def _nursing_relevance(lines: Optional[str]) -> str:
    if not lines:
        return "UNCLASSIFIED"
    if any(value in lines for value in ("SKILLED_NURSING", "ASSISTED_LIVING", "MEMORY_CARE")):
        return "DIRECT_CARE_RELEVANT"
    return "SENIOR_HOUSING_CONTEXT_ONLY"


def _extract_market_supply_items(*, category: str, keywords: List[str], url: str, html: str, market_key: Optional[str] = None) -> List[MarketSupplyItem]:
    text = _visible_text(html)
    headline = _headline_from_html(html)
    domain = urlparse(url).netloc.lower()
    items: List[MarketSupplyItem] = []
    for keyword in keywords:
        snippet = _sentence_with_keyword(text, keyword)
        if not snippet:
            continue
        context = f"{headline}. {snippet}. {text[:5000]}"
        city_state = _find_city_state(headline) or _find_city_state(snippet) or _find_city_state(text[:4000])
        # A targeted pilot must not silently accept a national result merely because
        # the search engine returned it.  If the actual source does not name the
        # Las Vegas metro, it is excluded rather than guessed into the market.
        if market_key == "LAS_VEGAS_METRO" and not any(term in context.lower() for term in _LAS_VEGAS_MARKET_TERMS):
            continue
        service_lines = _service_lines(context)
        units_match = _UNITS_RE.search(context)
        opening_match = _OPENING_RE.search(context)
        occupancy_match = _OCCUPANCY_RE.search(context)
        period_match = _PERIOD_RE.search(context)
        items.append(
            MarketSupplyItem(
                category=category,
                headline=headline,
                snippet=snippet,
                city_state=city_state,
                market_key=market_key,
                project_name=_project_name_from_headline(headline),
                service_lines=service_lines,
                units_or_beds=int(units_match.group(1)) if units_match else None,
                expected_opening=opening_match.group(1).strip() if opening_match else None,
                occupancy_rate=f"{occupancy_match.group(1)}%" if occupancy_match else None,
                occupancy_period=(f"Q{period_match.group(0)[1]} {period_match.group(1)}" if period_match and period_match.group(0).upper().startswith("Q") else period_match.group(0) if period_match else None),
                evidence_status="REPORTED",
                nursing_relevance=_nursing_relevance(service_lines),
                source_url=url,
                source_domain=domain,
            )
        )
        break  # one representative snippet per article is enough; avoid near-duplicate rows from the same page
    return items


def _persist_item(db: Session, item: MarketSupplyItem) -> bool:
    """Returns True if this was a genuinely new item (not a re-seen URL)."""
    existing = db.query(MarketSupplySignal).filter(
        MarketSupplySignal.source_url == item.source_url,
        MarketSupplySignal.category == item.category,
    ).all()
    if any((row.market_key or None) == item.market_key for row in existing):
        return False
    db.add(
        MarketSupplySignal(
            category=item.category,
            headline=item.headline,
            snippet=item.snippet,
            city_state=item.city_state,
            market_key=item.market_key,
            project_name=item.project_name,
            service_lines=item.service_lines,
            units_or_beds=item.units_or_beds,
            expected_opening=item.expected_opening,
            occupancy_rate=item.occupancy_rate,
            occupancy_period=item.occupancy_period,
            evidence_status=item.evidence_status,
            nursing_relevance=item.nursing_relevance,
            source_url=item.source_url,
            source_domain=item.source_domain,
        )
    )
    return True


LAS_VEGAS_QUERIES: List[Dict[str, str]] = [
    {"category": "CONSTRUCTION_START", "query": "Las Vegas Henderson North Las Vegas senior living broke ground construction 2026", "keywords": QUERIES[0]["keywords"]},
    {"category": "PLANNED_OPENING", "query": "Las Vegas Henderson North Las Vegas senior living planned opening 2026 2027 2028", "keywords": QUERIES[1]["keywords"]},
    {"category": "OCCUPANCY_RATE", "query": "Las Vegas senior housing occupancy rate NIC MAP 2026", "keywords": QUERIES[2]["keywords"]},
]


def run_market_supply_intelligence_cycle(db: Session, *, query_specs: Optional[List[Dict[str, str]]] = None, market_key: Optional[str] = None) -> Dict[str, object]:
    started_at = datetime.now(timezone.utc)
    job = AgentJobRun(agent_key=AGENT_KEY, status="RUNNING")
    db.add(job)
    db.commit()
    db.refresh(job)

    items_added = 0
    errors = 0
    category_results: List[Dict[str, object]] = []

    specs = query_specs or QUERIES
    for spec in specs:
        category = spec["category"]
        query = spec["query"]
        keywords = spec["keywords"]
        found_this_category: List[Dict[str, str]] = []

        try:
            candidates = _search_result_urls(query)
        except Exception as exc:  # pragma: no cover - network failure path
            errors += 1
            category_results.append({"category": category, "query": query, "error": str(exc), "items": []})
            continue

        checked = 0
        for url, _anchor in candidates:
            if checked >= _MAX_RESULTS_PER_QUERY:
                break
            domain = urlparse(url).netloc.lower()
            if (
                not domain
                or is_disallowed_article_source(url)
                or any(domain == skip or domain.endswith(f".{skip}") for skip in _SKIP_DOMAINS)
            ):
                continue
            checked += 1
            try:
                html, status = _fetch(url)
            except Exception:
                errors += 1
                continue
            time.sleep(1)  # be a polite, low-volume, infrequent visitor
            if status != 200:
                continue

            extracted = _extract_market_supply_items(category=category, keywords=keywords, url=url, html=html, market_key=market_key)
            for item in extracted:
                is_new = _persist_item(db, item)
                if is_new:
                    items_added += 1
                    found_this_category.append({"headline": item.headline, "city_state": item.city_state or "", "source_url": item.source_url})

        category_results.append({"category": category, "query": query, "items": found_this_category})

    finished_at = datetime.now(timezone.utc)
    runtime_ms = int((finished_at - started_at).total_seconds() * 1000)

    summary = "; ".join(
        f"{row['category']}: {len(row['items'])} new item(s)" if not row.get("error") else f"{row['category']}: search failed"
        for row in category_results
    )

    db.add(
        AgentKnowledgeRecord(
            agent_key=AGENT_KEY,
            record_type="market_supply_intelligence_cycle",
            entity_key=started_at.date().isoformat(),
            summary=summary,
            payload_json=_payload_json(category_results),
            confidence=0.6 if errors == 0 else max(0.25, 0.6 - 0.15 * errors),
            source="LIVE_WEB_SEARCH",
        )
    )

    job.status = "SUCCESS" if errors < len(QUERIES) else "FAILED"
    job.finished_at = finished_at
    job.runtime_ms = runtime_ms
    job.items_processed = len(QUERIES)
    job.items_added = items_added
    job.items_updated = 0
    job.errors = errors

    worker = db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).first()
    if worker is not None:
        worker.last_run = finished_at
        worker.items_added = (worker.items_added or 0) + items_added
        worker.errors = (worker.errors or 0) + errors
        worker.knowledge_records = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).count()

    db.commit()

    return {
        "market_key": market_key,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "runtime_ms": runtime_ms,
        "items_added": items_added,
        "errors": errors,
        "categories": category_results,
    }


def run_las_vegas_market_supply_pilot(db: Session) -> Dict[str, object]:
    """Targeted, structured research cycle for the Las Vegas metro pilot."""
    return run_market_supply_intelligence_cycle(db, query_specs=LAS_VEGAS_QUERIES, market_key="LAS_VEGAS_METRO")


def _payload_json(category_results: List[Dict[str, object]]) -> str:
    import json

    return json.dumps({"categories": category_results}, default=str)


def latest_market_supply_signals(db: Session, limit: int = 100) -> List[MarketSupplySignal]:
    return (
        db.query(MarketSupplySignal)
        .order_by(MarketSupplySignal.first_observed_at.desc())
        .limit(limit)
        .all()
    )


_DEFAULT_WEEKLY_INTERVAL_SECONDS = 7 * 24 * 60 * 60


def start_market_supply_intelligence_scheduler() -> None:
    """Separate weekly-cadence thread, same shape as competitive_intelligence_
    service.start_competitive_intelligence_scheduler. Configurable via
    OPTIME_MARKET_SUPPLY_INTERVAL_SECONDS (default 7 days)."""
    import os
    import threading

    interval = max(3600, int(os.getenv("OPTIME_MARKET_SUPPLY_INTERVAL_SECONDS", str(_DEFAULT_WEEKLY_INTERVAL_SECONDS))))

    def _runner() -> None:
        from app.database import SessionLocal

        while True:
            try:
                with SessionLocal() as db:
                    result = run_market_supply_intelligence_cycle(db)
                    logger.info(
                        "market_supply_intelligence_cycle_completed added=%s errors=%s",
                        result["items_added"],
                        result["errors"],
                    )
            except Exception:
                logger.exception("market_supply_intelligence_cycle_failed")
            time.sleep(interval)

    thread = threading.Thread(target=_runner, name="optime-market-supply-intelligence", daemon=True)
    thread.start()
