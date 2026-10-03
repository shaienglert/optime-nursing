"""Daily audit of observed activity; ingestion and guard admission are not adoption.

Uses the existing durable knowledge ledger. Archives are independent of host files.
No resident identifiers, family text, or recommendation identifiers are exported.
"""
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json

from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, RecommendationKnowledgeUsageLog
from app.services.agent_knowledge_reports import AGENT_REPORT_DEFS

ARCHIVE_TYPE = "research_daily_audit_v1"
ARCHIVE_AGENT = "research_daily_reporting"
OWNER_DECISION_TYPE = "research_owner_decision_v1"


def _json(value):
    try:
        result = json.loads(value or "{}")
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def build_daily_report(db, report_date: date, now=None):
    now = now or datetime.now(timezone.utc)
    start = datetime.combine(report_date, time.min, timezone.utc)
    end = min(start + timedelta(days=1), now)
    if start >= end:
        raise ValueError("Report window must contain elapsed time")
    runs = db.query(AgentJobRun).filter(AgentJobRun.started_at >= start, AgentJobRun.started_at < end).all()
    records = db.query(AgentKnowledgeRecord).filter(
        AgentKnowledgeRecord.created_at >= start, AgentKnowledgeRecord.created_at < end,
        AgentKnowledgeRecord.record_type != ARCHIVE_TYPE,
        AgentKnowledgeRecord.record_type != OWNER_DECISION_TYPE,
    ).all()
    usages = db.query(RecommendationKnowledgeUsageLog).filter(
        RecommendationKnowledgeUsageLog.logged_at >= start, RecommendationKnowledgeUsageLog.logged_at < end,
    ).all()
    keys = {str(d["agent_key"]) for d in AGENT_REPORT_DEFS}
    keys.update(r.agent_key for r in [*runs, *records, *usages])
    keys.discard(ARCHIVE_AGENT)
    # Pending questions carry across days; never manufacture policy questions
    # from an outage, nor keep resolved questions open as a static template.
    decision_rows = db.query(AgentKnowledgeRecord).filter(
        AgentKnowledgeRecord.record_type == OWNER_DECISION_TYPE,
        AgentKnowledgeRecord.created_at < end,
    ).order_by(AgentKnowledgeRecord.id.desc()).all()
    decisions = {}
    for row in decision_rows:
        decisions.setdefault(row.entity_key, _json(row.payload_json))
    questions = [{"key": key, **payload} for key, payload in decisions.items()
                 if payload.get("status") == "OPEN" and payload.get("question")]
    agents = []
    for key in sorted(keys):
        jobs = [r for r in runs if r.agent_key == key]
        facts = [r for r in records if r.agent_key == key]
        guards = [r for r in usages if r.agent_key == key]
        findings = []
        for record in facts:
            payload = _json(record.payload_json)
            # A prepared registry entry or seeded knowledge is not a new verified fact.
            findings.append({"record_id": record.id, "record_type": record.record_type,
                "status": payload.get("status", "UNCLASSIFIED"),
                "source_url": payload.get("source_url"),
                "observed_at": payload.get("observed_at"),
                "identity_verified": payload.get("identity_verified") is True})
        reasons = Counter(r.decision_reason for r in guards if r.decision != "USED" or not r.policy_allowed)
        agents.append({"agent_key": key, "status": "OBSERVED" if jobs or facts or guards else "MISSING",
            "runs": [{"id": r.id, "status": r.status, "items_processed": r.items_processed,
                "items_added": r.items_added, "errors": r.errors} for r in jobs],
            "records_ingested": len(facts), "findings": findings,
            "guard_admissions": sum(r.decision == "USED" and bool(r.policy_allowed) for r in guards),
            "guard_rejections": [{"reason": reason, "count": count} for reason, count in sorted(reasons.items())],
            "engine_adopted_facts": None,
            "adoption_status": "UNOBSERVABLE_NO_FACT_LEVEL_CONSUMPTION_TRACE"})
    return {"version": ARCHIVE_TYPE, "report_date": report_date.isoformat(),
        "window_start_utc": start.isoformat(), "window_end_utc": end.isoformat(),
        "generated_at": now.isoformat(), "status": "PARTIAL" if any(a["status"] == "MISSING" for a in agents) else "OBSERVED",
        "agents": agents,
        "limitations": ["Guard admission is permission to use a snapshot, not evidence of adoption in a decision.",
            "No activity record means MISSING, not successful inactivity.",
            "This audit does not assert absence of complaints or alter ranking."],
        "owner_questions": questions,
        "owner_decision_queue_status": "OBSERVED" if decisions else "UNCONNECTED_NO_DECISION_RECORDS"}


def archive_daily_report(db, report_date, now=None):
    report = build_daily_report(db, report_date, now)
    # Each completed capture is append-only; repeated captures preserve history.
    db.add(AgentKnowledgeRecord(agent_key=ARCHIVE_AGENT, record_type=ARCHIVE_TYPE,
        entity_key=report_date.isoformat(), summary=f"Daily observed activity {report_date}",
        payload_json=json.dumps(report, ensure_ascii=False), source="RUNTIME_AUDIT", confidence=0.0))
    db.commit()
    return report


def daily_report_history(db, limit=30):
    rows = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.record_type == ARCHIVE_TYPE).order_by(
        AgentKnowledgeRecord.id.desc()).limit(limit).all()
    return [_json(row.payload_json) for row in rows]
