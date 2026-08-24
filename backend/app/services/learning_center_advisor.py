from __future__ import annotations

"""Learning Center advisory layer for decision-time semantic reasoning.

The AI interpreter is not allowed to reason in isolation. It receives a compact,
traceable advisory packet assembled from the domain's maintained knowledge agents.
This layer is read-only: agents/knowledge remain the source of expertise; the
interpreter consumes them under the decision constitution.
"""

import json
from typing import Any, Dict, List

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord, AgentKnowledgeReportSnapshot

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

DECISION_TIME_AGENT_KNOWLEDGE_MAX_CHARS = 1800


def _compact_payload(value: Any, max_chars: int = DECISION_TIME_AGENT_KNOWLEDGE_MAX_CHARS) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value or "").strip()
    return text if len(text) <= max_chars else text[: max_chars - 3] + "..."


def _decode_json_text(value: Any) -> Any:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return text


def build_learning_center_advice(*, user_text: str) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    with SessionLocal() as db:
        for agent_key in ADVISORY_AGENT_ORDER:
            report = (
                db.query(AgentKnowledgeReportSnapshot)
                .filter(AgentKnowledgeReportSnapshot.agent_key == agent_key)
                .order_by(AgentKnowledgeReportSnapshot.last_refreshed_at.desc())
                .first()
            )
            row = (
                db.query(AgentKnowledgeRecord)
                .filter(AgentKnowledgeRecord.agent_key == agent_key)
                .order_by(AgentKnowledgeRecord.id.desc())
                .first()
            )

            if report is not None:
                knowledge = _decode_json_text(getattr(report, "report_json", ""))
                records.append({
                    "agent_key": agent_key,
                    "status": "AVAILABLE",
                    "source_layer": "AGENT_KNOWLEDGE_REPORT_SNAPSHOT",
                    "freshness_state": str(getattr(report, "freshness_status", None) or "UNKNOWN"),
                    "health_status": str(getattr(report, "health_status", None) or "UNKNOWN"),
                    "knowledge": _compact_payload(knowledge),
                    "record_id": getattr(report, "id", None),
                    "knowledge_count": int(getattr(report, "knowledge_count", 0) or 0),
                    "evidence_count": int(getattr(report, "evidence_count", 0) or 0),
                    "coverage": float(getattr(report, "coverage", 0.0) or 0.0),
                    "updated_at": str(getattr(report, "last_refreshed_at", None) or ""),
                })
                continue

            if row is not None:
                payload = _decode_json_text(getattr(row, "payload_json", ""))
                if payload in ("", {}, []):
                    payload = getattr(row, "summary", "")
                records.append({
                    "agent_key": agent_key,
                    "status": "AVAILABLE",
                    "source_layer": "AGENT_KNOWLEDGE_RECORD",
                    "freshness_state": "UNKNOWN",
                    "health_status": "UNKNOWN",
                    "knowledge": _compact_payload(payload),
                    "record_id": getattr(row, "id", None),
                    "updated_at": str(getattr(row, "created_at", None) or ""),
                })
                continue

            records.append({
                "agent_key": agent_key,
                "status": "MISSING",
                "source_layer": "NONE",
                "freshness_state": "UNKNOWN",
                "health_status": "MISSING",
                "knowledge": "",
            })

    available = [r for r in records if r["status"] == "AVAILABLE"]
    fresh = [r for r in available if str(r.get("freshness_state") or "").upper() == "FRESH"]
    unhealthy = [r for r in available if str(r.get("health_status") or "").upper() not in {"HEALTHY", "UNKNOWN"}]
    return {
        "advisor": "OPTIME_NURSING_LEARNING_CENTER",
        "consulted": True,
        "user_text": user_text,
        "agent_count": len(records),
        "available_agent_count": len(available),
        "fresh_agent_count": len(fresh),
        "unhealthy_agent_count": len(unhealthy),
        "agents": records,
        "policy": {
            "role": "ADVISORY_NOT_AUTHORITATIVE",
            "prefer_fresh_agent_reports": True,
            "decision_time_knowledge_budget_chars_per_agent": DECISION_TIME_AGENT_KNOWLEDGE_MAX_CHARS,
            "unknown_remains_unknown": True,
            "must_not_invent_facility_facts": True,
            "must_preserve_user_meaning": True,
            "missing_or_stale_material_knowledge_requires_research": True,
        },
    }


__all__ = ["build_learning_center_advice", "ADVISORY_AGENT_ORDER", "DECISION_TIME_AGENT_KNOWLEDGE_MAX_CHARS"]
