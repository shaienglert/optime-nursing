from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord, AgentQueueItem, AgentWorker
from app.services.facility_parameter_service import get_facility_parameter_table

QUEUE_TYPE = "DECISION_EVIDENCE_RESEARCH"


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _material_dimensions(human_context: Dict[str, Any]) -> Dict[str, tuple[str, ...]]:
    signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}
    social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
    independence = signals.get("independence_priority") if isinstance(signals.get("independence_priority"), dict) else {}
    out: Dict[str, tuple[str, ...]] = {"care_support": ("medication_support", "adl_support")}
    if _upper(social.get("value")) == "HIGH":
        out["social_engagement"] = ("activities", "transportation")
    if _upper(independence.get("value")) == "HIGH":
        out["autonomy_choice"] = ("transportation", "private_shared_rooms")
    return out


def _unknown_parameters(canonical_id: str, parameter_ids: tuple[str, ...]) -> List[str]:
    try:
        table = get_facility_parameter_table(canonical_id, priority_parameter_ids=list(parameter_ids), include_evidence_records=False)
    except KeyError:
        return list(parameter_ids)
    requested = set(parameter_ids)
    found = set()
    unknown: List[str] = []
    for row in table.get("rows") or []:
        pid = str(row.get("parameter_id") or "")
        if pid not in requested:
            continue
        found.add(pid)
        if row.get("raw_value") in (None, "", "UNKNOWN") or str(row.get("source") or "") in {"", "Not verified"}:
            unknown.append(pid)
    unknown.extend(sorted(requested - found))
    return sorted(set(unknown))


def _market_evidence(db, canonical_id: str) -> List[Dict[str, Any]]:
    rows = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.entity_key == canonical_id).order_by(AgentKnowledgeRecord.id.desc()).all()
    out: List[Dict[str, Any]] = []
    for row in rows:
        try:
            payload = json.loads(row.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        if str(payload.get("market") or "").lower() not in {"las-vegas", "las vegas", "nevada"}:
            continue
        out.append({"agent_key": row.agent_key, "summary": row.summary, "confidence": float(row.confidence or 0.0), "source": row.source, "payload": payload})
    return out


def _ensure_worker(db, agent_key: str) -> None:
    row = db.query(AgentWorker).filter(AgentWorker.agent_key == agent_key).first()
    if row is not None:
        row.queue_type = QUEUE_TYPE
        return
    names = {"activities_intelligence": "Activities Intelligence Agent", "provider_intelligence": "Provider Intelligence Agent"}
    db.add(AgentWorker(agent_key=agent_key, name=names[agent_key], mission="Fill material Las Vegas facility evidence gaps for governed recommendations.", data_sources='["official provider websites","Nevada HCQC / ALiS"]', queue_type=QUEUE_TYPE, status="IDLE", coverage=0.0))


def _queue(db, row: Dict[str, Any], dimension: str, unknown: List[str]) -> bool:
    agent_key = "activities_intelligence" if dimension == "social_engagement" else "provider_intelligence"
    _ensure_worker(db, agent_key)
    canonical_id = str(row.get("canonical_facility_id") or "")
    pending = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.agent_key == agent_key, AgentQueueItem.status.in_(["PENDING", "RUNNING"])).all()
    for item in pending:
        try:
            payload = json.loads(item.payload_json or "{}")
        except json.JSONDecodeError:
            continue
        if payload.get("canonical_facility_id") == canonical_id and payload.get("dimension") == dimension:
            return False
    payload = {"market": "las-vegas", "canonical_facility_id": canonical_id, "facility_name": row.get("facility_name"), "city": row.get("city") or "LAS VEGAS", "state": "NV", "dimension": dimension, "requested_parameters": unknown, "requested_at": datetime.now(timezone.utc).isoformat()}
    db.add(AgentQueueItem(queue_type=QUEUE_TYPE, agent_key=agent_key, payload_json=json.dumps(payload, sort_keys=True), status="PENDING", max_attempts=3))
    return True


def attach_agent_evidence_and_queue_gaps(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> Dict[str, Any]:
    db = SessionLocal()
    gaps: List[Dict[str, Any]] = []
    queued = 0
    try:
        dimensions = _material_dimensions(human_context)
        for row in rows:
            cid = str(row.get("canonical_facility_id") or "")
            if not cid:
                continue
            row["agent_person_fit_evidence"] = _market_evidence(db, cid)
            for dimension, parameters in dimensions.items():
                unknown = _unknown_parameters(cid, parameters)
                if not unknown:
                    continue
                gaps.append({"canonical_facility_id": cid, "facility_name": row.get("facility_name"), "dimension": dimension, "unknown_parameters": unknown})
                if _queue(db, row, dimension, unknown):
                    queued += 1
        db.commit()
        return {"status": "RESEARCH_REQUIRED" if gaps else "MATERIAL_EVIDENCE_AVAILABLE", "market": "las-vegas", "market_scoped": True, "material_gaps": gaps, "tasks_queued": queued, "decision_finality": "PROVISIONAL_PENDING_AGENT_EVIDENCE" if gaps else "EVIDENCE_COMPLETE_FOR_MATERIAL_DIMENSIONS", "policy": "resident unknown -> ask; facility unknown -> agent research; unknown is not mismatch"}
    except Exception as exc:
        db.rollback()
        return {"status": "AGENT_BRIDGE_UNAVAILABLE", "market": "las-vegas", "market_scoped": True, "reason": exc.__class__.__name__, "tasks_queued": 0, "material_gaps": [], "decision_finality": "PROVISIONAL_AGENT_BRIDGE_UNAVAILABLE"}
    finally:
        db.close()


def social_evidence_sort_key(row: Dict[str, Any]) -> tuple[int, float]:
    evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    scores = []
    for item in evidence:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if payload.get("social_engagement_verified") is True:
            scores.append(float(item.get("confidence") or 0.0))
    return (0, -max(scores)) if scores else (1, 0.0)
