from __future__ import annotations

"""Governed bridge from Knowledge Fabric / outcomes into the decision runtime.

This module deliberately separates *decision evidence* from *automatic weighting*.
Only active, recommendation-eligible, verified, fresh, conflict-free Knowledge
Objects are surfaced to the recommendation trace. Resident outcomes are exposed
as validation/learning context with sample size, but never change ranking weights
automatically. Every recommendation run can be persisted to the existing
RecommendationVerificationAudit table for reproducibility.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models.facility import ResidentOutcome
from app.models.knowledge_fabric import KnowledgeObject, RecommendationVerificationAudit

_VERIFIED = {"VERIFIED", "PARTIALLY_VERIFIED"}
_FRESH = {"FRESH", "CURRENT"}
_NO_CONFLICT = {"NO_CONFLICT", "RESOLVED"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _eligible_knowledge_objects(db) -> List[KnowledgeObject]:
    rows = (
        db.query(KnowledgeObject)
        .filter(KnowledgeObject.status == "ACTIVE")
        .filter(KnowledgeObject.recommendation_eligible == 1)
        .all()
    )
    return [
        row
        for row in rows
        if str(row.verification_status or "").upper() in _VERIFIED
        and str(row.freshness_status or "").upper() in _FRESH
        and str(row.conflict_status or "").upper() in _NO_CONFLICT
        and float(row.confidence or 0.0) > 0.0
    ]


def _knowledge_payload(rows: Iterable[KnowledgeObject]) -> Dict[str, Any]:
    objects = []
    for row in rows:
        objects.append(
            {
                "id": row.id,
                "object_key": row.object_key,
                "title": row.title,
                "category": row.category,
                "topic": row.topic,
                "entity_type": row.entity_type,
                "entity_key": row.entity_key,
                "property_name": row.property_name,
                "fact_value": row.fact_value,
                "source_name": row.source_name,
                "source_type": row.source_type,
                "source_reference": row.source_reference,
                "evidence_key": row.evidence_key,
                "evidence_summary": row.evidence_summary,
                "trust_level": row.trust_level,
                "confidence": float(row.confidence or 0.0),
                "verification_status": row.verification_status,
                "freshness_status": row.freshness_status,
                "conflict_status": row.conflict_status,
                "evidence_strength": row.evidence_strength,
                "version": row.version,
            }
        )
    return {
        "policy": "AUDIT_AND_EVIDENCE_ONLY_UNLESS_EXPLICITLY_MAPPED_BY_GOVERNED_DECISION_RULE",
        "eligibility_gate": [
            "status=ACTIVE",
            "recommendation_eligible=1",
            "verification_status in VERIFIED/PARTIALLY_VERIFIED",
            "freshness_status in FRESH/CURRENT",
            "conflict_status in NO_CONFLICT/RESOLVED",
            "confidence>0",
        ],
        "eligible_count": len(objects),
        "objects": objects,
        "automatic_rank_effect": "NONE",
    }


def _outcome_payload(db) -> Dict[str, Any]:
    rows: List[ResidentOutcome] = db.query(ResidentOutcome).all()
    n = len(rows)
    if not n:
        return {
            "policy": "LEARNING_VALIDATION_ONLY_NO_AUTOMATIC_WEIGHT_CHANGE",
            "sample_size": 0,
            "status": "NO_OUTCOME_SAMPLE",
            "automatic_rank_effect": "NONE",
        }
    success = sum(1 for row in rows if bool(row.successful_adjustment))
    loneliness = sum(1 for row in rows if bool(row.loneliness_event))
    relocation = sum(1 for row in rows if bool(row.relocated_within_24m))
    return {
        "policy": "LEARNING_VALIDATION_ONLY_NO_AUTOMATIC_WEIGHT_CHANGE",
        "sample_size": n,
        "successful_adjustment_rate": round(success / n, 4),
        "loneliness_event_rate": round(loneliness / n, 4),
        "relocated_within_24m_rate": round(relocation / n, 4),
        "status": "OBSERVATIONAL_NOT_CAUSAL",
        "automatic_rank_effect": "NONE",
        "governance_requirement": "Any future weight change requires explicit reviewed rule/version, sufficient sample, validation, and rollback path.",
    }


def load_governed_decision_context() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        knowledge = _knowledge_payload(_eligible_knowledge_objects(db))
        outcomes = _outcome_payload(db)
        return {
            "status": "CONNECTED",
            "generated_at": _utc_now_iso(),
            "knowledge_fabric": knowledge,
            "outcome_learning": outcomes,
        }
    except SQLAlchemyError as exc:
        return {
            "status": "UNAVAILABLE",
            "generated_at": _utc_now_iso(),
            "reason": exc.__class__.__name__,
            "knowledge_fabric": {
                "eligible_count": 0,
                "objects": [],
                "automatic_rank_effect": "NONE",
            },
            "outcome_learning": {
                "sample_size": 0,
                "automatic_rank_effect": "NONE",
            },
        }
    finally:
        db.close()


def persist_recommendation_verification_audits(
    *,
    core: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    governance_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist one immutable audit row per returned recommendation.

    Failure to persist never changes a recommendation; it is surfaced explicitly
    in the returned audit status so observability cannot silently pretend success.
    """
    model_version = str((core.get("decision_intelligence") or {}).get("version") or "unknown")
    audit_trace = core.get("recommendation_audit_trace") or {}
    knowledge_objects = ((governance_context.get("knowledge_fabric") or {}).get("objects") or [])
    knowledge_ids = [item.get("id") for item in knowledge_objects if item.get("id") is not None]
    knowledge_refs = [
        item.get("source_reference") or item.get("evidence_key") or item.get("object_key")
        for item in knowledge_objects
    ]
    resident_key = str(
        questionnaire_state.get("resident_key")
        or questionnaire_state.get("residentKey")
        or "ANONYMOUS_SESSION"
    )
    run_seed = _safe_json(
        {
            "resident_key": resident_key,
            "model_version": model_version,
            "questionnaire": questionnaire_state,
            "facilities": [row.get("canonical_facility_id") for row in core.get("results") or []],
            "timestamp": _utc_now_iso(),
        }
    )
    run_id = hashlib.sha256(run_seed.encode("utf-8")).hexdigest()[:24]

    db = SessionLocal()
    try:
        written = 0
        for row in core.get("results") or []:
            facility_id = str(row.get("canonical_facility_id") or "UNKNOWN")
            recommendation_key = f"decision:{run_id}:{facility_id}"[:160]
            db.add(
                RecommendationVerificationAudit(
                    recommendation_key=recommendation_key,
                    resident_key=resident_key[:160],
                    facts_used_json=_safe_json(
                        {
                            "patient_needs": (audit_trace.get("facts_used") or {}).get("patient_needs") or [],
                            "human_signals": (audit_trace.get("facts_used") or {}).get("human_signals") or {},
                            "facility": {
                                "canonical_facility_id": facility_id,
                                "eligibility_status": row.get("eligibility_status"),
                                "care_setting_fit": (row.get("care_setting_fit") or {}).get("status"),
                                "patient_match_score": row.get("patient_match_score"),
                                "success_factor_trace": row.get("success_factor_trace") or {},
                            },
                        }
                    ),
                    knowledge_object_ids_json=_safe_json(knowledge_ids),
                    evidence_references_json=_safe_json(
                        list(dict.fromkeys((audit_trace.get("evidence_references") or []) + knowledge_refs))
                    ),
                    decision_rules_applied_json=_safe_json(audit_trace.get("decision_rules_applied") or []),
                    professional_judgment_json=_safe_json(
                        {
                            "automatic_knowledge_rank_effect": "NONE",
                            "automatic_outcome_rank_effect": "NONE",
                            "unknown_policy": "UNKNOWN_REMAINS_UNKNOWN",
                        }
                    ),
                    model_version=model_version[:80],
                )
            )
            written += 1
        db.commit()
        return {"status": "PERSISTED", "run_id": run_id, "records_written": written}
    except SQLAlchemyError as exc:
        db.rollback()
        return {
            "status": "PERSISTENCE_FAILED",
            "run_id": run_id,
            "records_written": 0,
            "reason": exc.__class__.__name__,
        }
    finally:
        db.close()


def attach_governed_knowledge_learning_and_audit(
    *,
    core: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
) -> Dict[str, Any]:
    context = load_governed_decision_context()
    decision_intelligence = core.setdefault("decision_intelligence", {})
    decision_intelligence["governed_knowledge_learning"] = context
    persistence = persist_recommendation_verification_audits(
        core=core,
        questionnaire_state=questionnaire_state,
        governance_context=context,
    )
    audit_trace = core.setdefault("recommendation_audit_trace", {})
    audit_trace["persistence"] = persistence
    audit_trace["knowledge_fabric"] = {
        "status": context.get("status"),
        "eligible_count": ((context.get("knowledge_fabric") or {}).get("eligible_count") or 0),
        "automatic_rank_effect": "NONE",
    }
    audit_trace["outcome_learning"] = context.get("outcome_learning") or {}
    return core


__all__ = [
    "attach_governed_knowledge_learning_and_audit",
    "load_governed_decision_context",
    "persist_recommendation_verification_audits",
]
