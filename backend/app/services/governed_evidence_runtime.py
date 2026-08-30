from __future__ import annotations

"""Single source of governed per-row evidence payloads.

Before this module existed, client_intent_runtime.py and combined_care_solution_runtime.py
each had their own separately-written function that read the same underlying row fields
(agent_person_fit_evidence, provider_housing_evidence, life_plan_primary_evidence) into a
flat list of payload dicts for MUST-gate and care-delivery checks to scan. They had quietly
diverged: one synthesized rehab_verified/pt_ot_verified/continuum_of_care_verified flags from
life-plan evidence, the other passed the raw life-plan dict through unchanged (which carries
none of those keys, so any future check for them there would silently see nothing). No
production check had tripped over it yet, but it is the same "two disagreeing sources of
truth for one fact" shape as the medication-evidence bug this was extracted alongside. Every
reader of agent/provider/life-plan evidence should call agent_and_provider_payloads() here
instead of re-deriving its own reading of these fields.
"""

import json
from typing import Any, Dict, List

from app.models.agent_execution import AgentKnowledgeRecord

_MARKET_TOKENS = {"las-vegas", "las vegas", "nevada"}
TRUSTED_POSITIVE_SOURCES = {"OFFICIAL_PROVIDER_WEBSITE", "NEVADA_HCQC_ALIS", "GOVERNMENT_REGULATORY_SOURCE"}


def _upper(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def bulk_agent_evidence(db: Any, canonical_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Bulk-fetch raw AgentKnowledgeRecord evidence for many canonical ids in one query,
    newest-first per facility. No market or source-trust filtering -- callers that need
    those apply them on top (see bulk_market_scoped_agent_evidence,
    is_governed_positive_source). Generalizes decision_agent_bridge.py's per-facility
    query and patient_decision_engine.py's medication overlay query (which duplicated
    the same fetch-and-parse for a bounded candidate set) into one query.
    """
    if not canonical_ids:
        return {}
    rows = (
        db.query(AgentKnowledgeRecord)
        .filter(AgentKnowledgeRecord.entity_key.in_(canonical_ids))
        .order_by(AgentKnowledgeRecord.entity_key, AgentKnowledgeRecord.id.desc())
        .all()
    )
    out: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        try:
            payload = json.loads(row.payload_json or "{}")
        except (TypeError, ValueError):
            payload = {}
        out.setdefault(str(row.entity_key), []).append({
            "agent_key": row.agent_key,
            "summary": row.summary,
            "confidence": float(row.confidence or 0.0),
            "source": row.source,
            "payload": payload,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    return out


def bulk_market_scoped_agent_evidence(db: Any, canonical_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Same as bulk_agent_evidence(), filtered to records whose payload market is
    Las Vegas/Nevada. Matches decision_agent_bridge.py's previous per-facility
    _market_evidence() filter exactly.
    """
    by_id = bulk_agent_evidence(db, canonical_ids)
    return {
        canonical_id: [record for record in records if str((record.get("payload") or {}).get("market") or "").lower() in _MARKET_TOKENS]
        for canonical_id, records in by_id.items()
    }


def is_governed_positive_source(source: Any, payload: Dict[str, Any]) -> bool:
    """Whether one agent record counts as a trustworthy source for a positive claim,
    matching decision_agent_bridge.py's trust policy: only certain source classes, and
    an official-website claim only counts once its identity is verified.

    Not yet applied by every consumer of agent evidence -- see
    _agent_verified_medication_overlay in patient_decision_engine.py, which currently
    accepts a positive medication_support_verified from any source. Whether to tighten
    that to require a governed source, same as decision_agent_bridge.py already does
    for the dynamic MUST-gate pipeline, is an open question flagged for a decision
    rather than changed unilaterally, since it could affect facilities the medication
    MUST-gate fix already resolved.
    """
    source_u = str(source or "").upper()
    if source_u not in TRUSTED_POSITIVE_SOURCES:
        return False
    if source_u == "OFFICIAL_PROVIDER_WEBSITE" and payload.get("official_identity_verified") is not True:
        return False
    return True


def agent_only_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten only agent-sourced evidence for one candidate row.

    Kept separate from agent_and_provider_payloads() because some callers (e.g.
    public-reputation fallback) intentionally trust only agent research, not
    provider/life-plan evidence, for certain facts.
    """
    agent_evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    return [item.get("payload") for item in agent_evidence if isinstance(item, dict) and isinstance(item.get("payload"), dict)]


def agent_and_provider_payloads(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten agent-sourced, provider-verified, and life-plan evidence for one
    candidate row into a single list of payload dicts, in a stable order
    (agent evidence first, then provider evidence, then life-plan-derived flags).
    """
    out: List[Dict[str, Any]] = list(agent_only_payloads(row))

    provider = row.get("provider_housing_evidence") if isinstance(row.get("provider_housing_evidence"), dict) else {}
    provider_evidence = provider.get("evidence") if isinstance(provider.get("evidence"), dict) else None
    if provider_evidence:
        out.append(provider_evidence)

    life_plan = row.get("life_plan_primary_evidence") if isinstance(row.get("life_plan_primary_evidence"), dict) else {}
    if life_plan:
        direct: Dict[str, Any] = {}
        if str(life_plan.get("rehabilitation_source_url") or "").startswith("http"):
            direct["rehab_verified"] = True
            direct["pt_ot_verified"] = True
        modalities = {_upper(value) for value in row.get("housing_modalities") or []}
        if "LIFE_PLAN_CCRC" in modalities:
            direct["continuum_of_care_verified"] = True
        if direct:
            out.append(direct)

    return out


__all__ = [
    "agent_only_payloads",
    "agent_and_provider_payloads",
    "bulk_agent_evidence",
    "bulk_market_scoped_agent_evidence",
    "is_governed_positive_source",
    "TRUSTED_POSITIVE_SOURCES",
]
