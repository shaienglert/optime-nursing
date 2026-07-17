import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agent_execution import (
    AgentKnowledgeRecord,
    AgentKnowledgeRefreshEvent,
    AgentKnowledgeReportSnapshot,
    RecommendationKnowledgeUsageLog,
    SupervisorIncidentLog,
)
from app.services.agent_knowledge_reports import compute_supervisor_metrics, refresh_all_agent_reports


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(row: AgentKnowledgeReportSnapshot, now: datetime) -> bool:
    verified_until = row.verified_until
    if verified_until is None:
        return True
    return verified_until < now


def _knowledge_age_seconds(row: AgentKnowledgeReportSnapshot, now: datetime) -> int:
    last = row.last_successful_refresh or row.last_refreshed_at or now
    return max(0, int((now - last).total_seconds()))


def _create_incident(
    db: Session,
    *,
    incident_type: str,
    severity: str,
    summary: str,
    agent_key: Optional[str] = None,
    domain: Optional[str] = None,
    details: Optional[Dict[str, object]] = None,
) -> None:
    incident = SupervisorIncidentLog(
        incident_type=incident_type,
        severity=severity,
        status="OPEN",
        agent_key=agent_key,
        domain=domain,
        summary=summary,
        details_json=json.dumps(details or {}),
    )
    db.add(incident)


def _detect_duplicate_knowledge(db: Session) -> List[Dict[str, object]]:
    duplicates = (
        db.query(
            AgentKnowledgeRecord.agent_key,
            AgentKnowledgeRecord.entity_key,
            func.count(AgentKnowledgeRecord.id).label("n"),
        )
        .group_by(AgentKnowledgeRecord.agent_key, AgentKnowledgeRecord.entity_key)
        .having(func.count(AgentKnowledgeRecord.id) > 1)
        .all()
    )
    return [
        {
            "agent_key": row.agent_key,
            "entity_key": row.entity_key,
            "count": int(row.n),
        }
        for row in duplicates
    ]


def _detect_cross_agent_conflicts(db: Session) -> List[Dict[str, object]]:
    rows = (
        db.query(
            AgentKnowledgeRecord.entity_key,
            func.count(func.distinct(AgentKnowledgeRecord.summary)).label("distinct_summaries"),
            func.count(func.distinct(AgentKnowledgeRecord.agent_key)).label("agents"),
        )
        .group_by(AgentKnowledgeRecord.entity_key)
        .having(func.count(func.distinct(AgentKnowledgeRecord.summary)) > 1)
        .having(func.count(func.distinct(AgentKnowledgeRecord.agent_key)) > 1)
        .all()
    )
    return [
        {
            "entity_key": row.entity_key,
            "distinct_summaries": int(row.distinct_summaries),
            "agents": int(row.agents),
        }
        for row in rows
    ]


def run_supervisor_cycle(db: Session) -> Dict[str, object]:
    now = _now()
    rows = db.query(AgentKnowledgeReportSnapshot).order_by(AgentKnowledgeReportSnapshot.agent_key.asc()).all()

    refreshed_targets: List[str] = []
    retry_targets: List[str] = []
    incidents_created = 0

    # Decision rules and monitoring updates
    for row in rows:
        age = _knowledge_age_seconds(row, now)
        row.knowledge_age_seconds = age

        # Inactive agent detection
        if age > max(3600, int(row.ttl_seconds or 3600) * 2):
            _create_incident(
                db,
                incident_type="INACTIVE_AGENT",
                severity="HIGH",
                summary=f"Agent {row.agent_key} appears inactive.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"knowledge_age_seconds": age, "ttl_seconds": int(row.ttl_seconds or 0)},
            )
            incidents_created += 1

        # Health degradation rule
        if row.health_status not in {"HEALTHY", "DEGRADED"}:
            row.health_status = "DEGRADED"
        if float(row.average_confidence or 0.0) < 0.65:
            row.health_status = "DEGRADED"
            row.freshness_status = "NEEDS_REVIEW"
            row.pending_reviews = int(row.pending_reviews or 0) + 1
            _create_incident(
                db,
                incident_type="LOW_CONFIDENCE",
                severity="MEDIUM",
                summary=f"Agent {row.agent_key} confidence dropped below threshold.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"average_confidence": float(row.average_confidence or 0.0)},
            )
            incidents_created += 1

        # TTL expiry rule
        if _is_expired(row, now):
            row.freshness_status = "EXPIRED"
            _create_incident(
                db,
                incident_type="TTL_EXPIRED",
                severity="HIGH",
                summary=f"Knowledge expired for {row.agent_key}.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"verified_until": row.verified_until.isoformat() if row.verified_until else None},
            )
            incidents_created += 1
            refreshed_targets.append(row.agent_key)

        # Repeated refresh failures rule
        if int(row.failed_refresh_count or 0) >= 3:
            row.freshness_status = "STALE"
            _create_incident(
                db,
                incident_type="REPEATED_REFRESH_FAILURE",
                severity="HIGH",
                summary=f"Repeated refresh failures detected for {row.agent_key}.",
                agent_key=row.agent_key,
                domain=row.domain,
                details={"failed_refresh_count": int(row.failed_refresh_count or 0)},
            )
            incidents_created += 1
            retry_targets.append(row.agent_key)

        # Scheduled and priority refresh
        if row.next_refresh_at and row.next_refresh_at <= now:
            refreshed_targets.append(row.agent_key)

    # Detect duplicate/conflicting/missing knowledge
    duplicates = _detect_duplicate_knowledge(db)
    if duplicates:
        _create_incident(
            db,
            incident_type="DUPLICATE_KNOWLEDGE",
            severity="MEDIUM",
            summary="Duplicate knowledge objects detected.",
            details={"count": len(duplicates), "sample": duplicates[:20]},
        )
        incidents_created += 1

    conflicts = _detect_cross_agent_conflicts(db)
    if conflicts:
        _create_incident(
            db,
            incident_type="CONFLICTING_KNOWLEDGE",
            severity="HIGH",
            summary="Conflicting knowledge ownership detected across agents.",
            details={"count": len(conflicts), "sample": conflicts[:20]},
        )
        incidents_created += 1

    missing = [r.agent_key for r in rows if int(r.knowledge_count or 0) <= 0]
    if missing:
        _create_incident(
            db,
            incident_type="MISSING_KNOWLEDGE",
            severity="HIGH",
            summary="One or more agents have missing prepared knowledge.",
            details={"agents": missing},
        )
        incidents_created += 1

    # Refresh queue handling: priority + retry + scheduled
    priority_keys = sorted(set(retry_targets + refreshed_targets))
    refreshed_count = 0
    refresh_failures = 0
    if priority_keys:
        refresh_result = refresh_all_agent_reports(db, refresh_mode="priority", agent_keys=priority_keys, force=False, incremental=False)
        refreshed_count += int(refresh_result.get("refreshed", 0))
        refresh_failures += int(refresh_result.get("failures", 0))

    # Escalate persistent failures after refresh attempt
    failed_rows = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.failed_refresh_count >= 5).all()
    for row in failed_rows:
        _create_incident(
            db,
            incident_type="ESCALATED_REFRESH_FAILURE",
            severity="CRITICAL",
            summary=f"Escalation: {row.agent_key} requires manual intervention.",
            agent_key=row.agent_key,
            domain=row.domain,
            details={"failed_refresh_count": int(row.failed_refresh_count or 0)},
        )
        incidents_created += 1

    db.commit()

    supervisor = compute_supervisor_metrics(db)
    return {
        "incidents_created": incidents_created,
        "priority_refresh_targets": priority_keys,
        "refreshed": refreshed_count,
        "refresh_failures": refresh_failures,
        "supervisor": supervisor,
    }


def recent_incidents(db: Session, limit: int = 200) -> List[Dict[str, object]]:
    rows = (
        db.query(SupervisorIncidentLog)
        .order_by(SupervisorIncidentLog.created_at.desc())
        .limit(max(1, min(limit, 1000)))
        .all()
    )
    out: List[Dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "id": row.id,
                "incident_type": row.incident_type,
                "severity": row.severity,
                "status": row.status,
                "agent_key": row.agent_key,
                "domain": row.domain,
                "summary": row.summary,
                "details": json.loads(row.details_json or "{}"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out


def stale_usage_summary(db: Session, hours: int = 24) -> Dict[str, object]:
    since = _now() - timedelta(hours=max(1, min(hours, 24 * 30)))
    rows = (
        db.query(RecommendationKnowledgeUsageLog)
        .filter(RecommendationKnowledgeUsageLog.logged_at >= since)
        .all()
    )
    total = len(rows)
    stale_used = [row for row in rows if int(row.used_stale or 0) == 1]
    stale_not_allowed = [row for row in rows if int(row.used_stale or 0) == 1 and int(row.policy_allowed or 0) == 0]

    return {
        "window_hours": hours,
        "total_usage_logs": total,
        "stale_usage_count": len(stale_used),
        "stale_not_allowed_count": len(stale_not_allowed),
        "sample": [
            {
                "recommendation_key": row.recommendation_key,
                "agent_key": row.agent_key,
                "freshness_status": row.freshness_status,
                "policy_allowed": bool(int(row.policy_allowed or 0)),
                "decision": row.decision,
                "reason": row.decision_reason,
            }
            for row in stale_not_allowed[:30]
        ],
    }
