from __future__ import annotations

"""Canonical facility evidence runtime for Nursing V2.

Combines the canonical market inventory, OPTIME parameter table and persisted semantic
agent evidence into one downstream facility truth. It does not interpret client text or
make ranking decisions.
"""

import json
from collections import defaultdict
from typing import Any, Dict, List, Sequence

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord
from app.services.facility_parameter_service import (
    get_canonical_facility_index,
    get_facility_parameter_table,
    get_parameter_registry_payload,
)
from app.services.semantic_evidence_ai import CAPABILITY_SCHEMA


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def _parameter_index(table: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("parameter_id")): row
        for row in table.get("rows") or []
        if isinstance(row, dict) and str(row.get("parameter_id") or "").strip()
    }


def _load_agent_evidence(canonical_ids: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    ids = [str(value) for value in canonical_ids if str(value)]
    if not ids:
        return out
    db = SessionLocal()
    try:
        rows = (
            db.query(AgentKnowledgeRecord)
            .filter(AgentKnowledgeRecord.entity_key.in_(ids))
            .order_by(AgentKnowledgeRecord.id.desc())
            .all()
        )
        for row in rows:
            try:
                payload = json.loads(row.payload_json or "{}")
            except json.JSONDecodeError:
                continue
            market = str(payload.get("market") or "").strip().lower()
            if market and market not in {"las-vegas", "las vegas", "nevada"}:
                continue
            out[str(row.entity_key)].append(
                {
                    "record_id": int(row.id),
                    "agent_key": str(row.agent_key or ""),
                    "source": str(row.source or ""),
                    "confidence": float(row.confidence or 0.0),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "payload": payload,
                }
            )
    finally:
        db.close()
    return out


def _semantic_service_levels(agent_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Use the newest validated semantic interpretation for each capability.

    `NONE_OR_NOT_STATED` is evidence absence, not a verified negative capability.
    """
    levels: Dict[str, Dict[str, Any]] = {}
    for record in agent_records:
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        interpretation = payload.get("semantic_evidence_interpretation") if isinstance(payload.get("semantic_evidence_interpretation"), dict) else {}
        if interpretation.get("closed_world_validated") is not True:
            continue
        for item in interpretation.get("capabilities") or []:
            if not isinstance(item, dict):
                continue
            capability = _norm(item.get("capability"))
            if capability not in CAPABILITY_SCHEMA or capability in levels:
                continue
            level = _norm(item.get("level"))
            if level not in CAPABILITY_SCHEMA[capability].get("levels", []):
                continue
            levels[capability] = {
                "capability": capability,
                "level": level,
                "confidence": _norm(item.get("confidence"),),
                "evidence_summary": str(item.get("evidence_summary") or "").strip(),
                "source_url": payload.get("source_url"),
                "observed_at": payload.get("observed_at") or record.get("created_at"),
                "agent_record_id": record.get("record_id"),
                "source": record.get("source"),
                "semantic_interpretation": True,
            }
    return levels


def _positive_agent_parameter_evidence(agent_records: List[Dict[str, Any]], known_parameter_ids: set[str]) -> Dict[str, Dict[str, Any]]:
    """Promote only positive verified agent facts into canonical parameters.

    A False field in research payload often means "not found", not an explicit NO, so
    it may never overwrite UNKNOWN/YES as negative evidence.
    """
    promoted: Dict[str, Dict[str, Any]] = {}
    for record in agent_records:
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        for key, value in payload.items():
            if value is not True or not str(key).endswith("_verified"):
                continue
            parameter_id = str(key)[: -len("_verified")]
            if parameter_id not in known_parameter_ids or parameter_id in promoted:
                continue
            promoted[parameter_id] = {
                "parameter_id": parameter_id,
                "raw_value": "YES",
                "status_value": "YES",
                "source": record.get("source") or "SEMANTIC_AGENT_EVIDENCE",
                "last_verified": payload.get("observed_at") or record.get("created_at"),
                "evidence_confidence": record.get("confidence"),
                "evidence_strength": "SEMANTIC_PROVIDER_VERIFIED",
                "provenance": {
                    "agent_record_id": record.get("record_id"),
                    "source_url": payload.get("source_url"),
                    "evidence_interpretation_mode": payload.get("evidence_interpretation_mode"),
                },
                "evidence_count": 1,
                "evidence_records": [],
            }
    return promoted


def merge_canonical_facility_evidence(
    *,
    candidate: Dict[str, Any],
    parameter_table: Dict[str, Any],
    agent_records: List[Dict[str, Any]],
    known_parameter_ids: set[str],
) -> Dict[str, Any]:
    parameters = _parameter_index(parameter_table)
    promoted = _positive_agent_parameter_evidence(agent_records, known_parameter_ids)
    for parameter_id, agent_row in promoted.items():
        current = parameters.get(parameter_id)
        current_value = _norm((current or {}).get("raw_value"))
        # Positive governed semantic evidence may fill UNKNOWN, but we retain a direct
        # explicit NO for conflict review instead of silently overwriting it.
        if current_value in {"", "UNKNOWN", "NONE"}:
            parameters[parameter_id] = agent_row
        elif current_value == "NO":
            parameters[parameter_id] = {
                **current,
                "conflict_status": "CONFLICT",
                "conflicting_agent_evidence": agent_row,
            }

    return {
        "version": "canonical-facility-evidence-state-v2",
        "canonical_evidence_state": True,
        "canonical_facility_id": candidate.get("canonical_id") or candidate.get("canonical_facility_id"),
        "facility_name": parameter_table.get("facility_name") or candidate.get("facility_name") or candidate.get("name"),
        "city": parameter_table.get("city") or candidate.get("city"),
        "state": parameter_table.get("state") or candidate.get("state"),
        "canonical_type": parameter_table.get("canonical_type") or candidate.get("canonical_type"),
        "role_classification": parameter_table.get("role_classification") or candidate.get("role_classification"),
        "housing_modalities": list(candidate.get("housing_modalities") or []),
        "parameters": parameters,
        "semantic_service_levels": _semantic_service_levels(agent_records),
        "agent_evidence_record_count": len(agent_records),
        "evidence_rule": "One canonical facility evidence state feeds MUST, AI ranking, NICE verification and explanation. Missing evidence remains UNKNOWN; research non-findings never become NO.",
    }


class CanonicalFacilityRuntimeV2:
    """Batch-aware adapter used by the explicit V2 orchestrator."""

    def __init__(self) -> None:
        registry = get_parameter_registry_payload()
        self.known_parameter_ids = {
            str(row.get("parameter_id"))
            for row in registry.get("records") or []
            if isinstance(row, dict) and str(row.get("parameter_id") or "").strip()
        }
        self._agent_evidence: Dict[str, List[Dict[str, Any]]] = {}

    def load_candidate_universe(self, client_state: Dict[str, Any]) -> Sequence[Dict[str, Any]]:
        # The configured canonical runtime is already market-scoped (Las Vegas Valley
        # for the current Nursing production market). Do not use raw client text here.
        index = get_canonical_facility_index()
        rows = [dict(value) for value in index.values()]
        ids = [str(row.get("canonical_id") or row.get("canonical_facility_id") or "") for row in rows]
        self._agent_evidence = _load_agent_evidence(ids)
        return rows

    def load_facility_state(self, candidate: Dict[str, Any], client_state: Dict[str, Any]) -> Dict[str, Any]:
        canonical_id = str(candidate.get("canonical_id") or candidate.get("canonical_facility_id") or "")
        if not canonical_id:
            raise RuntimeError("V2_CANONICAL_UNIVERSE_ROW_WITHOUT_ID")
        priority_parameter_ids = sorted(
            {
                str(parameter_id)
                for requirement in client_state.get("requirements") or []
                if isinstance(requirement, dict)
                for parameter_id in requirement.get("evidence_parameter_ids") or []
                if str(parameter_id)
            }
        )
        table = get_facility_parameter_table(
            canonical_id,
            priority_parameter_ids=priority_parameter_ids,
            include_evidence_records=False,
        )
        return merge_canonical_facility_evidence(
            candidate=candidate,
            parameter_table=table,
            agent_records=self._agent_evidence.get(canonical_id, []),
            known_parameter_ids=self.known_parameter_ids,
        )


__all__ = ["CanonicalFacilityRuntimeV2", "merge_canonical_facility_evidence"]
