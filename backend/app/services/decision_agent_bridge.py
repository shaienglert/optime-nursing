from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord, AgentQueueItem, AgentWorker
from app.services.facility_parameter_service import get_facility_parameter_table

QUEUE_TYPE = "DECISION_EVIDENCE_RESEARCH"
_LOG = logging.getLogger(__name__)
_QUALITY_SAFETY_PARAMETERS = (
    "inspection_rating",
    "deficiency_count",
    "deficiency_severity",
    "complaint_related_findings",
    "penalties_fines",
    "sanctions_final_orders",
)


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _material_dimensions(human_context: Dict[str, Any]) -> Dict[str, tuple[str, ...]]:
    signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}
    social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
    independence = signals.get("independence_priority") if isinstance(signals.get("independence_priority"), dict) else {}
    out: Dict[str, tuple[str, ...]] = {
        "care_support": ("medication_support", "adl_support"),
        "facility_quality_safety": _QUALITY_SAFETY_PARAMETERS,
    }
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
        out.append({"agent_key": row.agent_key, "summary": row.summary, "confidence": float(row.confidence or 0.0), "source": row.source, "payload": payload, "created_at": row.created_at.isoformat() if row.created_at else None})
    return out


def _resolve_with_agent_evidence(unknown: List[str], dimension: str, evidence: List[Dict[str, Any]]) -> List[str]:
    unresolved = set(unknown)
    for item in evidence:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if dimension == "social_engagement":
            if payload.get("social_engagement_verified") is True:
                unresolved.discard("activities")
            if payload.get("transportation_verified") is True:
                unresolved.discard("transportation")
        elif dimension == "care_support":
            if payload.get("medication_support_verified") is True:
                unresolved.discard("medication_support")
        elif dimension == "autonomy_choice":
            if payload.get("transportation_verified") is True:
                unresolved.discard("transportation")
        elif dimension == "facility_quality_safety":
            verified_parameters = payload.get("regulatory_parameters_verified") if isinstance(payload.get("regulatory_parameters_verified"), list) else []
            for parameter_id in verified_parameters:
                unresolved.discard(str(parameter_id))
    return sorted(unresolved)


def _ensure_worker(db, agent_key: str) -> None:
    row = db.query(AgentWorker).filter(AgentWorker.agent_key == agent_key).first()
    if row is not None:
        row.queue_type = QUEUE_TYPE
        return
    names = {
        "activities_intelligence": "Activities Intelligence Agent",
        "provider_intelligence": "Provider Intelligence Agent",
        "regulatory_intelligence": "Nevada Regulatory Intelligence Agent",
    }
    db.add(AgentWorker(agent_key=agent_key, name=names[agent_key], mission="Fill material Las Vegas facility evidence gaps for governed recommendations.", data_sources='["official provider websites","Nevada HCQC / ALiS"]', queue_type=QUEUE_TYPE, status="IDLE", coverage=0.0))


def _recent_completed_item(db, canonical_id: str, dimension: str, hours: int = 24) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "DONE", AgentQueueItem.finished_at >= cutoff).all()
    for item in items:
        try:
            payload = json.loads(item.payload_json or "{}")
        except json.JSONDecodeError:
            continue
        if payload.get("canonical_facility_id") == canonical_id and payload.get("dimension") == dimension:
            return True
    return False


def _queue(db, row: Dict[str, Any], dimension: str, unknown: List[str]) -> bool:
    if dimension == "social_engagement":
        agent_key = "activities_intelligence"
    elif dimension == "facility_quality_safety":
        agent_key = "regulatory_intelligence"
    else:
        agent_key = "provider_intelligence"
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
    if _recent_completed_item(db, canonical_id, dimension):
        return False
    payload = {"market": "las-vegas", "canonical_facility_id": canonical_id, "facility_name": row.get("facility_name"), "city": row.get("city") or "LAS VEGAS", "state": "NV", "dimension": dimension, "requested_parameters": unknown, "requested_at": datetime.now(timezone.utc).isoformat()}
    db.add(AgentQueueItem(queue_type=QUEUE_TYPE, agent_key=agent_key, payload_json=json.dumps(payload, sort_keys=True), status="PENDING", max_attempts=3))
    return True


def _kick_worker_async() -> None:
    def run() -> None:
        try:
            from app.services.decision_research_worker import process_pending_decision_research
            result = process_pending_decision_research(limit=60)
            _LOG.info("decision evidence worker result=%s", result)
        except Exception:
            _LOG.exception("decision evidence worker crashed")

    threading.Thread(target=run, name="optime-decision-evidence-worker", daemon=True).start()


def attach_agent_evidence_and_queue_gaps(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> Dict[str, Any]:
    db = SessionLocal()
    gaps: List[Dict[str, Any]] = []
    queued = 0
    researched_unknown = 0
    try:
        dimensions = _material_dimensions(human_context)
        for row in rows:
            cid = str(row.get("canonical_facility_id") or "")
            if not cid:
                continue
            evidence = _market_evidence(db, cid)
            row["agent_person_fit_evidence"] = evidence
            for dimension, parameters in dimensions.items():
                unknown = _resolve_with_agent_evidence(_unknown_parameters(cid, parameters), dimension, evidence)
                if not unknown:
                    continue
                was_researched = _recent_completed_item(db, cid, dimension)
                gaps.append({"canonical_facility_id": cid, "facility_name": row.get("facility_name"), "dimension": dimension, "unknown_parameters": unknown, "research_completed_no_public_evidence": was_researched})
                if was_researched:
                    researched_unknown += 1
                elif _queue(db, row, dimension, unknown):
                    queued += 1
        db.commit()
        if queued > 0:
            _kick_worker_async()
        if gaps and queued == 0 and researched_unknown == len(gaps):
            finality = "PROVISIONAL_DIRECT_VERIFICATION_REQUIRED"
            status = "PUBLIC_RESEARCH_EXHAUSTED_MATERIAL_UNKNOWN_REMAINS"
        elif gaps:
            finality = "PROVISIONAL_PENDING_AGENT_EVIDENCE"
            status = "RESEARCH_REQUIRED"
        else:
            finality = "EVIDENCE_COMPLETE_FOR_MATERIAL_DIMENSIONS"
            status = "MATERIAL_EVIDENCE_AVAILABLE"
        return {"status": status, "market": "las-vegas", "market_scoped": True, "material_gaps": gaps, "tasks_queued": queued, "researched_unknown_count": researched_unknown, "decision_finality": finality, "policy": "resident unknown -> ask; facility unknown -> agent research; unknown is not mismatch"}
    except Exception as exc:
        db.rollback()
        _LOG.exception("agent evidence bridge unavailable")
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
