from __future__ import annotations

"""Monthly competitor structural research -- part of the Competitive Intelligence
Agent's scope (same AGENT_KEY, same AgentWorker/AgentJobRun/AgentKnowledgeRecord
identity as competitive_intelligence_service.py and market_supply_intelligence_
service.py), but answering a different question than either of those.

competitive_intelligence_service.py tracks WHAT CHANGED on each competitor's own
homepage (positioning, monetization language, feature list). This module researches
what the homepage doesn't say: how the service actually operates (the client-facing
process), how big/established the organization is, and who owns or backs it. Pricing
and commission structure are explicitly out of scope -- OPTIME's own placement-fee
mechanics (see placement_referral_service.py) don't depend on what competitors
charge, so that isn't worth the research budget here.

Same honesty rule as the rest of this agent family: a category with no real,
sourced result for a competitor this month is recorded as exactly that -- "not
found" is a true finding, never silently skipped or guessed at from general
background knowledge.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
from app.services.competitive_intelligence_service import (
    AGENT_KEY,
    COMPETITORS,
    ExtractedSignal,
    _apply_signal,
    _visible_text,
    startup_delay_seconds,
)
from app.services.decision_research_worker import _fetch, _search_result_urls

logger = logging.getLogger(__name__)

_MAX_RESULTS_PER_QUERY = 5

# Sources that are never a legitimate basis for a structural claim about a company
# -- social/job/media-hosting platforms, not company or press information. Unlike
# market_supply_intelligence_service, third-party coverage (news, Wikipedia,
# Crunchbase-style profiles) is explicitly *not* excluded here: for facts like
# ownership or headcount, independent coverage is often the only real source, since
# a company's own homepage rarely states who backs it.
_SKIP_DOMAINS = (
    "facebook.com", "instagram.com", "pinterest.com", "youtube.com",
    "indeed.com", "glassdoor.com", "yelp.com", "tiktok.com",
)

RESEARCH_CATEGORIES: List[Dict[str, object]] = [
    {
        "signal_type": "service_model_description",
        "query_suffix": "how it works senior living referral",
        "keywords": (
            "how it works", "we match", "connect you with", "connects families",
            "local advisor will", "personalized recommendations", "in-person tour",
            "narrow down", "compare options", "senior living advisor",
        ),
    },
    {
        "signal_type": "organizational_scale_disclosure",
        "query_suffix": "about us company history",
        "keywords": (
            "founded in", "headquartered", "offices in", "advisors nationwide",
            "team of", "employees", "years of experience", "serving families since",
            "founded by",
        ),
    },
    {
        "signal_type": "ownership_or_backing_disclosure",
        "query_suffix": "owned by parent company investors",
        "keywords": (
            "backed by", "owned by", "a subsidiary of", "part of the", "part of a family of",
            "investors include", "private equity", "acquired by", "parent company",
            "portfolio company",
        ),
    },
]


def _first_keyword_snippet(text: str, keywords: Tuple[str, ...], radius: int = 160) -> Optional[str]:
    lower = text.lower()
    for keyword in keywords:
        idx = lower.find(keyword.lower())
        if idx < 0:
            continue
        start = max(0, idx - radius)
        end = min(len(text), idx + len(keyword) + radius)
        return text[start:end].strip()
    return None


@dataclass
class CategoryResearchResult:
    signal_type: str
    query: str
    found: bool
    source_url: Optional[str] = None
    outcome: Optional[str] = None  # NEW, CHANGED, UNCHANGED
    error: Optional[str] = None


def _research_category(competitor_name: str, category: Dict[str, object]) -> Tuple[CategoryResearchResult, Optional[ExtractedSignal], Optional[str]]:
    """Returns (result, signal-if-found, source_url-if-found). Never raises for a
    plain 'not found this month' outcome -- only a genuine search failure is an
    error."""
    query = f'{competitor_name} {category["query_suffix"]}'
    try:
        candidates = _search_result_urls(query)
    except Exception as exc:  # pragma: no cover - network failure path
        return CategoryResearchResult(signal_type=category["signal_type"], query=query, found=False, error=str(exc)), None, None

    checked = 0
    for url, _anchor in candidates:
        if checked >= _MAX_RESULTS_PER_QUERY:
            break
        domain = urlparse(url).netloc.lower()
        if not domain or any(domain == skip or domain.endswith(f".{skip}") for skip in _SKIP_DOMAINS):
            continue
        checked += 1
        try:
            html, status = _fetch(url)
        except Exception:
            continue
        time.sleep(1)  # be a polite, low-volume, infrequent visitor
        if status != 200:
            continue
        snippet = _first_keyword_snippet(_visible_text(html), tuple(category["keywords"]))
        if snippet:
            return (
                CategoryResearchResult(signal_type=category["signal_type"], query=query, found=True, source_url=url),
                ExtractedSignal(category["signal_type"], snippet),
                url,
            )

    return CategoryResearchResult(signal_type=category["signal_type"], query=query, found=False), None, None


def run_competitor_structural_research_cycle(db: Session) -> Dict[str, object]:
    """The whole agent, one cycle. Same code path for the monthly scheduler and an
    on-demand manual run."""
    started_at = datetime.now(timezone.utc)
    job = AgentJobRun(agent_key=AGENT_KEY, status="RUNNING")
    db.add(job)
    db.commit()
    db.refresh(job)

    items_added = 0
    items_updated = 0
    errors = 0
    competitor_results: List[Dict[str, object]] = []

    for competitor in COMPETITORS:
        category_summaries: List[Dict[str, object]] = []
        for category in RESEARCH_CATEGORIES:
            result, signal, url = _research_category(competitor["name"], category)
            if result.error:
                errors += 1
            elif signal is not None and url is not None:
                outcome = _apply_signal(
                    db,
                    competitor_key=competitor["key"],
                    competitor_name=competitor["name"],
                    source_url=url,
                    signal=signal,
                )
                result.outcome = outcome
                if outcome == "NEW":
                    items_added += 1
                elif outcome == "CHANGED":
                    items_updated += 1
            category_summaries.append(
                {
                    "signal_type": result.signal_type,
                    "found": result.found,
                    "source_url": result.source_url,
                    "outcome": result.outcome,
                    "error": result.error,
                }
            )
        competitor_results.append({"competitor_key": competitor["key"], "competitor_name": competitor["name"], "categories": category_summaries})

    finished_at = datetime.now(timezone.utc)
    runtime_ms = int((finished_at - started_at).total_seconds() * 1000)

    summary_lines = []
    for row in competitor_results:
        found_count = sum(1 for c in row["categories"] if c["found"])
        summary_lines.append(f"{row['competitor_name']}: {found_count}/{len(RESEARCH_CATEGORIES)} categories found")
    summary = "; ".join(summary_lines) or "No competitors configured"

    total_categories = len(COMPETITORS) * len(RESEARCH_CATEGORIES)

    db.add(
        AgentKnowledgeRecord(
            agent_key=AGENT_KEY,
            record_type="competitor_structural_research_cycle",
            entity_key=started_at.date().isoformat(),
            summary=summary,
            payload_json=_payload_json(competitor_results),
            confidence=0.6 if errors == 0 else max(0.2, 0.6 - 0.15 * errors),
            source="LIVE_WEB_SEARCH",
        )
    )

    job.status = "SUCCESS" if errors < total_categories else "FAILED"
    job.finished_at = finished_at
    job.runtime_ms = runtime_ms
    job.items_processed = total_categories
    job.items_added = items_added
    job.items_updated = items_updated
    job.errors = errors

    worker = db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).first()
    if worker is not None:
        worker.last_run = finished_at
        worker.items_added = (worker.items_added or 0) + items_added
        worker.items_updated = (worker.items_updated or 0) + items_updated
        worker.errors = (worker.errors or 0) + errors
        worker.knowledge_records = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).count()

    db.commit()

    return {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "runtime_ms": runtime_ms,
        "items_added": items_added,
        "items_updated": items_updated,
        "errors": errors,
        "results": competitor_results,
    }


def _payload_json(competitor_results: List[Dict[str, object]]) -> str:
    import json

    return json.dumps({"competitors": competitor_results}, default=str)


_DEFAULT_MONTHLY_INTERVAL_SECONDS = 30 * 24 * 60 * 60


def start_competitor_structural_research_scheduler() -> None:
    """Background daemon thread, same shape as the other two schedulers in this
    agent family. Configurable via OPTIME_COMPETITOR_RESEARCH_INTERVAL_SECONDS
    (default 30 days).

    Built with the restart-resilience fix from day one (see
    competitive_intelligence_service.startup_delay_seconds): the first cycle in a
    given process only runs immediately if the last recorded cycle is already
    older than `interval` (or none exists yet), so a Render redeploy mid-month
    can't turn a monthly job into a frequent one.
    """
    import os
    import threading

    interval = max(3600, int(os.getenv("OPTIME_COMPETITOR_RESEARCH_INTERVAL_SECONDS", str(_DEFAULT_MONTHLY_INTERVAL_SECONDS))))

    def _runner() -> None:
        from app.database import SessionLocal

        try:
            delay = startup_delay_seconds("competitor_structural_research_cycle", interval)
            if delay > 0:
                logger.info("competitor_structural_research_cycle_deferred seconds=%s", delay)
                time.sleep(delay)
        except Exception:
            logger.exception("competitor_structural_research_startup_delay_check_failed")

        while True:
            try:
                with SessionLocal() as db:
                    result = run_competitor_structural_research_cycle(db)
                    logger.info(
                        "competitor_structural_research_cycle_completed added=%s updated=%s errors=%s",
                        result["items_added"],
                        result["items_updated"],
                        result["errors"],
                    )
            except Exception:
                logger.exception("competitor_structural_research_cycle_failed")
            time.sleep(interval)

    thread = threading.Thread(target=_runner, name="optime-competitor-structural-research", daemon=True)
    thread.start()
