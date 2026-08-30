from __future__ import annotations

"""Latency-bounded decision evidence bridge.

The legacy bridge performs repeated per-facility/per-dimension database lookups. This
implementation preserves the same governance semantics while batching database reads,
loading each facility parameter table once, and queuing research without N+1 queries.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import inspect

from app.database import SessionLocal
from app.models.agent_execution import AgentQueueItem, AgentWorker
from app.services import governed_evidence_runtime
from app.services.facility_parameter_service import get_facility_parameter_table
from app.services.decision_agent_bridge import (
    QUEUE_TYPE,
    _AGENT_TABLES,
    _material_dimensions,
    _resolve_with_agent_evidence,
    _ensure_worker,
    _kick_worker_async,
)

_LOG = logging.getLogger(__name__)


def _agent_schema_available(db) -> bool:
    return _AGENT_TABLES.issubset(set(inspect(db.get_bind()).get_table_names()))


def _load_unknown_parameters_once(canonical_id: str, parameter_ids: Set[str]) -> Set[str]:
    if not parameter_ids:
        return set()
    try:
        table = get_facility_parameter_table(
            canonical_id,
            priority_parameter_ids=sorted(parameter_ids),
            include_evidence_records=False,
        )
    except KeyError:
        return set(parameter_ids)
    found: Set[str] = set()
    unknown: Set[str] = set()
    for row in table.get("rows") or []:
        pid = str(row.get("parameter_id") or "")
        if pid not in parameter_ids:
            continue
        found.add(pid)
        if row.get("raw_value") in (None, "", "UNKNOWN") or str(row.get("source") or "") in {"", "Not verified"}:
            unknown.add(pid)
    unknown.update(parameter_ids - found)
    return unknown


def _prefetch_evidence(db, canonical_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    # This is the live production evidence-fetch path (see app/services/__init__.py's
    # _IntegratedRuntimeLoader, which monkey-patches attach_agent_evidence_and_queue_gaps
    # to this module's _fast variant). Was its own duplicate of the same
    # fetch-and-market-filter query as decision_agent_bridge.py's _market_evidence /
    # patient_decision_engine.py's medication overlay; now shares
    # governed_evidence_runtime.bulk_market_scoped_agent_evidence with both.
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for canonical_id, records in governed_evidence_runtime.bulk_market_scoped_agent_evidence(db, canonical_ids).items():
        out[canonical_id] = records
    return out


def _prefetch_queue_state(db, canonical_ids: Set[str]) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]], int]:
    pending_keys: Set[Tuple[str, str]] = set()
    recent_done_keys: Set[Tuple[str, str]] = set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    pending_items = (
        db.query(AgentQueueItem)
        .filter(
            AgentQueueItem.queue_type == QUEUE_TYPE,
            AgentQueueItem.status.in_(["PENDING", "RUNNING"]),
        )
        .all()
    )
    recent_items = (
        db.query(AgentQueueItem)
        .filter(
            AgentQueueItem.queue_type == QUEUE_TYPE,
            AgentQueueItem.status == "DONE",
            AgentQueueItem.finished_at >= cutoff,
        )
        .all()
    )

    for item in pending_items:
        try:
            payload = json.loads(item.payload_json or "{}")
        except json.JSONDecodeError:
            continue
        cid = str(payload.get("canonical_facility_id") or "")
        dim = str(payload.get("dimension") or "")
        if cid in canonical_ids and dim:
            pending_keys.add((cid, dim))

    for item in recent_items:
        try:
            payload = json.loads(item.payload_json or "{}")
        except json.JSONDecodeError:
            continue
        cid = str(payload.get("canonical_facility_id") or "")
        dim = str(payload.get("dimension") or "")
        if cid in canonical_ids and dim:
            recent_done_keys.add((cid, dim))

    return pending_keys, recent_done_keys, len(pending_items)


def _agent_key_for_dimension(dimension: str) -> str:
    if dimension == "social_engagement":
        return "activities_intelligence"
    if dimension == "facility_quality_safety":
        return "regulatory_intelligence"
    return "provider_intelligence"


def attach_agent_evidence_and_queue_gaps_fast(rows: List[Dict[str, Any]], human_context: Dict[str, Any]) -> Dict[str, Any]:
    db = SessionLocal()
    gaps: List[Dict[str, Any]] = []
    queued = 0
    researched_unknown = 0
    try:
        bind = db.get_bind()
        if not _agent_schema_available(db):
            if bind.dialect.name == "sqlite":
                return {
                    "status": "LOCAL_AGENT_SCHEMA_NOT_INITIALIZED",
                    "market": "las-vegas",
                    "market_scoped": True,
                    "material_gaps": [],
                    "tasks_queued": 0,
                    "pending_backlog": 0,
                    "researched_unknown_count": 0,
                    "decision_finality": "PROVISIONAL_LOCAL_AGENT_SCHEMA_NOT_INITIALIZED",
                    "policy": "Local/test SQLite may omit agent persistence tables; production PostgreSQL must contain them.",
                    "execution_mode": "BATCHED_DB_BRIDGE",
                }
            raise RuntimeError("Production agent persistence schema is incomplete")

        dimensions = _material_dimensions(human_context)
        all_parameters: Set[str] = set()
        for params in dimensions.values():
            all_parameters.update(params)

        canonical_ids = [str(row.get("canonical_facility_id") or "") for row in rows]
        canonical_ids = [cid for cid in canonical_ids if cid]
        canonical_id_set = set(canonical_ids)
        evidence_by_cid = _prefetch_evidence(db, canonical_ids)
        pending_keys, recent_done_keys, existing_pending_count = _prefetch_queue_state(db, canonical_id_set)

        for agent_key in ("activities_intelligence", "provider_intelligence", "regulatory_intelligence"):
            _ensure_worker(db, agent_key)

        newly_queued_keys: Set[Tuple[str, str]] = set()
        for row in rows:
            cid = str(row.get("canonical_facility_id") or "")
            if not cid:
                continue
            evidence = evidence_by_cid.get(cid, [])
            row["agent_person_fit_evidence"] = evidence
            unknown_for_facility = _load_unknown_parameters_once(cid, all_parameters)

            for dimension, parameters in dimensions.items():
                unknown = sorted(unknown_for_facility.intersection(parameters))
                unknown = _resolve_with_agent_evidence(unknown, dimension, evidence)
                if not unknown:
                    continue
                key = (cid, dimension)
                was_researched = key in recent_done_keys
                gaps.append(
                    {
                        "canonical_facility_id": cid,
                        "facility_name": row.get("facility_name"),
                        "dimension": dimension,
                        "unknown_parameters": unknown,
                        "research_completed_no_public_evidence": was_researched,
                    }
                )
                if was_researched:
                    researched_unknown += 1
                    continue
                if key in pending_keys or key in newly_queued_keys:
                    continue

                agent_key = _agent_key_for_dimension(dimension)
                payload = {
                    "market": "las-vegas",
                    "canonical_facility_id": cid,
                    "facility_name": row.get("facility_name"),
                    "city": row.get("city") or "LAS VEGAS",
                    "state": "NV",
                    "dimension": dimension,
                    "requested_parameters": unknown,
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                }
                db.add(
                    AgentQueueItem(
                        queue_type=QUEUE_TYPE,
                        agent_key=agent_key,
                        payload_json=json.dumps(payload, sort_keys=True),
                        status="PENDING",
                        max_attempts=3,
                    )
                )
                newly_queued_keys.add(key)
                queued += 1

        db.commit()
        pending_backlog = existing_pending_count + queued
        if queued > 0 or pending_backlog > 0:
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

        return {
            "status": status,
            "market": "las-vegas",
            "market_scoped": True,
            "material_gaps": gaps,
            "tasks_queued": queued,
            "pending_backlog": pending_backlog,
            "researched_unknown_count": researched_unknown,
            "decision_finality": finality,
            "policy": "client intent first; resident unknown -> ask; facility MUST unknown -> agent research; unknown is not mismatch",
            "execution_mode": "BATCHED_DB_BRIDGE",
            "facility_count": len(canonical_ids),
            "database_prefetch": True,
        }
    except Exception as exc:
        db.rollback()
        _LOG.exception("batched agent evidence bridge unavailable")
        return {
            "status": "AGENT_BRIDGE_UNAVAILABLE",
            "market": "las-vegas",
            "market_scoped": True,
            "reason": exc.__class__.__name__,
            "tasks_queued": 0,
            "material_gaps": [],
            "decision_finality": "PROVISIONAL_AGENT_BRIDGE_UNAVAILABLE",
            "execution_mode": "BATCHED_DB_BRIDGE",
        }
    finally:
        db.close()


__all__ = ["attach_agent_evidence_and_queue_gaps_fast"]
