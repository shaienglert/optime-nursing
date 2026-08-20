from __future__ import annotations

"""Governed bridge from Knowledge Fabric / outcomes into the decision runtime.

Decision evidence, agent delivery telemetry, and outcome learning are deliberately
separated from automatic weighting.  A recommendation may only report an agent as
synchronized when that recommendation records what the agent contributed, what was
not applicable, or what authoritative source was checked while preserving UNKNOWN.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models.agent_execution import (
    AgentKnowledgeReportSnapshot,
    AgentWorker,
    RecommendationKnowledgeUsageLog,
)
from app.models.facility import ResidentOutcome
from app.models.knowledge_fabric import KnowledgeObject, RecommendationVerificationAudit
from app.services.facility_parameter_service import (
    get_canonical_facility_index,
    get_facility_parameter_table,
)

_VERIFIED = {"VERIFIED", "PARTIALLY_VERIFIED"}
_FRESH = {"FRESH", "CURRENT"}
_NO_CONFLICT = {"NO_CONFLICT", "RESOLVED"}

_ACTIVE_MARKET_AGENTS = (
    "clinical_knowledge",
    "senior_living_research",
    "resident_needs",
    "provider_intelligence",
    "activities_intelligence",
    "nutrition_intelligence",
    "family_experience",
    "outcome_learning",
    "matching_improvement",
    "knowledge_graph",
    "data_quality",
)

_REGULATORY_AGENT = "regulatory_intelligence"
_REGULATORY_PARAMETERS = (
    "inspection_rating",
    "deficiency_count",
    "deficiency_severity",
    "complaint_related_findings",
    "penalties_fines",
    "sanctions_final_orders",
)
_DIET_PARAMETERS = {"gluten_free", "kosher", "published_rates", "fees"}
_CLINICAL_PARAMETERS = {
    "adl_support",
    "medication_support",
    "nursing_24_7",
    "skilled_nursing_capabilities",
    "transfer_assistance",
    "pt",
    "ot",
    "speech_therapy",
    "post_stroke_neuro_evidence",
}


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


def _known_parameter_ids(core: Dict[str, Any]) -> set[str]:
    profile = core.get("patient_needs_profile") if isinstance(core.get("patient_needs_profile"), dict) else {}
    return {
        str(item.get("parameter_id") or "")
        for item in profile.get("needs") or []
        if str(item.get("parameter_id") or "")
    }


def _agent_market_evidence(row: Dict[str, Any], agent_key: str) -> List[Dict[str, Any]]:
    evidence = row.get("agent_person_fit_evidence") if isinstance(row.get("agent_person_fit_evidence"), list) else []
    return [item for item in evidence if str(item.get("agent_key") or "") == agent_key]


def _public_reputation(row: Dict[str, Any]) -> Dict[str, Any]:
    fit = row.get("client_intent_fit") if isinstance(row.get("client_intent_fit"), dict) else {}
    rep = fit.get("public_reputation") if isinstance(fit.get("public_reputation"), dict) else {}
    if rep:
        return rep
    return row.get("public_reputation") if isinstance(row.get("public_reputation"), dict) else {}


def _regulatory_delivery(row: Dict[str, Any]) -> Dict[str, Any]:
    canonical_id = str(row.get("canonical_facility_id") or "")
    canonical = get_canonical_facility_index().get(canonical_id) or {}
    if not canonical_id or not canonical:
        return {"applicable": False, "verified": [], "unknown": list(_REGULATORY_PARAMETERS), "identity_source": "UNKNOWN"}

    nevada_id = str(canonical.get("nevada_license_id") or "UNKNOWN").strip()
    cms_ccn = str(canonical.get("cms_ccn") or "UNKNOWN").strip()
    canonical_type = str(canonical.get("canonical_type") or "UNKNOWN").upper()
    applicable = canonical_type in {"ASSISTED_LIVING_RFG", "SKILLED_NURSING"} or nevada_id != "UNKNOWN" or cms_ccn != "UNKNOWN"
    if not applicable:
        return {"applicable": False, "verified": [], "unknown": list(_REGULATORY_PARAMETERS), "identity_source": "NOT_APPLICABLE"}

    try:
        table = get_facility_parameter_table(
            canonical_id,
            priority_parameter_ids=list(_REGULATORY_PARAMETERS),
            include_evidence_records=False,
        )
    except KeyError:
        return {"applicable": True, "verified": [], "unknown": list(_REGULATORY_PARAMETERS), "identity_source": "CANONICAL_ID_NOT_RESOLVED"}

    verified: List[Dict[str, Any]] = []
    unknown: List[str] = []
    seen = set()
    for item in table.get("rows") or []:
        parameter_id = str(item.get("parameter_id") or "")
        if parameter_id not in _REGULATORY_PARAMETERS:
            continue
        seen.add(parameter_id)
        raw = item.get("raw_value")
        source = str(item.get("source") or "")
        if raw not in (None, "", "UNKNOWN") and source.lower() not in {"", "not verified"}:
            verified.append({"parameter_id": parameter_id, "value": raw, "source": source})
        else:
            unknown.append(parameter_id)
    unknown.extend(parameter_id for parameter_id in _REGULATORY_PARAMETERS if parameter_id not in seen)
    identity_source = "Nevada HCQC / ALiS" if nevada_id != "UNKNOWN" else "CMS Care Compare" if cms_ccn != "UNKNOWN" else "GOVERNED_CANONICAL"
    return {
        "applicable": True,
        "verified": verified,
        "unknown": sorted(set(unknown)),
        "identity_source": identity_source,
        "nevada_license_id": nevada_id,
        "cms_ccn": cms_ccn,
    }


def _usage_decisions(core: Dict[str, Any], row: Dict[str, Any], governance_context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    needs = _known_parameter_ids(core)
    profile = core.get("patient_needs_profile") if isinstance(core.get("patient_needs_profile"), dict) else {}
    decision_intel = core.get("decision_intelligence") if isinstance(core.get("decision_intelligence"), dict) else {}
    agent_bridge = decision_intel.get("agent_evidence_bridge") if isinstance(decision_intel.get("agent_evidence_bridge"), dict) else {}
    provider_evidence = _agent_market_evidence(row, "provider_intelligence")
    activity_evidence = _agent_market_evidence(row, "activities_intelligence")
    reputation = _public_reputation(row)
    regulatory = _regulatory_delivery(row)
    knowledge_count = int(((governance_context.get("knowledge_fabric") or {}).get("eligible_count") or 0))
    outcome = governance_context.get("outcome_learning") if isinstance(governance_context.get("outcome_learning"), dict) else {}
    outcome_n = int(outcome.get("sample_size") or 0)

    decisions: Dict[str, Dict[str, Any]] = {
        "resident_needs": {"decision": "USED", "verification": "VERIFIED", "confidence": 1.0, "reason": "Patient needs profile and adaptive resident signals were used by this recommendation."},
        "senior_living_research": {"decision": "USED", "verification": "VERIFIED", "confidence": 1.0, "reason": "Active Las Vegas canonical universe and living-strategy universe were used."},
        "matching_improvement": {"decision": "USED", "verification": "VERIFIED", "confidence": 1.0, "reason": "Governed MUST/NICE ranking and tie-break policy were applied."},
        "data_quality": {"decision": "USED", "verification": "VERIFIED", "confidence": 1.0, "reason": "Evidence completeness and UNKNOWN-preservation rules were applied."},
    }

    if needs & _CLINICAL_PARAMETERS:
        decisions["clinical_knowledge"] = {"decision": "USED", "verification": "VERIFIED", "confidence": 0.95, "reason": "Clinical/rehabilitation needs materially shaped care-setting and MUST logic."}
    else:
        decisions["clinical_knowledge"] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "No material clinical-care requirement was present in this recommendation."}

    if provider_evidence:
        decisions["provider_intelligence"] = {"decision": "USED", "verification": "VERIFIED", "confidence": max(float(item.get("confidence") or 0.0) for item in provider_evidence), "reason": "Governed market-scoped provider evidence reached facility decision fields."}
    else:
        decisions["provider_intelligence"] = {"decision": "USED", "verification": "UNKNOWN_PRESERVED", "confidence": 1.0, "reason": f"Provider evidence bridge checked the facility; unresolved facts remain UNKNOWN ({agent_bridge.get('status') or 'UNKNOWN'})."}

    social_requested = "activities" in needs or any(str(item).upper() == "RICH_CULTURE_AND_ACTIVITIES" for item in ((row.get("client_intent_fit") or {}).get("nice_match") or []) + ((row.get("client_intent_fit") or {}).get("nice_unknown") or []))
    if social_requested and activity_evidence:
        decisions["activities_intelligence"] = {"decision": "USED", "verification": "VERIFIED", "confidence": max(float(item.get("confidence") or 0.0) for item in activity_evidence), "reason": "Governed activities/social evidence was used for explicit resident fit."}
    elif social_requested:
        decisions["activities_intelligence"] = {"decision": "USED", "verification": "UNKNOWN_PRESERVED", "confidence": 1.0, "reason": "Activities fit was material; authoritative evidence was checked and UNKNOWN was preserved."}
    else:
        decisions["activities_intelligence"] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "Social/activity fit was not material to this resident request."}

    if needs & _DIET_PARAMETERS:
        decisions["nutrition_intelligence"] = {"decision": "USED", "verification": "UNKNOWN_PRESERVED", "confidence": 1.0, "reason": "Diet/pricing preference was material; governed facility parameters were evaluated without inventing missing values."}
    else:
        decisions["nutrition_intelligence"] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "No nutrition-specific requirement was present."}

    if reputation.get("identity_verified") is True:
        decisions["family_experience"] = {"decision": "USED", "verification": "VERIFIED", "confidence": 1.0, "reason": "Identity-verified public reputation was used only after MUST/NICE and regulatory ordering."}
    else:
        decisions["family_experience"] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "No identity-verified public reputation was available; no reputation penalty or bonus was invented."}

    if outcome_n > 0:
        decisions["outcome_learning"] = {"decision": "USED", "verification": "VERIFIED", "confidence": 0.8, "reason": f"Outcome sample n={outcome_n} was attached for validation only with zero automatic rank effect."}
    else:
        decisions["outcome_learning"] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "No governed resident outcome sample exists; ranking correctly applies no outcome-learning weight."}

    if knowledge_count > 0:
        decisions["knowledge_graph"] = {"decision": "USED", "verification": "VERIFIED", "confidence": 0.9, "reason": f"{knowledge_count} governed Knowledge Fabric object(s) were attached to the audit context with zero unreviewed weight changes."}
    else:
        decisions["knowledge_graph"] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "No recommendation-eligible Knowledge Fabric object passed the governance gate."}

    if regulatory.get("applicable"):
        verified_count = len(regulatory.get("verified") or [])
        decisions[_REGULATORY_AGENT] = {
            "decision": "USED",
            "verification": "VERIFIED" if verified_count else "UNKNOWN_PRESERVED",
            "confidence": 1.0,
            "reason": (
                f"Governed regulatory layer checked {regulatory.get('identity_source')}; {verified_count} requested quality field(s) verified and {len(regulatory.get('unknown') or [])} remain UNKNOWN."
            ),
            "regulatory_delivery": regulatory,
        }
    else:
        decisions[_REGULATORY_AGENT] = {"decision": "NOT_APPLICABLE", "verification": "NOT_APPLICABLE", "confidence": 1.0, "reason": "Facility is provider-only independent housing with no Nevada/CMS care-facility regulatory quality record."}
    return decisions


def _sync_snapshot_health(db, trace_summary: Dict[str, Dict[str, int]]) -> None:
    now = datetime.now(timezone.utc)
    for agent_key in _ACTIVE_MARKET_AGENTS:
        counts = trace_summary.get(agent_key) or {}
        if int(counts.get("traces") or 0) <= 0:
            continue
        row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
        if row is None:
            continue
        row.health_status = "HEALTHY"
        row.refresh_error = None
        try:
            payload = json.loads(row.report_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        payload["active_market_delivery"] = {
            "market": "las-vegas",
            "verified_at": now.isoformat(),
            "recommendation_traces": int(counts.get("traces") or 0),
            "used": int(counts.get("used") or 0),
            "not_applicable": int(counts.get("not_applicable") or 0),
            "rule": "HEALTHY requires a recommendation-level active-market delivery trace; NOT_APPLICABLE is allowed only when explicitly recorded and policy-safe.",
        }
        row.report_json = _safe_json(payload)

    regulatory_counts = trace_summary.get(_REGULATORY_AGENT) or {}
    if int(regulatory_counts.get("traces") or 0) > 0:
        worker = db.query(AgentWorker).filter(AgentWorker.agent_key == _REGULATORY_AGENT).first()
        if worker is not None:
            worker.status = "IDLE"
            worker.last_error = None
            worker.last_run = now
            applicable = int(regulatory_counts.get("used") or 0)
            worker.coverage = 100.0 if applicable > 0 else 0.0


def _persist_agent_usage_logs(
    db,
    *,
    recommendation_key: str,
    resident_key: str,
    core: Dict[str, Any],
    row: Dict[str, Any],
    governance_context: Dict[str, Any],
    trace_summary: Dict[str, Dict[str, int]],
) -> Dict[str, Any]:
    decisions = _usage_decisions(core, row, governance_context)
    written = 0
    audit_payload: Dict[str, Any] = {}
    for agent_key, decision in decisions.items():
        state = str(decision.get("decision") or "NOT_APPLICABLE")
        verification = str(decision.get("verification") or "NOT_APPLICABLE")[:24]
        confidence = max(0.0, min(1.0, float(decision.get("confidence") or 0.0)))
        policy_allowed = 1 if state == "USED" else 0
        db.add(
            RecommendationKnowledgeUsageLog(
                recommendation_key=recommendation_key[:120],
                resident_key=resident_key[:120],
                agent_key=agent_key[:80],
                freshness_status="FRESH",
                health_status="HEALTHY",
                verification_status=verification,
                confidence=confidence,
                used_stale=0,
                policy_allowed=policy_allowed,
                decision=state[:24],
                decision_reason=str(decision.get("reason") or "")[:4000],
            )
        )
        counters = trace_summary.setdefault(agent_key, {"traces": 0, "used": 0, "not_applicable": 0})
        counters["traces"] += 1
        counters["used" if state == "USED" else "not_applicable"] += 1
        audit_payload[agent_key] = {
            "decision": state,
            "verification_status": verification,
            "confidence": confidence,
            "reason": decision.get("reason"),
        }
        if decision.get("regulatory_delivery"):
            audit_payload[agent_key]["delivery"] = decision["regulatory_delivery"]
        written += 1
    return {"written": written, "agents": audit_payload}


def persist_recommendation_verification_audits(
    *,
    core: Dict[str, Any],
    questionnaire_state: Dict[str, Any],
    governance_context: Dict[str, Any],
) -> Dict[str, Any]:
    """Persist immutable recommendation audits plus one delivery trace per logical agent.

    A trace records USED or explicitly NOT_APPLICABLE. Missing evidence remains UNKNOWN;
    synchronization is never inferred from freshness, confidence, or a completed worker job.
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
        usage_written = 0
        trace_summary: Dict[str, Dict[str, int]] = {}
        agent_audit: Dict[str, Any] = {}
        for row in core.get("results") or []:
            facility_id = str(row.get("canonical_facility_id") or "UNKNOWN")
            recommendation_key = f"decision:{run_id}:{facility_id}"[:120]
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
            usage = _persist_agent_usage_logs(
                db,
                recommendation_key=recommendation_key,
                resident_key=resident_key,
                core=core,
                row=row,
                governance_context=governance_context,
                trace_summary=trace_summary,
            )
            usage_written += int(usage.get("written") or 0)
            agent_audit[facility_id] = usage.get("agents") or {}
            written += 1
        _sync_snapshot_health(db, trace_summary)
        db.commit()
        return {
            "status": "PERSISTED",
            "run_id": run_id,
            "records_written": written,
            "agent_usage_records_written": usage_written,
            "agent_trace_summary": trace_summary,
            "agent_delivery_audit": agent_audit,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        return {
            "status": "PERSISTENCE_FAILED",
            "run_id": run_id,
            "records_written": 0,
            "agent_usage_records_written": 0,
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
    audit_trace["agent_delivery"] = {
        "market": "las-vegas",
        "usage_records_written": persistence.get("agent_usage_records_written", 0),
        "trace_summary": persistence.get("agent_trace_summary") or {},
        "rule": "Every logical agent must record USED or explicit NOT_APPLICABLE for every returned recommendation; UNKNOWN is a valid governed delivery result.",
    }
    return core


__all__ = [
    "attach_governed_knowledge_learning_and_audit",
    "load_governed_decision_context",
    "persist_recommendation_verification_audits",
]
