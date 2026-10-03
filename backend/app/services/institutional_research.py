"""Persistent research delivery ledger: attempted != verified != fresh.

Only collectors write this record type. Public reports preserve the most recent
attempt, including failure, so an old success cannot mask a broken source.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord
from app.services.research_coverage_contract import RECORD_TYPE, TOPICS, VERSION, observation_status, parse_date, complaint_window, permitted_source

LOG = logging.getLogger(__name__)
KNOWN_FINDINGS_TYPE = f"{RECORD_TYPE}:known_complaint_findings"


def save_observation(db, canonical_id: str, topic: str, payload: dict) -> None:
    if topic not in TOPICS:
        raise ValueError("Unknown institutional research topic")
    db.add(AgentKnowledgeRecord(
        agent_key="regulatory_intelligence", record_type=f"{RECORD_TYPE}:{topic}", entity_key=canonical_id,
        source=str(payload.get("source") or TOPICS[topic]["source"]),
        confidence=1.0 if payload.get("status") == "VERIFIED" else 0.0,
        summary=f"{topic}: {payload.get('status', 'UNKNOWN')}",
        payload_json=json.dumps({**payload, "topic": topic, "contract_version": VERSION}, sort_keys=True),
    ))
    # A failed refresh must stay visible without erasing previously established
    # findings. Keep the known-event history separately from source attempt status.
    findings = (payload.get("data") or {}).get("findings") or []
    if topic == "official_complaints" and findings and payload.get("identity_verified") is True and permitted_source(payload.get("source_url", "")):
        previous = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.entity_key == canonical_id,
            AgentKnowledgeRecord.record_type == KNOWN_FINDINGS_TYPE).order_by(AgentKnowledgeRecord.id.desc()).first()
        try:
            known = json.loads(previous.payload_json).get("findings", []) if previous else []
        except (TypeError, ValueError):
            known = []
        merged = {}
        for finding in [*known, *findings]:
            item = {**finding, "source_url": finding.get("source_url") or payload.get("source_url")}
            if not parse_date(item.get("date")) or not permitted_source(item["source_url"]):
                continue
            merged[(item["date"], str(item.get("tag") or item.get("subject") or ""))] = item
        db.add(AgentKnowledgeRecord(agent_key="regulatory_intelligence", record_type=KNOWN_FINDINGS_TYPE,
            entity_key=canonical_id, source=str(payload.get("source") or "OFFICIAL_REGULATOR"), confidence=1.0,
            summary="Known published complaint-related findings", payload_json=json.dumps({"findings": list(merged.values())}, sort_keys=True)))


def load_observations(canonical_ids: list[str] | None = None) -> tuple[dict, str | None]:
    db = SessionLocal()
    try:
        query = db.query(func.max(AgentKnowledgeRecord.id)).filter(
            AgentKnowledgeRecord.record_type.in_([*[f"{RECORD_TYPE}:{topic}" for topic in TOPICS], KNOWN_FINDINGS_TYPE]))
        if canonical_ids is not None:
            if not canonical_ids:
                return {}, None
            query = query.filter(AgentKnowledgeRecord.entity_key.in_(canonical_ids))
        latest_ids = query.group_by(AgentKnowledgeRecord.entity_key, AgentKnowledgeRecord.record_type)
        records = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.id.in_(latest_ids)).all()
        out = {}
        for record in records:
            try:
                payload = json.loads(record.payload_json)
            except (ValueError, TypeError):
                LOG.warning("Malformed institutional research observation id=%s", record.id)
                continue
            topic = payload.get("topic")
            if record.record_type == KNOWN_FINDINGS_TYPE:
                out.setdefault(record.entity_key, {})["known_complaint_findings"] = payload.get("findings") or []
            if topic in TOPICS:
                out.setdefault(record.entity_key, {}).setdefault(topic, payload)
        return out, None
    except SQLAlchemyError:
        LOG.exception("Institutional research ledger unavailable")
        return {}, "RESEARCH_LEDGER_UNAVAILABLE"
    finally:
        db.close()


def facility_research_report(canonical_id: str, facility: dict, observations: dict | None = None,
                             *, ledger_error: str | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    synthetic = facility.get("synthetic_pilot") is True or canonical_id.startswith("PILOT-NV-")
    if observations is None:
        if synthetic:
            observations = {}
        else:
            all_records, ledger_error = load_observations([canonical_id])
            observations = all_records.get(canonical_id, {})
    start, end = complaint_window(now.date())
    known = [item for item in observations.get("known_complaint_findings", [])
             if parse_date(item.get("date")) is not None and start <= parse_date(item.get("date")) <= end
             and permitted_source(item.get("source_url", ""))]
    topics = []
    for key, policy in TOPICS.items():
        record = observations.get(key) or {}
        status = "SYNTHETIC_PILOT_NOT_PUBLIC_RESEARCH" if synthetic else observation_status(record, key, now)
        topics.append({"topic": key, "label": policy["label"], "source": record.get("source") or policy["source"],
                       "status": status, "observed_at": record.get("observed_at"),
                       "source_url": record.get("source_url"), "data": record.get("data") or {},
                       "limitation": record.get("limitation") or ("No current verified information is available." if status != "VERIFIED" else None),
                       "next_action": policy["next_action"], "known_findings": known if key == "official_complaints" and not synthetic else []})
    counts = Counter(item["status"] for item in topics)
    return {"canonical_facility_id": canonical_id, "contract_version": VERSION, "checked_at": now.isoformat(),
            "status": "SYNTHETIC_PILOT" if synthetic else ("DEGRADED" if ledger_error or any(t["status"] not in {"VERIFIED", "NOT_APPLICABLE"} for t in topics) else "CURRENT"),
            "ledger_error": ledger_error, "topics": topics, "status_counts": dict(counts),
            "policy": "Sources remain separate. Missing information is not negative evidence; a complaint is not a verified violation."}


def research_coverage_report(index: dict) -> dict:
    records, error = load_observations(list(index))
    reports = [facility_research_report(cid, row, records.get(cid, {}), ledger_error=error) for cid, row in index.items()]
    real = [r for r in reports if r["status"] != "SYNTHETIC_PILOT"]
    counts = Counter(t["status"] for r in real for t in r["topics"])
    return {"contract_version": VERSION, "status": "DEGRADED" if error or any(r["status"] == "DEGRADED" for r in real) else ("NO_REAL_FACILITIES" if not real else "CURRENT"),
            "real_facilities": len(real), "synthetic_excluded": len(reports) - len(real),
            "status_counts": dict(counts), "ledger_error": error, "facilities": reports}
