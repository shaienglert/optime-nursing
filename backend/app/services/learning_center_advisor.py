from __future__ import annotations

"""Learning Center advisory layer for decision-time semantic reasoning.

The AI interpreter is not allowed to reason in isolation. It receives a compact,
traceable advisory packet assembled from the domain's maintained knowledge agents.
This layer is read-only: agents/knowledge remain the source of expertise; the
interpreter consumes them under the decision constitution.
"""

from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord

ADVISORY_AGENT_ORDER = [
    "resident_needs",
    "nutrition_intelligence",
    "activities_intelligence",
    "senior_living_research",
    "provider_intelligence",
    "family_experience",
    "outcome_learning",
    "matching_improvement",
    "knowledge_graph",
    "data_quality",
]


def _compact_payload(value: Any, max_chars: int = 3500) -> str:
    text = str(value or "").strip()
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def build_learning_center_advice(*, user_text: str) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    with SessionLocal() as db:
        for agent_key in ADVISORY_AGENT_ORDER:
            row = (
                db.query(AgentKnowledgeRecord)
                .filter(AgentKnowledgeRecord.agent_key == agent_key)
                .order_by(AgentKnowledgeRecord.id.desc())
                .first()
            )
            if row is None:
                records.append({
                    "agent_key": agent_key,
                    "status": "MISSING",
                    "freshness_state": "UNKNOWN",
                    "knowledge": "",
                })
                continue
            payload = getattr(row, "knowledge_payload", None) or getattr(row, "payload", None) or getattr(row, "summary", None)
            records.append({
                "agent_key": agent_key,
                "status": "AVAILABLE",
                "freshness_state": str(getattr(row, "freshness_state", None) or "UNKNOWN"),
                "knowledge": _compact_payload(payload),
                "record_id": getattr(row, "id", None),
                "updated_at": str(getattr(row, "updated_at", None) or getattr(row, "created_at", None) or ""),
            })

    available = [r for r in records if r["status"] == "AVAILABLE"]
    return {
        "advisor": "OPTIME_NURSING_LEARNING_CENTER",
        "consulted": True,
        "user_text": user_text,
        "agent_count": len(records),
        "available_agent_count": len(available),
        "agents": records,
        "policy": {
            "role": "ADVISORY_NOT_AUTHORITATIVE",
            "unknown_remains_unknown": True,
            "must_not_invent_facility_facts": True,
            "must_preserve_user_meaning": True,
        },
    }


__all__ = ["build_learning_center_advice", "ADVISORY_AGENT_ORDER"]
