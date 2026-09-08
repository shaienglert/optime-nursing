from __future__ import annotations

"""Competitive Intelligence Agent -- real v1, not the full 17-section spec in
docs/agent_specs/competitive_intelligence_agent_spec.md (that spec's Ask/Search/
Explain/Verify API surface and knowledge-graph relationships are future work; this
is the first real, running slice of it).

What this actually does, every cycle: fetches each named competitor's public
homepage (live HTTP, reusing decision_research_worker.py's _fetch primitive -- no
new scraping stack), and extracts only what's literally present in that page's own
text -- monetization language, scale claims (numbers next to relevant words),
feature mentions, and the page's own headline copy. Nothing here is inferred,
estimated, or filled in from prior knowledge of these companies; a fetch failure or
an unmatched pattern is recorded as exactly that, not skipped silently.

Change detection is real, not fabricated: each (competitor, signal_type) has one
live row in competitive_intelligence_signals. A cycle can only ever report one of
three honest states for a given signal -- newly observed (no prior row), unchanged
(content hash matches), or changed (hash differs, both old and new text kept
nowhere but the current row, which is deliberately fine: the point is knowing THAT
something moved, not diffing every past revision).
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentWorker
from app.models.competitive_intelligence import CompetitiveIntelligenceSignal
from app.services.decision_research_worker import _fetch

logger = logging.getLogger(__name__)

AGENT_KEY = "competitive_intelligence"

COMPETITORS: List[Dict[str, str]] = [
    {"key": "a_place_for_mom", "name": "A Place for Mom", "url": "https://www.aplaceformom.com/"},
    {"key": "caring_com", "name": "Caring.com", "url": "https://www.caring.com/"},
    {"key": "seniorly", "name": "Seniorly", "url": "https://www.seniorly.com/"},
]

_MONETIZATION_PHRASES = (
    "at no cost", "free for families", "free service", "no cost to you", "no cost to families",
    "paid by", "compensated by", "we are compensated", "referral fee", "advertise with us",
    "sponsored", "our fees are paid", "communities pay", "senior living communities compensate",
)

_FEATURE_KEYWORDS = (
    "compare", "pricing", "cost calculator", "photos", "availability", "reviews",
    "schedule a tour", "book a tour", "talk to an advisor", "local advisor", "free consultation",
)

_SCALE_PATTERN = re.compile(
    r"([\d][\d,]{2,9})\s*\+?\s*(communities|senior living communities|reviews|families|advisors|providers)",
    re.IGNORECASE,
)

_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_STRIP_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)


def _visible_text(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    text = _STRIP_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _first_match_text(pattern: re.Pattern, html: str) -> Optional[str]:
    match = pattern.search(html)
    if not match:
        return None
    return _STRIP_RE.sub(" ", match.group(1)).strip()[:200] or None


def _snippet_around(text: str, phrase: str, radius: int = 60) -> str:
    idx = text.lower().find(phrase.lower())
    if idx < 0:
        return phrase
    start = max(0, idx - radius)
    end = min(len(text), idx + len(phrase) + radius)
    return text[start:end].strip()


@dataclass
class ExtractedSignal:
    signal_type: str
    detail_text: str


@dataclass
class CompetitorCycleResult:
    competitor_key: str
    competitor_name: str
    source_url: str
    fetch_ok: bool
    http_status: Optional[int]
    signals: List[ExtractedSignal] = field(default_factory=list)
    error: Optional[str] = None


def extract_signals(html: str) -> List[ExtractedSignal]:
    text = _visible_text(html)
    lower = text.lower()
    signals: List[ExtractedSignal] = []

    headline = _first_match_text(_H1_RE, html) or _first_match_text(_TITLE_RE, html)
    if headline:
        signals.append(ExtractedSignal("positioning_headline", headline))

    found_monetization = [phrase for phrase in _MONETIZATION_PHRASES if phrase in lower]
    if found_monetization:
        signals.append(
            ExtractedSignal(
                "monetization_language",
                "; ".join(_snippet_around(text, phrase) for phrase in found_monetization[:3]),
            )
        )

    found_features = sorted({kw for kw in _FEATURE_KEYWORDS if kw in lower})
    if found_features:
        signals.append(ExtractedSignal("feature_mentions", ", ".join(found_features)))

    scale_matches = _SCALE_PATTERN.findall(text)
    if scale_matches:
        seen = []
        for number, unit in scale_matches[:5]:
            entry = f"{number} {unit}"
            if entry not in seen:
                seen.append(entry)
        signals.append(ExtractedSignal("scale_claims", "; ".join(seen)))

    return signals


def _content_hash(detail_text: str) -> str:
    return hashlib.sha256(detail_text.encode("utf-8")).hexdigest()


def _apply_signal(db: Session, *, competitor_key: str, competitor_name: str, source_url: str, signal: ExtractedSignal) -> str:
    """Returns one of: NEW, CHANGED, UNCHANGED."""
    existing = (
        db.query(CompetitiveIntelligenceSignal)
        .filter(
            CompetitiveIntelligenceSignal.competitor_key == competitor_key,
            CompetitiveIntelligenceSignal.signal_type == signal.signal_type,
        )
        .first()
    )
    new_hash = _content_hash(signal.detail_text)
    now = datetime.now(timezone.utc)

    if existing is None:
        db.add(
            CompetitiveIntelligenceSignal(
                competitor_key=competitor_key,
                competitor_name=competitor_name,
                signal_type=signal.signal_type,
                source_url=source_url,
                detail_text=signal.detail_text,
                content_hash=new_hash,
            )
        )
        return "NEW"

    if existing.content_hash == new_hash:
        existing.last_observed_at = now
        return "UNCHANGED"

    existing.detail_text = signal.detail_text
    existing.content_hash = new_hash
    existing.source_url = source_url
    existing.last_observed_at = now
    existing.last_changed_at = now
    return "CHANGED"


def run_competitive_intelligence_cycle(db: Session) -> Dict[str, object]:
    """The whole agent, one cycle. Called both by the background scheduler and for
    an on-demand manual run -- identical code path either way, no separate 'test
    mode' that could silently drift from what actually runs unattended."""
    started_at = datetime.now(timezone.utc)
    job = AgentJobRun(agent_key=AGENT_KEY, status="RUNNING")
    db.add(job)
    db.commit()
    db.refresh(job)

    results: List[CompetitorCycleResult] = []
    items_added = 0
    items_updated = 0
    errors = 0

    for competitor in COMPETITORS:
        url = competitor["url"]
        try:
            html, status = _fetch(url)
        except Exception as exc:  # pragma: no cover - network failure path
            errors += 1
            results.append(
                CompetitorCycleResult(
                    competitor_key=competitor["key"],
                    competitor_name=competitor["name"],
                    source_url=url,
                    fetch_ok=False,
                    http_status=None,
                    error=str(exc),
                )
            )
            continue

        if status != 200:
            errors += 1
            results.append(
                CompetitorCycleResult(
                    competitor_key=competitor["key"],
                    competitor_name=competitor["name"],
                    source_url=url,
                    fetch_ok=False,
                    http_status=status,
                    error=f"HTTP {status}",
                )
            )
            continue

        extracted = extract_signals(html)
        result = CompetitorCycleResult(
            competitor_key=competitor["key"],
            competitor_name=competitor["name"],
            source_url=url,
            fetch_ok=True,
            http_status=status,
            signals=extracted,
        )
        results.append(result)

        for signal in extracted:
            outcome = _apply_signal(
                db,
                competitor_key=competitor["key"],
                competitor_name=competitor["name"],
                source_url=url,
                signal=signal,
            )
            if outcome == "NEW":
                items_added += 1
            elif outcome == "CHANGED":
                items_updated += 1

        time.sleep(1)  # be a polite, low-volume, infrequent visitor to these sites

    finished_at = datetime.now(timezone.utc)
    runtime_ms = int((finished_at - started_at).total_seconds() * 1000)

    summary_lines = []
    for result in results:
        if not result.fetch_ok:
            summary_lines.append(f"{result.competitor_name}: fetch failed ({result.error})")
        else:
            summary_lines.append(f"{result.competitor_name}: {len(result.signals)} signal type(s) observed")
    summary = "; ".join(summary_lines) or "No competitors configured"

    db.add(
        AgentKnowledgeRecord(
            agent_key=AGENT_KEY,
            record_type="competitive_intelligence_cycle",
            entity_key=started_at.date().isoformat(),
            summary=summary,
            payload_json=_cycle_payload_json(results),
            confidence=0.7 if errors == 0 else max(0.3, 0.7 - 0.15 * errors),
            source="LIVE_WEB_FETCH",
        )
    )

    job.status = "SUCCESS" if errors < len(COMPETITORS) else "FAILED"
    job.finished_at = finished_at
    job.runtime_ms = runtime_ms
    job.items_processed = len(COMPETITORS)
    job.items_added = items_added
    job.items_updated = items_updated
    job.errors = errors

    worker = db.query(AgentWorker).filter(AgentWorker.agent_key == AGENT_KEY).first()
    if worker is None:
        worker = AgentWorker(
            agent_key=AGENT_KEY,
            name="Competitive Intelligence Agent",
            mission="Track named competitors' public positioning, monetization language, feature surface, and scale claims.",
            data_sources="[\"aplaceformom.com\", \"caring.com\", \"seniorly.com\"]",
            queue_type="competitive_intelligence",
        )
        db.add(worker)
    worker.status = "IDLE"
    worker.last_run = finished_at
    worker.next_run = None  # set by the scheduler loop, not stored here
    worker.runtime_ms = runtime_ms
    worker.items_processed = len(COMPETITORS)
    worker.items_added = items_added
    worker.items_updated = items_updated
    worker.errors = errors
    worker.knowledge_records = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == AGENT_KEY).count()

    db.commit()

    return {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "runtime_ms": runtime_ms,
        "items_added": items_added,
        "items_updated": items_updated,
        "errors": errors,
        "results": [
            {
                "competitor_key": r.competitor_key,
                "competitor_name": r.competitor_name,
                "source_url": r.source_url,
                "fetch_ok": r.fetch_ok,
                "http_status": r.http_status,
                "error": r.error,
                "signals": [{"signal_type": s.signal_type, "detail_text": s.detail_text} for s in r.signals],
            }
            for r in results
        ],
    }


def _cycle_payload_json(results: List[CompetitorCycleResult]) -> str:
    import json

    return json.dumps(
        {
            "results": [
                {
                    "competitor_key": r.competitor_key,
                    "fetch_ok": r.fetch_ok,
                    "http_status": r.http_status,
                    "error": r.error,
                    "signal_count": len(r.signals),
                }
                for r in results
            ]
        }
    )


def latest_signals(db: Session) -> List[CompetitiveIntelligenceSignal]:
    return db.query(CompetitiveIntelligenceSignal).order_by(
        CompetitiveIntelligenceSignal.competitor_key, CompetitiveIntelligenceSignal.signal_type
    ).all()


_DEFAULT_INTERVAL_SECONDS = 6 * 60 * 60


def start_competitive_intelligence_scheduler() -> None:
    """Background daemon thread, same shape as chief_ai_supervisor.start_supervisor_
    scheduler: runs for as long as the FastAPI process is alive, on an interval
    configurable via OPTIME_COMPETITIVE_INTEL_INTERVAL_SECONDS (default 6 hours).
    A failed cycle is logged and the loop keeps going -- one bad fetch must not kill
    the schedule.
    """
    import os
    import threading

    interval = max(300, int(os.getenv("OPTIME_COMPETITIVE_INTEL_INTERVAL_SECONDS", str(_DEFAULT_INTERVAL_SECONDS))))

    def _runner() -> None:
        from app.database import SessionLocal

        while True:
            try:
                with SessionLocal() as db:
                    result = run_competitive_intelligence_cycle(db)
                    logger.info(
                        "competitive_intelligence_cycle_completed added=%s updated=%s errors=%s",
                        result["items_added"],
                        result["items_updated"],
                        result["errors"],
                    )
            except Exception:
                logger.exception("competitive_intelligence_cycle_failed")
            time.sleep(interval)

    thread = threading.Thread(target=_runner, name="optime-competitive-intelligence", daemon=True)
    thread.start()
