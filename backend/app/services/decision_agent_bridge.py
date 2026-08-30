from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import inspect

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord, AgentQueueItem, AgentWorker
from app.services import governed_evidence_runtime
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
_AGENT_TABLES = {"agent_knowledge_records", "agent_queue_items", "agent_workers"}


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _agent_schema_available(db) -> bool:
    bind = db.get_bind()
    tables = set(inspect(bind).get_table_names())
    return _AGENT_TABLES.issubset(tables)


def _material_dimensions(human_context: Dict[str, Any]) -> Dict[str, tuple[str, ...]]:
    signals = human_context.get("signals") if isinstance(human_context.get("signals"), dict) else {}
    social = signals.get("social_transition_priority") if isinstance(signals.get("social_transition_priority"), dict) else {}
    independence = signals.get("independence_priority") if isinstance(signals.get("independence_priority"), dict) else {}
    strategy = human_context.get("living_strategy") if isinstance(human_context.get("living_strategy"), dict) else {}
    strategy_signals = strategy.get("signals") if isinstance(strategy.get("signals"), dict) else {}
    household = strategy.get("household") if isinstance(strategy.get("household"), dict) else {}
    out: Dict[str, tuple[str, ...]] = {"care_support": ("medication_support", "adl_support"), "facility_quality_safety": _QUALITY_SAFETY_PARAMETERS}
    if _upper(social.get("value")) == "HIGH" or bool(strategy_signals.get("high_social_culture_priority")):
        out["social_engagement"] = ("activities", "transportation")
    if _upper(independence.get("value")) == "HIGH": out["autonomy_choice"] = ("transportation", "private_shared_rooms")
    if bool(strategy_signals.get("rehabilitation_need_detected")): out["rehab_path"] = ("pt", "ot", "rehabilitation")
    if str(household.get("type") or "") == "COUPLE": out["couple_coresidence"] = ("couple_occupancy", "second_person_policy")
    if bool(strategy_signals.get("expected_recovery")): out["recovery_transition"] = ("outside_care_allowed", "continuum_of_care")
    return out


def _unknown_parameters(canonical_id: str, parameter_ids: tuple[str, ...]) -> List[str]:
    try: table = get_facility_parameter_table(canonical_id, priority_parameter_ids=list(parameter_ids), include_evidence_records=False)
    except KeyError: return list(parameter_ids)
    requested, found, unknown = set(parameter_ids), set(), []
    for row in table.get("rows") or []:
        pid = str(row.get("parameter_id") or "")
        if pid not in requested: continue
        found.add(pid)
        if row.get("raw_value") in (None, "", "UNKNOWN") or str(row.get("source") or "") in {"", "Not verified"}: unknown.append(pid)
    unknown.extend(sorted(requested - found))
    return sorted(set(unknown))


def _market_evidence(db, canonical_id: str) -> List[Dict[str, Any]]:
    return governed_evidence_runtime.bulk_market_scoped_agent_evidence(db, [canonical_id]).get(canonical_id, [])


def _governed_evidence(evidence: List[Dict[str, Any]], dimension: str) -> List[Dict[str, Any]]:
    relevant = [item for item in evidence if str((item.get("payload") or {}).get("dimension") or dimension) == dimension]
    if not relevant: return []
    # Records arrive newest-first. A completed newer research result that verified no public claim
    # supersedes stale positive assertions for this dimension. Positive assertions are usable only
    # from governed source classes and with verified identity.
    newest = relevant[0]
    newest_payload = newest.get("payload") if isinstance(newest.get("payload"), dict) else {}
    if newest_payload.get("research_completed") is True and newest_payload.get("official_identity_verified") is False:
        return []
    governed: List[Dict[str, Any]] = []
    for item in relevant:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if not governed_evidence_runtime.is_governed_positive_source(item.get("source"), payload): continue
        governed.append(item)
    return governed


def _resolve_with_agent_evidence(unknown: List[str], dimension: str, evidence: List[Dict[str, Any]]) -> List[str]:
    unresolved = set(unknown)
    for item in _governed_evidence(evidence, dimension):
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        if dimension == "social_engagement":
            if payload.get("social_engagement_verified") is True: unresolved.discard("activities")
            if payload.get("transportation_verified") is True: unresolved.discard("transportation")
        elif dimension == "care_support":
            if payload.get("medication_support_verified") is True: unresolved.discard("medication_support")
            if payload.get("adl_support_verified") is True: unresolved.discard("adl_support")
        elif dimension == "autonomy_choice":
            if payload.get("transportation_verified") is True: unresolved.discard("transportation")
        elif dimension == "facility_quality_safety":
            for parameter_id in payload.get("regulatory_parameters_verified") if isinstance(payload.get("regulatory_parameters_verified"), list) else []: unresolved.discard(str(parameter_id))
        elif dimension == "rehab_path" and (payload.get("rehab_verified") is True or payload.get("pt_ot_verified") is True): unresolved.difference_update({"pt", "ot", "rehabilitation"})
        elif dimension == "couple_coresidence" and payload.get("couple_coresidence_verified") is True: unresolved.difference_update({"couple_occupancy", "second_person_policy"})
        elif dimension == "recovery_transition":
            if payload.get("outside_care_allowed_verified") is True: unresolved.discard("outside_care_allowed")
            if payload.get("continuum_of_care_verified") is True: unresolved.discard("continuum_of_care")
    return sorted(unresolved)


def _worker_values(agent_key: str) -> Dict[str, Any]:
    names = {"activities_intelligence": "Activities Intelligence Agent", "provider_intelligence": "Provider Intelligence Agent", "regulatory_intelligence": "Nevada Regulatory Intelligence Agent"}
    return {"agent_key": agent_key, "name": names[agent_key], "mission": "Fill material Las Vegas facility evidence gaps for governed recommendations.", "data_sources": '["official provider websites","Nevada HCQC / ALiS"]', "queue_type": QUEUE_TYPE, "status": "IDLE", "coverage": 0.0}


def _ensure_worker(db, agent_key: str) -> None:
    values = _worker_values(agent_key); bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        db.execute(pg_insert(AgentWorker).values(**values).on_conflict_do_update(index_elements=["agent_key"], set_={"queue_type": QUEUE_TYPE})); return
    for pending in tuple(db.new):
        if isinstance(pending, AgentWorker) and pending.agent_key == agent_key: pending.queue_type = QUEUE_TYPE; return
    row = db.query(AgentWorker).filter(AgentWorker.agent_key == agent_key).first()
    if row is not None: row.queue_type = QUEUE_TYPE; return
    db.add(AgentWorker(**values))


def _recent_completed_item(db, canonical_id: str, dimension: str, hours: int = 24) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "DONE", AgentQueueItem.finished_at >= cutoff).all()
    for item in items:
        try: payload = json.loads(item.payload_json or "{}")
        except json.JSONDecodeError: continue
        if payload.get("canonical_facility_id") == canonical_id and payload.get("dimension") == dimension: return True
    return False


def _queue(db, row: Dict[str, Any], dimension: str, unknown: List[str]) -> bool:
    agent_key = "activities_intelligence" if dimension == "social_engagement" else "regulatory_intelligence" if dimension == "facility_quality_safety" else "provider_intelligence"
    _ensure_worker(db, agent_key); canonical_id = str(row.get("canonical_facility_id") or "")
    pending = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.agent_key == agent_key, AgentQueueItem.status.in_(["PENDING", "RUNNING"])).all()
    for item in pending:
        try: payload = json.loads(item.payload_json or "{}")
        except json.JSONDecodeError: continue
        if payload.get("canonical_facility_id") == canonical_id and payload.get("dimension") == dimension: return False
    if _recent_completed_item(db, canonical_id, dimension): return False
    payload = {"market": "las-vegas", "canonical_facility_id": canonical_id, "facility_name": row.get("facility_name"), "city": row.get("city") or "LAS VEGAS", "state": "NV", "dimension": dimension, "requested_parameters": unknown, "requested_at": datetime.now(timezone.utc).isoformat()}
    db.add(AgentQueueItem(queue_type=QUEUE_TYPE, agent_key=agent_key, payload_json=json.dumps(payload, sort_keys=True), status="PENDING", max_attempts=3)); return True


def _kick_worker_async() -> None:
    def run() -> None:
        try:
            from app.services.decision_research_worker import process_pending_decision_research
            while True:
                result = process_pending_decision_research(limit=60); _LOG.info("decision evidence worker result=%s", result)
                if result.get("status") == "ALREADY_RUNNING" or not int(result.get("remaining") or 0): break
        except Exception: _LOG.exception("decision evidence worker crashed")
    threading.Thread(target=run, name="optime-decision-evidence-worker", daemon=True).start()


def attach_agent_evidence_and_queue_gaps(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> Dict[str, Any]:
    db = SessionLocal(); gaps: List[Dict[str, Any]] = []; queued = researched_unknown = 0
    try:
        bind = db.get_bind()
        if not _agent_schema_available(db):
            if bind.dialect.name == "sqlite": return {"status": "LOCAL_AGENT_SCHEMA_NOT_INITIALIZED", "market": "las-vegas", "market_scoped": True, "material_gaps": [], "tasks_queued": 0, "pending_backlog": 0, "researched_unknown_count": 0, "decision_finality": "PROVISIONAL_LOCAL_AGENT_SCHEMA_NOT_INITIALIZED", "policy": "Local/test SQLite may omit agent persistence tables; production PostgreSQL must contain them."}
            raise RuntimeError("Production agent persistence schema is incomplete")
        dimensions = _material_dimensions(human_context)
        for row in rows:
            cid = str(row.get("canonical_facility_id") or "")
            if not cid: continue
            evidence = _market_evidence(db, cid); row["agent_person_fit_evidence"] = evidence
            for dimension, parameters in dimensions.items():
                unknown = _resolve_with_agent_evidence(_unknown_parameters(cid, parameters), dimension, evidence)
                if not unknown: continue
                was_researched = _recent_completed_item(db, cid, dimension)
                gaps.append({"canonical_facility_id": cid, "facility_name": row.get("facility_name"), "dimension": dimension, "unknown_parameters": unknown, "research_completed_no_public_evidence": was_researched})
                if was_researched: researched_unknown += 1
                elif _queue(db, row, dimension, unknown): queued += 1
        db.commit(); pending_backlog = db.query(AgentQueueItem).filter(AgentQueueItem.queue_type == QUEUE_TYPE, AgentQueueItem.status == "PENDING").count()
        if queued > 0 or pending_backlog > 0: _kick_worker_async()
        if gaps and queued == 0 and researched_unknown == len(gaps): finality, status = "PROVISIONAL_DIRECT_VERIFICATION_REQUIRED", "PUBLIC_RESEARCH_EXHAUSTED_MATERIAL_UNKNOWN_REMAINS"
        elif gaps: finality, status = "PROVISIONAL_PENDING_AGENT_EVIDENCE", "RESEARCH_REQUIRED"
        else: finality, status = "EVIDENCE_COMPLETE_FOR_MATERIAL_DIMENSIONS", "MATERIAL_EVIDENCE_AVAILABLE"
        return {"status": status, "market": "las-vegas", "market_scoped": True, "material_gaps": gaps, "tasks_queued": queued, "pending_backlog": pending_backlog, "researched_unknown_count": researched_unknown, "decision_finality": finality, "policy": "client intent first; resident unknown -> ask; facility MUST unknown -> agent research; unknown is not mismatch"}
    except Exception as exc:
        db.rollback(); _LOG.exception("agent evidence bridge unavailable")
        return {"status": "AGENT_BRIDGE_UNAVAILABLE", "market": "las-vegas", "market_scoped": True, "reason": exc.__class__.__name__, "tasks_queued": 0, "material_gaps": [], "decision_finality": "PROVISIONAL_AGENT_BRIDGE_UNAVAILABLE"}
    finally: db.close()


def social_evidence_sort_key(row: Dict[str, Any]) -> tuple[int, float]:
    evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    scores = [float(item.get("confidence") or 0.0) for item in _governed_evidence(evidence, "social_engagement") if (item.get("payload") or {}).get("social_engagement_verified") is True]
    return (0, -max(scores)) if scores else (1, 0.0)
