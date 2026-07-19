from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.agent_execution import RecommendationKnowledgeUsageLog
from app.models.facility import Facility
from app.models.knowledge_fabric import KnowledgeEvidence, KnowledgeObject, RecommendationVerificationAudit


SOURCE_TIER_DEFINITIONS = {
    "TIER_1": {
        "label": "AUTHORITATIVE_REGULATORY",
        "examples": ["AHCA", "CMS", "Medicare Care Compare", "State inspections", "Government registry"],
        "base_confidence": 0.92,
    },
    "TIER_2": {
        "label": "INDEPENDENT_PROFESSIONAL_SCIENTIFIC",
        "examples": ["Peer-reviewed journal", "Clinical guideline", "Professional organization"],
        "base_confidence": 0.82,
    },
    "TIER_3": {
        "label": "INDEPENDENT_EXPERIENCE_OBSERVATIONAL",
        "examples": ["Google Reviews", "Yelp", "Caring.com", "SeniorAdvisor"],
        "base_confidence": 0.62,
    },
    "TIER_4": {
        "label": "PROVIDER_REPORTED",
        "examples": ["Official facility website", "Provider statement", "Provider brochure"],
        "base_confidence": 0.72,
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def source_tier(source_name: str, source_type: str) -> str:
    combined = f"{source_name or ''} {source_type or ''}".lower()

    if any(token in combined for token in ["ahca", "cms", "medicare care compare", "state inspection", "government", "regulator", "licens"]):
        return "TIER_1"
    if any(token in combined for token in ["peer", "clinical guideline", "journal", "professional", "accreditation", "academic"]):
        return "TIER_2"
    if any(token in combined for token in ["google", "yelp", "caring", "senioradvisor", "review", "facebook", "instagram", "linkedin"]):
        return "TIER_3"
    if any(token in combined for token in ["provider", "official website", "facility website", "brochure", "marketing"]):
        return "TIER_4"
    return "TIER_4"


def freshness_status_for_claim(claim_type: str, evidence_date: Optional[datetime], verified_date: Optional[datetime]) -> str:
    candidate = _to_utc(verified_date) or _to_utc(evidence_date)
    if candidate is None:
        return "UNKNOWN"

    age_days = (_now() - candidate).total_seconds() / 86400.0
    claim_type_norm = (claim_type or "").lower()

    if any(token in claim_type_norm for token in ["inspection", "licens", "regulatory", "penalty"]):
        if age_days <= 30:
            return "CURRENT"
        if age_days <= 120:
            return "AGING"
        return "STALE"

    if any(token in claim_type_norm for token in ["pricing", "staffing", "ownership"]):
        if age_days <= 45:
            return "CURRENT"
        if age_days <= 150:
            return "AGING"
        return "STALE"

    if age_days <= 90:
        return "CURRENT"
    if age_days <= 240:
        return "AGING"
    return "STALE"


def confidence_for_claim(
    *,
    source_name: str,
    source_type: str,
    claim_type: str,
    source_count: int,
    has_conflict: bool,
    freshness_status: str,
) -> float:
    tier = source_tier(source_name, source_type)
    base = SOURCE_TIER_DEFINITIONS[tier]["base_confidence"]

    claim_type_norm = (claim_type or "").lower()
    if any(token in claim_type_norm for token in ["inspection", "licens", "regulatory"]) and tier not in {"TIER_1", "TIER_2"}:
        base -= 0.18
    if any(token in claim_type_norm for token in ["experience", "sentiment", "social"]) and tier == "TIER_3":
        base += 0.06

    evidence_bonus = min(0.08, max(0, source_count - 1) * 0.02)
    conflict_penalty = 0.15 if has_conflict else 0.0
    freshness_penalty = 0.0
    if freshness_status == "AGING":
        freshness_penalty = 0.08
    elif freshness_status in {"STALE", "UNKNOWN"}:
        freshness_penalty = 0.2

    return max(0.0, min(1.0, round(base + evidence_bonus - conflict_penalty - freshness_penalty, 3)))


@dataclass
class TraceabilityMetrics:
    material_claims_audited: int
    fully_traceable: int
    partially_traceable: int
    untraceable: int
    conflicting: int
    stale: int


def _traceability_classification(obj: KnowledgeObject) -> str:
    has_source = (obj.source_name or "").strip().upper() != "UNKNOWN"
    has_reference = bool((obj.source_reference or "").strip())
    has_evidence = bool((obj.evidence_key or "").strip())
    is_verified = str(obj.verification_status or "").upper() in {"VERIFIED", "PARTIALLY_VERIFIED"}

    if has_source and has_reference and has_evidence and is_verified:
        return "TRACEABLE"
    if has_source and (has_reference or has_evidence):
        return "PARTIALLY_TRACEABLE"
    return "UNTRACEABLE"


def _material_claims_query(db: Session):
    return (
        db.query(KnowledgeObject)
        .filter(KnowledgeObject.status == "ACTIVE")
        .filter(KnowledgeObject.recommendation_eligible == 1)
    )


def audit_traceability(db: Session) -> Dict[str, object]:
    objects: List[KnowledgeObject] = _material_claims_query(db).all()

    fully = 0
    partial = 0
    untraceable = 0
    stale = 0
    conflicting = 0

    tier_distribution: Dict[str, int] = {"TIER_1": 0, "TIER_2": 0, "TIER_3": 0, "TIER_4": 0}
    critical_gaps: List[str] = []

    for obj in objects:
        classification = _traceability_classification(obj)
        if classification == "TRACEABLE":
            fully += 1
        elif classification == "PARTIALLY_TRACEABLE":
            partial += 1
        else:
            untraceable += 1

        tier = source_tier(obj.source_name or "", obj.source_type or "")
        tier_distribution[tier] = tier_distribution.get(tier, 0) + 1

        freshness = freshness_status_for_claim(obj.property_name or "", obj.published_at, obj.verified_at)
        if freshness == "STALE":
            stale += 1
        if str(obj.conflict_status or "").upper() not in {"NO_CONFLICT", "RESOLVED"}:
            conflicting += 1

        if classification != "TRACEABLE" and str(obj.verification_status or "").upper() == "VERIFIED":
            critical_gaps.append(
                f"VERIFIED material fact without full traceability: object_key={obj.object_key}, property={obj.property_name}, source={obj.source_name}"
            )

    # Detect value conflicts for same entity/property where multiple ACTIVE values exist.
    value_conflicts = (
        db.query(
            KnowledgeObject.entity_key,
            KnowledgeObject.property_name,
            func.count(func.distinct(KnowledgeObject.fact_value)).label("n"),
        )
        .filter(KnowledgeObject.status == "ACTIVE")
        .group_by(KnowledgeObject.entity_key, KnowledgeObject.property_name)
        .having(func.count(func.distinct(KnowledgeObject.fact_value)) > 1)
        .all()
    )
    conflicting += len(value_conflicts)

    return {
        "metrics": TraceabilityMetrics(
            material_claims_audited=len(objects),
            fully_traceable=fully,
            partially_traceable=partial,
            untraceable=untraceable,
            conflicting=conflicting,
            stale=stale,
        ).__dict__,
        "source_tier_distribution": tier_distribution,
        "critical_evidence_gaps": critical_gaps[:50],
        "value_conflicts_detected": [
            {
                "entity_key": row.entity_key,
                "property_name": row.property_name,
                "distinct_values": int(row.n),
            }
            for row in value_conflicts[:50]
        ],
    }


def facility_material_claim_trace(db: Session, facility_id: int) -> Dict[str, object]:
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        return {"error": "facility_not_found"}

    entity_keys = [facility.cms_id, str(facility.id), facility.name]
    claims = (
        db.query(KnowledgeObject)
        .filter(KnowledgeObject.status == "ACTIVE")
        .filter(KnowledgeObject.entity_key.in_(entity_keys))
        .order_by(KnowledgeObject.updated_at.desc())
        .all()
    )

    out = []
    for claim in claims:
        tier = source_tier(claim.source_name or "", claim.source_type or "")
        fresh = freshness_status_for_claim(claim.property_name or "", claim.published_at, claim.verified_at)
        conf = confidence_for_claim(
            source_name=claim.source_name or "",
            source_type=claim.source_type or "",
            claim_type=claim.property_name or "",
            source_count=max(1, int(claim.source_diversity or 1)),
            has_conflict=str(claim.conflict_status or "").upper() not in {"NO_CONFLICT", "RESOLVED"},
            freshness_status=fresh,
        )
        out.append(
            {
                "claim": claim.property_name,
                "value": claim.fact_value,
                "source": claim.source_name,
                "source_type": claim.source_type,
                "source_tier": tier,
                "source_reference": claim.source_reference,
                "published_at": claim.published_at.isoformat() if claim.published_at else None,
                "retrieved_at": claim.updated_at.isoformat() if claim.updated_at else None,
                "verification_status": claim.verification_status,
                "freshness_status": fresh,
                "confidence": conf,
                "conflict_status": claim.conflict_status,
                "traceability": _traceability_classification(claim),
                "what_is_unknown": "Source reference missing" if not claim.source_reference else None,
            }
        )

    return {
        "facility_id": facility_id,
        "facility_name": facility.name,
        "claims": out,
    }


def recommendation_score_trace(db: Session, recommendation_key: str) -> Dict[str, object]:
    usages = (
        db.query(RecommendationKnowledgeUsageLog)
        .filter(RecommendationKnowledgeUsageLog.recommendation_key == recommendation_key)
        .order_by(RecommendationKnowledgeUsageLog.logged_at.asc())
        .all()
    )
    audits = (
        db.query(RecommendationVerificationAudit)
        .filter(RecommendationVerificationAudit.recommendation_key == recommendation_key)
        .order_by(RecommendationVerificationAudit.created_at.desc())
        .all()
    )

    return {
        "recommendation_key": recommendation_key,
        "knowledge_usage": [
            {
                "agent_key": row.agent_key,
                "freshness_status": row.freshness_status,
                "verification_status": row.verification_status,
                "confidence": row.confidence,
                "decision": row.decision,
                "decision_reason": row.decision_reason,
                "logged_at": row.logged_at.isoformat() if row.logged_at else None,
            }
            for row in usages
        ],
        "verification_audits": [
            {
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "facts_used_json": row.facts_used_json,
                "evidence_references_json": row.evidence_references_json,
                "decision_rules_applied_json": row.decision_rules_applied_json,
                "professional_judgment_json": row.professional_judgment_json,
                "model_version": row.model_version,
            }
            for row in audits
        ],
    }
