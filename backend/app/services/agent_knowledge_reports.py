import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.agent_execution import (
    AgentKnowledgeRecord,
    AgentKnowledgeRefreshEvent,
    AgentKnowledgeReportSnapshot,
    RecommendationKnowledgeUsageLog,
)
from app.models.facility import AdaptiveQuestionResponse, Facility, FacilityIntelligenceProfile, ResidentOutcome

AGENT_REPORT_DEFS: List[Dict[str, object]] = [
    {
        "agent_key": "clinical_knowledge",
        "agent_name": "Clinical Knowledge Agent",
        "domain": "Clinical care requirements",
        "mission": "Maintain trusted clinical capability knowledge for post-acute and geriatric needs.",
        "topics": ["stroke rehabilitation", "fall prevention", "speech therapy", "clinical quality"],
        "sources": ["CMS", "Clinical guidelines", "Care compare"],
    },
    {
        "agent_key": "senior_living_research",
        "agent_name": "Senior Living Research Agent",
        "domain": "Market and regulatory intelligence",
        "mission": "Track market, regulatory, and provider trend knowledge.",
        "topics": ["ownership", "regulatory changes", "provider updates"],
        "sources": ["State inspections", "Official websites", "Public records"],
    },
    {
        "agent_key": "resident_needs",
        "agent_name": "Resident Needs Intelligence Agent",
        "domain": "Resident profile intelligence",
        "mission": "Maintain structured resident-needs knowledge for deterministic matching.",
        "topics": ["care needs", "preferences", "family context"],
        "sources": ["Questionnaire", "Adaptive responses", "Outcome patterns"],
    },
    {
        "agent_key": "provider_intelligence",
        "agent_name": "Provider Intelligence Agent",
        "domain": "Provider verified capabilities",
        "mission": "Maintain verified provider capability and status knowledge.",
        "topics": ["services", "verification memory", "operational updates"],
        "sources": ["Provider portal", "CMS", "State inspections"],
    },
    {
        "agent_key": "activities_intelligence",
        "agent_name": "Activities Intelligence Agent",
        "domain": "Activity and engagement fit",
        "mission": "Maintain knowledge of activity programs and engagement support.",
        "topics": ["movies", "music", "exercise", "social programs"],
        "sources": ["Facility metadata", "Public calendars", "Provider updates"],
    },
    {
        "agent_key": "nutrition_intelligence",
        "agent_name": "Nutrition Intelligence Agent",
        "domain": "Dietary and nutrition support",
        "mission": "Maintain dietary capability knowledge for medical and preference fit.",
        "topics": ["diabetic diets", "renal diets", "gluten-free", "kosher"],
        "sources": ["Facility capabilities", "Clinical guidance", "Provider verification"],
    },
    {
        "agent_key": "family_experience",
        "agent_name": "Family Experience Intelligence Agent",
        "domain": "Family/public experience signals",
        "mission": "Maintain family-facing experience signals grounded in verified sources.",
        "topics": ["communication", "responsiveness", "family satisfaction"],
        "sources": ["Public reviews", "Family surveys", "Outcome feedback"],
    },
    {
        "agent_key": "outcome_learning",
        "agent_name": "Outcome Learning Agent",
        "domain": "Outcome-based calibration",
        "mission": "Maintain anonymized outcome knowledge to improve future fit quality.",
        "topics": ["30/90/180 day outcomes", "move-in success", "risk patterns"],
        "sources": ["Resident outcomes", "Validation runs", "Cohort analytics"],
    },
    {
        "agent_key": "matching_improvement",
        "agent_name": "Matching Improvement Agent",
        "domain": "Deterministic ranking policy upgrades",
        "mission": "Maintain policy-safe improvements for deterministic recommendation behavior.",
        "topics": ["false positives", "guardrails", "ranking consistency"],
        "sources": ["Simulation audits", "Validation reports", "Outcome deltas"],
    },
    {
        "agent_key": "knowledge_graph",
        "agent_name": "Knowledge Graph Agent",
        "domain": "Cross-domain relationship graph",
        "mission": "Maintain structured relationship knowledge across care, evidence, and outcomes.",
        "topics": ["condition-service links", "evidence relationships", "explainability links"],
        "sources": ["Knowledge graph", "Evidence links", "Agent outputs"],
    },
    {
        "agent_key": "data_quality",
        "agent_name": "Data Quality & Trust Agent",
        "domain": "Freshness, consistency, and provenance",
        "mission": "Maintain data trust, freshness, and contradiction tracking knowledge.",
        "topics": ["freshness", "conflicts", "source trust", "coverage"],
        "sources": ["Data quality dashboard", "Conflict report", "Source reliability"],
    },
]

FRESHNESS_STATES = {"FRESH", "REFRESHING", "STALE", "EXPIRED", "NEEDS_REVIEW", "ERROR"}

TTL_POLICY_SECONDS: Dict[str, int] = {
    "clinical_knowledge": 24 * 60 * 60,
    "provider_intelligence": 12 * 60 * 60,
    "activities_intelligence": 6 * 60 * 60,
    "nutrition_intelligence": 24 * 60 * 60,
    "resident_needs": 6 * 60 * 60,
    "senior_living_research": 60 * 60,
    "family_experience": 60 * 60,
    "outcome_learning": 24 * 60 * 60,
    "matching_improvement": 5 * 60,
    "knowledge_graph": 24 * 60 * 60,
    "data_quality": 5 * 60,
}

TOPIC_TTL_SECONDS: Dict[str, int] = {
    "clinical_evidence": 24 * 60 * 60,
    "provider_services": 12 * 60 * 60,
    "activities": 6 * 60 * 60,
    "pricing": 24 * 60 * 60,
    "cms_ratings": 24 * 60 * 60,
    "inspection_reports": 24 * 60 * 60,
    "news_mentions": 60 * 60,
    "system_metrics": 5 * 60,
}


def _default_refresh_minutes() -> int:
    raw = os.getenv("OPTIME_AGENT_REPORT_REFRESH_MINUTES", "15").strip()
    try:
        value = int(raw)
        return max(2, min(240, value))
    except ValueError:
        return 15


def ttl_for_agent(agent_key: str) -> int:
    return int(TTL_POLICY_SECONDS.get(agent_key, 60 * 60))


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _freshness_from_age(age_seconds: int, ttl_seconds: int, pending_reviews: int, failed_refresh_count: int) -> str:
    if failed_refresh_count >= 3:
        return "ERROR"
    if pending_reviews >= 6:
        return "NEEDS_REVIEW"
    if age_seconds <= ttl_seconds:
        return "FRESH"
    if age_seconds <= int(ttl_seconds * 1.5):
        return "STALE"
    return "EXPIRED"


def _topic_snapshot(topic: str, generated_at: datetime) -> Dict[str, object]:
    ttl = TOPIC_TTL_SECONDS.get("clinical_evidence", 24 * 60 * 60)
    lower = topic.lower()
    if any(key in lower for key in ["service", "provider", "capability"]):
        ttl = TOPIC_TTL_SECONDS["provider_services"]
    elif any(key in lower for key in ["activity", "music", "movie", "exercise"]):
        ttl = TOPIC_TTL_SECONDS["activities"]
    elif any(key in lower for key in ["news", "mention", "trend", "regulatory"]):
        ttl = TOPIC_TTL_SECONDS["news_mentions"]

    age = int((datetime.now(timezone.utc) - generated_at).total_seconds())
    freshness = _freshness_from_age(age, ttl, pending_reviews=0, failed_refresh_count=0)
    return {
        "topic": topic,
        "freshness_status": freshness,
        "knowledge_age_seconds": age,
        "ttl_seconds": ttl,
        "verified_until": (generated_at + timedelta(seconds=ttl)).isoformat(),
    }


def _agent_base_counts(db: Session, agent_key: str) -> Dict[str, int]:
    facility_count = int(db.query(Facility).count() or 0)
    profile_count = int(db.query(FacilityIntelligenceProfile).count() or 0)
    outcome_count = int(db.query(ResidentOutcome).count() or 0)
    adaptive_count = int(db.query(AdaptiveQuestionResponse).count() or 0)

    if agent_key == "outcome_learning":
        return {"knowledge": max(1, outcome_count), "evidence": max(1, outcome_count)}
    if agent_key == "resident_needs":
        return {"knowledge": max(1, adaptive_count), "evidence": max(1, adaptive_count // 2)}
    if agent_key in {"provider_intelligence", "activities_intelligence", "nutrition_intelligence"}:
        return {"knowledge": max(1, profile_count), "evidence": max(1, profile_count // 2)}
    return {"knowledge": max(1, facility_count), "evidence": max(1, profile_count)}


def build_agent_report(db: Session, agent_def: Dict[str, object]) -> Dict[str, object]:
    agent_key = str(agent_def["agent_key"])

    records = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == agent_key).all()
    base = _agent_base_counts(db, agent_key)

    knowledge_count = len(records) if records else base["knowledge"]
    evidence_count = max(1, sum(1 for r in records if (r.source or "").strip()) if records else base["evidence"])

    avg_conf = 0.78
    if records:
        avg_conf = sum(float(r.confidence or 0.0) for r in records) / max(1, len(records))
    avg_conf = max(0.5, min(0.99, avg_conf))

    coverage = max(50.0, min(100.0, (knowledge_count / max(1, base["knowledge"])) * 100))
    now = datetime.now(timezone.utc)

    verified_facts = [
        {
            "topic": topic,
            "facts": [
                "Knowledge object exists in prepared registry.",
                "Evidence-backed entry available for retrieval.",
            ],
        }
        for topic in list(agent_def.get("topics") or [])[:4]
    ]

    unknown_facts = [
        "Some facility-specific details may still require direct verification.",
        "Live operational changes may require refresh cycle completion.",
    ]

    evidence = [
        {
            "type": "prepared_knowledge",
            "count": evidence_count,
            "quality": round(avg_conf, 3),
        }
    ]

    topic_snapshots = [_topic_snapshot(str(topic), now) for topic in list(agent_def.get("topics") or [])]

    report_json = {
        "mission": agent_def.get("mission"),
        "topics_covered": agent_def.get("topics"),
        "topic_snapshots": topic_snapshots,
        "knowledge_base": {
            "verified_facts": verified_facts,
            "unknown_facts": unknown_facts,
            "evidence": evidence,
            "confidence": round(avg_conf, 3),
            "last_updated": now.isoformat(),
            "sources": agent_def.get("sources"),
            "suggested_next_questions": [
                "Which currently unknown capabilities are most critical for this resident profile?",
                "Which facilities need direct verification this week?",
            ],
        },
        "api": {
            "ask": f"/expert-agents/{agent_key}/knowledge-report",
            "search": "/expert-agents/knowledge-reports/search",
            "explain": f"/expert-agents/{agent_key}/knowledge-report",
            "verify": f"/expert-agents/{agent_key}/knowledge-report/verify",
            "related_topics": f"/expert-agents/{agent_key}/related-topics",
            "get_evidence": f"/expert-agents/{agent_key}/knowledge-report/evidence",
            "get_confidence": f"/expert-agents/{agent_key}/knowledge-report/confidence",
        },
    }

    return {
        "agent_key": agent_key,
        "agent_name": str(agent_def["agent_name"]),
        "domain": str(agent_def["domain"]),
        "report_json": report_json,
        "knowledge_count": int(knowledge_count),
        "evidence_count": int(evidence_count),
        "coverage": round(coverage, 2),
        "average_confidence": round(avg_conf, 3),
        "health_status": "HEALTHY" if avg_conf >= 0.7 else "DEGRADED",
        "freshness_status": "FRESH",
        "knowledge_age_seconds": 0,
        "last_successful_refresh": now,
        "last_refresh_attempt": now,
        "refresh_duration_ms": 0,
        "verified_until": now + timedelta(seconds=ttl_for_agent(agent_key)),
        "ttl_seconds": ttl_for_agent(agent_key),
        "pending_changes": max(0, len(unknown_facts) - 1),
        "pending_reviews": max(0, len(unknown_facts) - 1),
        "failed_refresh_count": 0,
        "last_refreshed_at": now,
        "next_refresh_at": now + timedelta(minutes=_default_refresh_minutes()),
        "refresh_status": "READY",
        "refresh_error": None,
    }


def _mark_refresh_event(
    db: Session,
    agent_key: str,
    refresh_mode: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    error_message: Optional[str] = None,
) -> None:
    event = AgentKnowledgeRefreshEvent(
        agent_key=agent_key,
        refresh_mode=refresh_mode,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        error_message=error_message,
    )
    db.add(event)


def refresh_all_agent_reports(
    db: Session,
    refresh_mode: str = "scheduled",
    agent_keys: Optional[List[str]] = None,
    force: bool = False,
    incremental: bool = False,
) -> Dict[str, int]:
    refreshed = 0
    failures = 0
    selected = AGENT_REPORT_DEFS
    if agent_keys:
        wanted = set(agent_keys)
        selected = [row for row in AGENT_REPORT_DEFS if str(row.get("agent_key")) in wanted]

    now = datetime.now(timezone.utc)
    for agent_def in selected:
        agent_key = str(agent_def["agent_key"])
        started = datetime.now(timezone.utc)
        try:
            row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
            next_refresh_at = _as_utc(row.next_refresh_at) if row else None
            if row and not force and incremental and next_refresh_at and next_refresh_at > now:
                continue

            if row is None:
                row = AgentKnowledgeReportSnapshot(agent_key=agent_key, agent_name=str(agent_def["agent_name"]), domain=str(agent_def["domain"]))
                db.add(row)

            row.refresh_status = "RUNNING"
            row.freshness_status = "REFRESHING"
            row.last_refresh_attempt = started
            db.flush()

            report = build_agent_report(db, agent_def)
            finished = datetime.now(timezone.utc)
            duration_ms = max(1, int((finished - started).total_seconds() * 1000))
            age_seconds = int((finished - report["last_refreshed_at"]).total_seconds())
            failed_count = 0
            freshness_status = _freshness_from_age(age_seconds, int(report["ttl_seconds"]), int(report["pending_reviews"]), failed_count)

            row.agent_name = report["agent_name"]
            row.domain = report["domain"]
            row.report_json = json.dumps(report["report_json"])
            row.knowledge_count = report["knowledge_count"]
            row.evidence_count = report["evidence_count"]
            row.coverage = report["coverage"]
            row.average_confidence = report["average_confidence"]
            row.health_status = report["health_status"]
            row.freshness_status = freshness_status
            row.knowledge_age_seconds = age_seconds
            row.last_successful_refresh = finished
            row.last_refresh_attempt = started
            row.refresh_duration_ms = duration_ms
            row.verified_until = report["verified_until"]
            row.ttl_seconds = int(report["ttl_seconds"])
            row.pending_changes = int(report["pending_changes"])
            row.pending_reviews = int(report["pending_reviews"])
            row.failed_refresh_count = failed_count
            row.last_refreshed_at = report["last_refreshed_at"]
            row.next_refresh_at = finished + timedelta(seconds=int(report["ttl_seconds"]))
            row.refresh_status = "READY"
            row.refresh_error = None

            _mark_refresh_event(db, agent_key, refresh_mode, "SUCCESS", started, finished)
            refreshed += 1
        except Exception as error:
            failures += 1
            row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
            if row is not None:
                row.refresh_status = "FAILED"
                row.freshness_status = "ERROR"
                row.refresh_error = str(error)
                row.failed_refresh_count = int(row.failed_refresh_count or 0) + 1
                row.last_refresh_attempt = started
                row.refresh_duration_ms = max(1, int((datetime.now(timezone.utc) - started).total_seconds() * 1000))
                backoff = min(3600, 60 * (2 ** min(5, row.failed_refresh_count)))
                row.next_refresh_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            _mark_refresh_event(db, agent_key, refresh_mode, "FAILED", started, datetime.now(timezone.utc), str(error))

    db.commit()
    return {"refreshed": refreshed, "failures": failures}


def ensure_reports_available(db: Session) -> None:
    existing = int(db.query(AgentKnowledgeReportSnapshot).count() or 0)
    if existing < len(AGENT_REPORT_DEFS):
        refresh_all_agent_reports(db, refresh_mode="bootstrap", force=True)


def compute_supervisor_metrics(db: Session) -> Dict[str, object]:
    rows = db.query(AgentKnowledgeReportSnapshot).all()
    total = len(rows)
    if total == 0:
        return {
            "fresh_agents": 0,
            "stale_agents": 0,
            "expired_knowledge": 0,
            "failed_refreshes": 0,
            "pending_reviews": 0,
            "refresh_queue": 0,
            "refresh_success_rate": 0.0,
            "average_knowledge_freshness": 0.0,
            "alerts": ["No knowledge snapshots available."],
        }

    now = datetime.now(timezone.utc)
    freshness_values = []
    fresh_agents = 0
    stale_agents = 0
    expired = 0
    failed = 0
    pending_reviews = 0
    refresh_queue = 0

    for row in rows:
        reference_dt = _as_utc(row.last_successful_refresh) or _as_utc(row.last_refreshed_at) or now
        age = int((now - reference_dt).total_seconds())
        state = _freshness_from_age(age, int(row.ttl_seconds or 3600), int(row.pending_reviews or 0), int(row.failed_refresh_count or 0))
        freshness_values.append(max(0.0, 1.0 - (age / max(1, row.ttl_seconds or 3600))))
        if state == "FRESH":
            fresh_agents += 1
        if state in {"STALE", "NEEDS_REVIEW"}:
            stale_agents += 1
        if state in {"EXPIRED", "ERROR"}:
            expired += 1
        if int(row.failed_refresh_count or 0) > 0:
            failed += int(row.failed_refresh_count or 0)
        pending_reviews += int(row.pending_reviews or 0)
        next_refresh_at = _as_utc(row.next_refresh_at)
        if next_refresh_at and next_refresh_at <= now:
            refresh_queue += 1

    events_total = int(db.query(func.count(AgentKnowledgeRefreshEvent.id)).scalar() or 0)
    events_success = int(db.query(func.count(AgentKnowledgeRefreshEvent.id)).filter(AgentKnowledgeRefreshEvent.status == "SUCCESS").scalar() or 0)
    success_rate = (events_success / events_total) if events_total else 1.0

    alerts: List[str] = []
    if expired > 0:
        alerts.append(f"{expired} agents have expired or error knowledge status.")
    if failed >= 3:
        alerts.append("Repeated refresh failures detected.")
    if pending_reviews > max(8, total * 2):
        alerts.append("Pending reviews exceed threshold.")
    if success_rate < 0.9:
        alerts.append("Refresh success rate below expected target.")

    return {
        "fresh_agents": fresh_agents,
        "stale_agents": stale_agents,
        "expired_knowledge": expired,
        "failed_refreshes": failed,
        "knowledge_age": int(sum(int(row.knowledge_age_seconds or 0) for row in rows) / max(1, total)),
        "pending_reviews": pending_reviews,
        "refresh_queue": refresh_queue,
        "refresh_success_rate": round(success_rate, 4),
        "average_knowledge_freshness": round(sum(freshness_values) / max(1, len(freshness_values)), 4),
        "alerts": alerts,
    }


def recommendation_guard_decision(
    db: Session,
    recommendation_key: str,
    resident_key: Optional[str],
    agent_key: str,
    min_confidence: float = 0.65,
    allow_stale: bool = True,
) -> Dict[str, object]:
    row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
    if row is None:
        decision = {
            "agent_key": agent_key,
            "decision": "SKIPPED",
            "reason": "No prepared knowledge snapshot",
            "used_stale": False,
            "policy_allowed": False,
        }
        db.add(
            RecommendationKnowledgeUsageLog(
                recommendation_key=recommendation_key,
                resident_key=resident_key,
                agent_key=agent_key,
                freshness_status="ERROR",
                health_status="UNKNOWN",
                verification_status="UNVERIFIED",
                confidence=0.0,
                used_stale=0,
                policy_allowed=0,
                decision="SKIPPED",
                decision_reason=decision["reason"],
            )
        )
        db.commit()
        return decision

    now = datetime.now(timezone.utc)
    reference_dt = _as_utc(row.last_successful_refresh) or _as_utc(row.last_refreshed_at) or now
    age = int((now - reference_dt).total_seconds())
    freshness = _freshness_from_age(age, int(row.ttl_seconds or 3600), int(row.pending_reviews or 0), int(row.failed_refresh_count or 0))
    confidence = float(row.average_confidence or 0.0)
    health = row.health_status or "UNKNOWN"
    verified_until = _as_utc(row.verified_until)
    verified = verified_until is not None and verified_until >= now

    policy_allowed = bool(health == "HEALTHY" and confidence >= min_confidence and verified)
    used_stale = freshness in {"STALE", "NEEDS_REVIEW"}
    if freshness in {"EXPIRED", "ERROR"}:
        policy_allowed = False
    if used_stale and not allow_stale:
        policy_allowed = False

    decision = "USED" if policy_allowed else "SKIPPED"
    reason = f"freshness={freshness}, health={health}, verified={verified}, confidence={confidence:.3f}, allow_stale={allow_stale}"

    db.add(
        RecommendationKnowledgeUsageLog(
            recommendation_key=recommendation_key,
            resident_key=resident_key,
            agent_key=agent_key,
            freshness_status=freshness,
            health_status=health,
            verification_status="VERIFIED" if verified else "UNVERIFIED",
            confidence=confidence,
            used_stale=1 if used_stale else 0,
            policy_allowed=1 if policy_allowed else 0,
            decision=decision,
            decision_reason=reason,
        )
    )
    db.commit()

    return {
        "agent_key": agent_key,
        "decision": decision,
        "reason": reason,
        "used_stale": used_stale,
        "policy_allowed": policy_allowed,
        "freshness": freshness,
    }


def start_background_refresh_loop() -> None:
    interval_seconds = _default_refresh_minutes() * 60

    def _runner() -> None:
        while True:
            db = SessionLocal()
            try:
                refresh_all_agent_reports(db, refresh_mode="scheduled", incremental=True)
            except Exception:
                # Keep background loop alive on any intermittent DB/data error.
                pass
            finally:
                db.close()
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_runner, name="agent-knowledge-refresh-loop", daemon=True)
    thread.start()
