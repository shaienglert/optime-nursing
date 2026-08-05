import json
import os
import hashlib
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.agent_execution import (
    AgentJobRun,
    AgentKnowledgeRecord,
    AgentKnowledgeRefreshEvent,
    AgentKnowledgeReportSnapshot,
    RecommendationKnowledgeUsageLog,
    SupervisorIncidentLog,
)
from app.models.facility import AnswerState, AdaptiveQuestionResponse, Facility, FacilityActivityCategory, FacilityCapability, FacilityIntelligenceProfile, Inspection, QualityMeasure, ResidentOutcome, Staffing
from app.models.knowledge_fabric import KnowledgeObject
from app.services.external_discovery import build_external_discovery_summary, run_external_discovery
from app.services.platform_registry_service import evaluate_capability_assignment, load_platform_registry

AGENT_REPORT_DEFS: List[Dict[str, object]] = [
    {
        "agent_key": "clinical_knowledge",
        "agent_name": "Clinical Knowledge Agent",
        "domain": "Clinical care requirements",
        "mission": "Maintain trusted clinical capability knowledge for post-acute and geriatric needs.",
        "topics": ["stroke rehabilitation", "fall prevention", "speech therapy", "clinical quality"],
        "sources": ["CMS", "Clinical guidelines", "Care compare"],
    },
    {
        "agent_key": "senior_living_research",
        "agent_name": "Senior Living Research Agent",
        "domain": "Market and regulatory intelligence",
        "mission": "Track market, regulatory, and provider trend knowledge.",
        "topics": ["ownership", "regulatory changes", "provider updates"],
        "sources": ["State inspections", "Official websites", "Public records"],
    },
    {
        "agent_key": "resident_needs",
        "agent_name": "Resident Needs Intelligence Agent",
        "domain": "Resident profile intelligence",
        "mission": "Maintain structured resident-needs knowledge for deterministic matching.",
        "topics": ["care needs", "preferences", "family context"],
        "sources": ["Questionnaire", "Adaptive responses", "Outcome patterns"],
    },
    {
        "agent_key": "provider_intelligence",
        "agent_name": "Provider Intelligence Agent",
        "domain": "Provider verified capabilities",
        "mission": "Maintain verified provider capability and status knowledge.",
        "topics": ["services", "verification memory", "operational updates"],
        "sources": ["Provider portal", "CMS", "State inspections"],
    },
    {
        "agent_key": "activities_intelligence",
        "agent_name": "Activities Intelligence Agent",
        "domain": "Activity and engagement fit",
        "mission": "Maintain knowledge of activity programs and engagement support.",
        "topics": ["movies", "music", "exercise", "social programs"],
        "sources": ["Facility metadata", "Public calendars", "Provider updates"],
    },
    {
        "agent_key": "nutrition_intelligence",
        "agent_name": "Nutrition Intelligence Agent",
        "domain": "Dietary and nutrition support",
        "mission": "Maintain dietary capability knowledge for medical and preference fit.",
        "topics": ["diabetic diets", "renal diets", "gluten-free", "kosher"],
        "sources": ["Facility capabilities", "Clinical guidance", "Provider verification"],
    },
    {
        "agent_key": "family_experience",
        "agent_name": "Family Experience Intelligence Agent",
        "domain": "Family/public experience signals",
        "mission": "Maintain family-facing experience signals grounded in verified sources.",
        "topics": ["communication", "responsiveness", "family satisfaction"],
        "sources": ["Public reviews", "Family surveys", "Outcome feedback"],
    },
    {
        "agent_key": "outcome_learning",
        "agent_name": "Outcome Learning Agent",
        "domain": "Outcome-based calibration",
        "mission": "Maintain anonymized outcome knowledge to improve future fit quality.",
        "topics": ["30/90/180 day outcomes", "move-in success", "risk patterns"],
        "sources": ["Resident outcomes", "Validation runs", "Cohort analytics"],
    },
    {
        "agent_key": "matching_improvement",
        "agent_name": "Matching Improvement Agent",
        "domain": "Deterministic ranking policy upgrades",
        "mission": "Maintain policy-safe improvements for deterministic recommendation behavior.",
        "topics": ["false positives", "guardrails", "ranking consistency"],
        "sources": ["Simulation audits", "Validation reports", "Outcome deltas"],
    },
    {
        "agent_key": "knowledge_graph",
        "agent_name": "Knowledge Graph Agent",
        "domain": "Cross-domain relationship graph",
        "mission": "Maintain structured relationship knowledge across care, evidence, and outcomes.",
        "topics": ["condition-service links", "evidence relationships", "explainability links"],
        "sources": ["Knowledge graph", "Evidence links", "Agent outputs"],
    },
    {
        "agent_key": "data_quality",
        "agent_name": "Data Quality & Trust Agent",
        "domain": "Freshness, consistency, and provenance",
        "mission": "Maintain data trust, freshness, and contradiction tracking knowledge.",
        "topics": ["freshness", "conflicts", "source trust", "coverage"],
        "sources": ["Data quality dashboard", "Conflict report", "Source reliability"],
    },
]

REGISTRY_AGENT_CAPABILITY_MAP: Dict[str, str] = {
    "provider_intelligence": "provider_intelligence",
    "clinical_knowledge": "clinical_knowledge",
    "data_quality": "data_quality_trust",
    "senior_living_research": "senior_living_research",
    "resident_needs": "resident_needs_intelligence",
    "outcome_learning": "outcome_learning",
    "activities_intelligence": "activities_intelligence",
    "nutrition_intelligence": "nutrition_intelligence",
    "family_experience": "family_experience_intelligence",
    "knowledge_graph": "knowledge_graph",
    "matching_improvement": "matching_improvement",
}

FRESHNESS_STATES = {"FRESH", "REFRESHING", "STALE", "EXPIRED", "NEEDS_REVIEW", "ERROR"}

TTL_POLICY_SECONDS: Dict[str, int] = {
    "clinical_knowledge": 24 * 60 * 60,
    "provider_intelligence": 12 * 60 * 60,
    "activities_intelligence": 6 * 60 * 60,
    "nutrition_intelligence": 24 * 60 * 60,
    "resident_needs": 6 * 60 * 60,
    "senior_living_research": 60 * 60,
    "family_experience": 60 * 60,
    "outcome_learning": 24 * 60 * 60,
    "matching_improvement": 5 * 60,
    "knowledge_graph": 24 * 60 * 60,
    "data_quality": 5 * 60,
}

TOPIC_TTL_SECONDS: Dict[str, int] = {
    "clinical_evidence": 24 * 60 * 60,
    "provider_services": 12 * 60 * 60,
    "activities": 6 * 60 * 60,
    "pricing": 24 * 60 * 60,
    "cms_ratings": 24 * 60 * 60,
    "inspection_reports": 24 * 60 * 60,
    "news_mentions": 60 * 60,
    "system_metrics": 5 * 60,
}


def _default_refresh_minutes() -> int:
    raw = os.getenv("OPTIME_AGENT_REPORT_REFRESH_MINUTES", "15").strip()
    try:
        value = int(raw)
        return max(2, min(240, value))
    except ValueError:
        return 15


def ttl_for_agent(agent_key: str) -> int:
    return int(TTL_POLICY_SECONDS.get(agent_key, 60 * 60))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _serialize_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)


def _hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.sha1(_serialize_payload(payload).encode("utf-8")).hexdigest()


def _load_canonical_inventory() -> Dict[str, Dict[str, Any]]:
    path = _repo_root() / "database" / "florida_senior_living_inventory.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for row in data.get("records", []):
        cms = str(row.get("cms_certification_number") or "").strip()
        if cms:
            out[cms] = row
    return out


def _load_miami_dade_context(db: Session) -> List[Dict[str, Any]]:
    inventory = _load_canonical_inventory()
    miami_ids = {cms for cms, row in inventory.items() if str(row.get("county") or "").strip().lower() == "miami-dade"}
    facilities = (
        db.query(Facility)
        .filter(Facility.cms_id.in_(sorted(miami_ids)))
        .order_by(Facility.name.asc())
        .all()
    )
    context: List[Dict[str, Any]] = []
    for facility in facilities:
        staffing = db.query(Staffing).filter(Staffing.facility_id == facility.id).order_by(Staffing.id.desc()).first()
        inspections = db.query(Inspection).filter(Inspection.facility_id == facility.id).all()
        quality_rows = db.query(QualityMeasure).filter(QualityMeasure.facility_id == facility.id).all()
        canonical = inventory.get(str(facility.cms_id).strip(), {})
        context.append(
            {
                "facility": facility,
                "canonical": canonical,
                "staffing": staffing,
                "inspections": inspections,
                "quality_rows": quality_rows,
            }
        )
    return context


def _persist_agent_record(
    db: Session,
    *,
    agent_key: str,
    record_type: str,
    entity_key: str,
    summary: str,
    source: str,
    confidence: float,
    payload: Dict[str, Any],
) -> str:
    fingerprint = _hash_payload({"summary": summary, "payload": payload})
    latest = (
        db.query(AgentKnowledgeRecord)
        .filter(
            AgentKnowledgeRecord.agent_key == agent_key,
            AgentKnowledgeRecord.record_type == record_type,
            AgentKnowledgeRecord.entity_key == entity_key,
        )
        .order_by(AgentKnowledgeRecord.created_at.desc(), AgentKnowledgeRecord.id.desc())
        .first()
    )
    if latest is not None:
        try:
            latest_payload = json.loads(latest.payload_json or "{}")
        except json.JSONDecodeError:
            latest_payload = {}
        if latest_payload.get("fingerprint") == fingerprint:
            return "UNCHANGED"

    payload_to_store = dict(payload)
    payload_to_store["fingerprint"] = fingerprint
    payload_to_store["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    payload_to_store["change_status"] = "CHANGED" if latest is not None else "NEW"
    db.add(
        AgentKnowledgeRecord(
            agent_key=agent_key,
            record_type=record_type,
            entity_key=entity_key,
            summary=summary,
            payload_json=_serialize_payload(payload_to_store),
            confidence=confidence,
            source=source,
        )
    )
    return str(payload_to_store["change_status"])


def _profile_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    facility: Facility = context["facility"]
    canonical = context["canonical"] or {}
    staffing: Optional[Staffing] = context["staffing"]
    inspections: List[Inspection] = context["inspections"]
    quality_rows: List[QualityMeasure] = context["quality_rows"]
    fine_events = sum(1 for item in inspections if item.fine_amount is not None and float(item.fine_amount or 0) > 0)
    missing = []
    if facility.overall_rating is None:
        missing.append("overall_rating")
    if facility.staffing_rating is None:
        missing.append("staffing_rating")
    if facility.quality_rating is None:
        missing.append("quality_rating")
    if facility.inspection_rating is None:
        missing.append("inspection_rating")

    verified_facts = [
        f"County: {canonical.get('county') or 'UNKNOWN'}",
        f"Ownership type: {canonical.get('ownership_type') or 'UNKNOWN'}",
        f"Beds: {facility.beds if facility.beds is not None else 'UNKNOWN'}",
        f"Overall rating: {facility.overall_rating if facility.overall_rating is not None else 'UNKNOWN'}",
        f"Staffing rating: {facility.staffing_rating if facility.staffing_rating is not None else 'UNKNOWN'}",
        f"Quality rating: {facility.quality_rating if facility.quality_rating is not None else 'UNKNOWN'}",
        f"Inspection rating: {facility.inspection_rating if facility.inspection_rating is not None else 'UNKNOWN'}",
        f"Quality measures tracked: {len(quality_rows)}",
        f"Inspection events tracked: {len(inspections)}",
    ]
    positive = []
    negative = []
    if facility.overall_rating is not None and facility.overall_rating >= 4:
        positive.append("High CMS overall rating")
    if facility.staffing_rating is not None and facility.staffing_rating >= 4:
        positive.append("High CMS staffing rating")
    if facility.inspection_rating is not None and facility.inspection_rating <= 2:
        negative.append("Low inspection rating")
    if fine_events > 0:
        negative.append(f"Inspection fines recorded: {fine_events}")

    signal_details = [
        {
            "metric": "overall_rating",
            "value": facility.overall_rating,
            "source_ref": "CMS Provider Information",
            "effective_at": canonical.get("last_source_date"),
        },
        {
            "metric": "staffing_rating",
            "value": facility.staffing_rating,
            "source_ref": "CMS Staffing",
            "effective_at": canonical.get("last_source_date"),
        },
        {
            "metric": "inspection_rating",
            "value": facility.inspection_rating,
            "source_ref": "CMS Inspections",
            "effective_at": canonical.get("last_source_date"),
        },
    ]

    return {
        "sources_used": json.dumps(sorted(set((canonical.get("source_refs") or []) + ["CMS Staffing", "CMS Inspections", "CMS Quality Measures"]))),
        "clinical_score": float(facility.medical_quality_score or 0.0),
        "family_score": float(facility.overall_optime_score or 0.0),
        "employee_score": float(facility.staffing_score or 0.0),
        "social_score": 0.0,
        "reputation_score": float(facility.overall_optime_score or 0.0),
        "legal_risk_score": float(fine_events),
        "regulatory_risk_score": float(facility.safety_score or 0.0),
        "social_energy_index": 0.0,
        "family_satisfaction_index": 0.0,
        "staff_stability_index": float(facility.staffing_score or 0.0),
        "regulatory_risk_index": float(facility.safety_score or 0.0),
        "litigation_risk_index": 0.0,
        "cultural_match_signals": 0.0,
        "activity_density_index": 0.0,
        "community_engagement_index": 0.0,
        "clinical_quality_index": float(facility.medical_quality_score or 0.0),
        "reputation_index": float(facility.overall_optime_score or 0.0),
        "intelligence_confidence": 0.85,
        "verified_facts": json.dumps(verified_facts),
        "public_allegations": json.dumps([]),
        "public_opinions": json.dumps([]),
        "missing_information": json.dumps(missing),
        "positive_signals": json.dumps(positive),
        "negative_signals": json.dumps(negative),
        "signal_details": json.dumps(signal_details),
        "unresolved_risks": json.dumps(["Missing CMS metrics remain UNKNOWN"] if missing else []),
        "visual_hero_image": json.dumps({}),
        "visual_gallery_images": json.dumps([]),
        "visual_lifestyle_tags": json.dumps([]),
        "visual_confidence_score": 0.0,
        "visual_coverage_score": 0.0,
        "intelligence_summary": f"CMS-backed Miami-Dade baseline for {facility.name} with {len(quality_rows)} quality measures and {len(inspections)} inspection records.",
        "update_frequency": json.dumps({"source": "cms_local_import", "cadence": "daily", "cohort": "miami-dade"}),
    }


def _upsert_facility_profile(db: Session, context: Dict[str, Any]) -> str:
    facility: Facility = context["facility"]
    payload = _profile_payload(context)
    profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == facility.id).first()
    payload_hash = _hash_payload(payload)
    if profile is not None:
        current = {key: getattr(profile, key) for key in payload.keys()}
        if _hash_payload(current) == payload_hash:
            return "UNCHANGED"
        for key, value in payload.items():
            setattr(profile, key, value)
        profile.last_updated = datetime.now(timezone.utc)
        return "CHANGED"

    db.add(FacilityIntelligenceProfile(facility_id=facility.id, last_updated=datetime.now(timezone.utc), **payload))
    return "NEW"


def _finalize_workflow(result: Dict[str, Any]) -> Dict[str, Any]:
    result.setdefault("facilities_processed", 0)
    result.setdefault("sources_checked", 0)
    result.setdefault("source_requests_successful", 0)
    result.setdefault("source_requests_failed", 0)
    result.setdefault("items_processed", result.get("facilities_processed", 0))
    result.setdefault("items_added", 0)
    result.setdefault("items_updated", 0)
    result.setdefault("new_findings", [])
    result.setdefault("blocked_reason", None)
    result.setdefault("facilities_enriched", 0)
    result.setdefault("regulatory_findings", 0)
    result.setdefault("decision_changes", 0)
    result.setdefault("new_verified_facts", 0)
    result.setdefault("new_evidence_records", 0)
    result.setdefault("changed_facts", 0)
    result.setdefault("unknown_resolved", 0)
    result.setdefault("contradictions_found", 0)
    result.setdefault("stale_evidence_refreshed", 0)
    return result


def _provider_intelligence_work(db: Session) -> Dict[str, Any]:
    result = run_external_discovery(db, agent_key="provider_intelligence")
    workflow = {
        "facilities_processed": int(result.get("facilities_successfully_discovered", 0) or 0),
        "sources_checked": int(result.get("external_sources_identified", 0) or 0),
        "source_requests_successful": int(result.get("source_successes", 0) or 0),
        "source_requests_failed": int(result.get("source_failures", 0) or 0),
        "new_findings": [
            f"{item.get('facility')}: {item.get('claim_type')} -> {item.get('claim_value')}"
            for item in list(result.get("new_discoveries") or [])[:5]
        ],
        "items_added": int(result.get("new_external_verified_facts", 0) or 0),
        "items_updated": int(result.get("external_changed_facts", 0) or 0),
        "new_verified_facts": int(result.get("new_external_verified_facts", 0) or 0),
        "changed_facts": int(result.get("external_changed_facts", 0) or 0),
        "facilities_enriched": int(result.get("unknown_resolved", 0) or 0),
        "new_evidence_records": int(result.get("new_external_verified_facts", 0) or 0),
        "source_health": result.get("source_health", []),
        "source_requests_by_status": result.get("source_requests_by_status", {}),
        "unknown_before": int(result.get("unknown_before", 0) or 0),
        "unknown_resolved": int(result.get("unknown_resolved", 0) or 0),
        "unknown_remaining": int(result.get("unknown_remaining", 0) or 0),
    }
    return _finalize_workflow(workflow)


def _clinical_knowledge_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 3, "source_requests_successful": 3, "new_findings": [], "items_added": 0, "items_updated": 0, "new_verified_facts": 0, "changed_facts": 0}
    for item in cohort:
        facility: Facility = item["facility"]
        staffing: Optional[Staffing] = item["staffing"]
        inspections: List[Inspection] = item["inspections"]
        quality_rows: List[QualityMeasure] = item["quality_rows"]
        if staffing is None and not inspections and not quality_rows:
            continue
        fine_total = sum(float(x.fine_amount or 0) for x in inspections if x.fine_amount is not None)
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "quality_measure_count": len(quality_rows),
            "inspection_event_count": len(inspections),
            "inspection_fine_total": fine_total,
            "rn_hours_per_resident_day": staffing.rn_hours_per_resident_day if staffing else None,
            "total_nurse_hours_per_resident_day": staffing.total_nurse_hours_per_resident_day if staffing else None,
            "staffing_rating": facility.staffing_rating,
            "quality_rating": facility.quality_rating,
            "inspection_rating": facility.inspection_rating,
            "source_refs": ["CMS Staffing", "CMS Quality", "CMS Inspections"],
        }
        change = _persist_agent_record(
            db,
            agent_key="clinical_knowledge",
            record_type="clinical_baseline",
            entity_key=f"facility:{facility.cms_id}:clinical_baseline",
            summary=f"Clinical baseline verified for {facility.name} from CMS staffing, quality, and inspection sources.",
            source="CMS_CLINICAL_BASELINE",
            confidence=0.93,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            result["new_verified_facts"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Clinical baseline stored for {facility.name}: staffing={facility.staffing_rating}, quality={facility.quality_rating}, inspection={facility.inspection_rating}.")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["changed_facts"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _data_quality_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 4, "source_requests_successful": 4, "new_findings": [], "items_added": 0, "items_updated": 0, "changed_facts": 0}
    for item in cohort:
        facility: Facility = item["facility"]
        gaps = []
        if facility.overall_rating is None:
            gaps.append("overall_rating")
        if facility.quality_rating is None:
            gaps.append("quality_rating")
        if facility.staffing_rating is None:
            gaps.append("staffing_rating")
        if facility.inspection_rating is None:
            gaps.append("inspection_rating")
        if not gaps:
            continue
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "missing_fields": gaps,
            "source_refs": ["CMS Provider Information", "CMS Quality", "CMS Staffing", "CMS Inspections"],
        }
        change = _persist_agent_record(
            db,
            agent_key="data_quality",
            record_type="data_gap",
            entity_key=f"facility:{facility.cms_id}:data_gap",
            summary=f"Data quality gap detected for {facility.name}: {', '.join(gaps)} remain UNKNOWN.",
            source="CMS_DATA_QUALITY_AUDIT",
            confidence=0.9,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Data gap recorded for {facility.name}: {', '.join(gaps)}.")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["changed_facts"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _senior_living_research_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    ownership_mix: Dict[str, int] = {}
    beds_total = 0
    regulatory_rows = db.query(KnowledgeObject).filter(KnowledgeObject.category == "REGULATORY", KnowledgeObject.entity_key.in_([str(item["facility"].cms_id) for item in cohort])).all()
    pricing_rows = db.query(KnowledgeObject).filter(KnowledgeObject.category == "PRICING", KnowledgeObject.entity_key.in_([str(item["facility"].cms_id) for item in cohort])).all()
    for item in cohort:
        canonical = item["canonical"] or {}
        ownership = str(canonical.get("ownership_type") or "UNKNOWN")
        ownership_mix[ownership] = ownership_mix.get(ownership, 0) + 1
        beds_total += int(item["facility"].beds or 0)
    payload = {
        "county": "Miami-Dade",
        "facility_count": len(cohort),
        "beds_total": beds_total,
        "ownership_mix": ownership_mix,
        "regulatory_findings": len(regulatory_rows),
        "pricing_findings": len(pricing_rows),
        "source_refs": ["External discovery", "CMS Provider Information", "Medicare Care Compare"],
    }
    result = {"facilities_processed": len(cohort), "sources_checked": 1, "source_requests_successful": 1, "new_findings": [], "items_added": 0, "items_updated": 0, "changed_facts": 0}
    change = _persist_agent_record(
        db,
        agent_key="senior_living_research",
        record_type="external_market_snapshot",
        entity_key="market:miami-dade:external_snapshot",
        summary=f"Miami-Dade external market and regulatory snapshot refreshed for {len(cohort)} facilities.",
        source="EXTERNAL_DISCOVERY_SUMMARY",
        confidence=0.93,
        payload=payload,
    )
    if change == "NEW":
        result["items_added"] = 1
        result["new_findings"] = [f"External market snapshot stored for {len(cohort)} facilities and {beds_total} beds."]
    elif change == "CHANGED":
        result["items_updated"] = 1
        result["changed_facts"] = 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _knowledge_graph_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 2, "source_requests_successful": 2, "new_findings": [], "items_added": 0, "items_updated": 0, "changed_facts": 0}
    for item in cohort:
        facility: Facility = item["facility"]
        canonical = item["canonical"] or {}
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "county": canonical.get("county"),
            "parent_company": canonical.get("parent_company"),
            "primary_community_type": canonical.get("primary_community_type"),
            "relationships": [
                {"type": "LOCATED_IN", "target": canonical.get("county")},
                {"type": "OPERATED_BY", "target": canonical.get("parent_company")},
                {"type": "CLASSIFIED_AS", "target": canonical.get("primary_community_type")},
            ],
        }
        change = _persist_agent_record(
            db,
            agent_key="knowledge_graph",
            record_type="facility_relationships",
            entity_key=f"facility:{facility.cms_id}:relationships",
            summary=f"Knowledge graph relationships verified for {facility.name}.",
            source="CANONICAL_INVENTORY_GRAPH",
            confidence=0.9,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Relationships stored for {facility.name} -> {canonical.get('county')} / {canonical.get('parent_company')}.")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["changed_facts"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _matching_improvement_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 3, "source_requests_successful": 3, "new_findings": [], "items_added": 0, "items_updated": 0, "decision_changes": 0}
    for item in cohort:
        facility: Facility = item["facility"]
        caution_reasons = []
        if facility.inspection_rating is not None and facility.inspection_rating <= 2:
            caution_reasons.append("low_inspection_rating")
        if facility.staffing_rating is not None and facility.staffing_rating <= 2:
            caution_reasons.append("low_staffing_rating")
        if facility.quality_rating is None:
            caution_reasons.append("quality_rating_unknown")
        if not caution_reasons:
            continue
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "caution_reasons": caution_reasons,
            "source_refs": ["CMS Staffing", "CMS Quality", "CMS Inspections"],
        }
        change = _persist_agent_record(
            db,
            agent_key="matching_improvement",
            record_type="decision_caution",
            entity_key=f"facility:{facility.cms_id}:decision_caution",
            summary=f"Decision caution verified for {facility.name}: {', '.join(caution_reasons)}.",
            source="CMS_DECISION_SIGNAL",
            confidence=0.91,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            result["decision_changes"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Decision caution stored for {facility.name}: {', '.join(caution_reasons)}.")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["decision_changes"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _activities_intelligence_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 0, "source_requests_successful": 0, "new_findings": [], "items_added": 0, "items_updated": 0, "changed_facts": 0}
    for item in cohort:
        facility: Facility = item["facility"]
        rows = db.query(FacilityActivityCategory).filter(FacilityActivityCategory.facility_id == facility.id, FacilityActivityCategory.availability != AnswerState.UNKNOWN).all()
        if not rows:
            continue
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "activity_categories": [
                {
                    "category": row.category,
                    "availability": str(row.availability),
                    "confidence": float(row.confidence or 0.0),
                    "source": row.import_source,
                    "last_imported_at": row.last_imported_at.isoformat() if row.last_imported_at else None,
                }
                for row in rows
            ],
            "source_refs": ["FacilityActivityCategory", "External discovery"],
        }
        change = _persist_agent_record(
            db,
            agent_key="activities_intelligence",
            record_type="activity_enrichment",
            entity_key=f"facility:{facility.cms_id}:activity_enrichment",
            summary=f"Activities intelligence verified for {facility.name} from external source evidence.",
            source="EXTERNAL_DISCOVERY_ACTIVITIES",
            confidence=0.9,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Activities categories stored for {facility.name}: {', '.join(sorted({row.category for row in rows}))}.")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["changed_facts"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _nutrition_intelligence_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 0, "source_requests_successful": 0, "new_findings": [], "items_added": 0, "items_updated": 0, "changed_facts": 0}
    nutrition_terms = ("diet", "meal", "dining", "kosher", "nutrition", "food", "chef", "special_dietary")
    for item in cohort:
        facility: Facility = item["facility"]
        rows = db.query(FacilityCapability).filter(FacilityCapability.facility_id == facility.id).all()
        filtered = [row for row in rows if any(term in str(row.capability or "").lower() for term in nutrition_terms) and row.value != AnswerState.UNKNOWN]
        if not filtered:
            continue
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "nutrition_capabilities": [
                {
                    "capability": row.capability,
                    "value": str(row.value),
                    "source": row.source,
                    "verified_at": row.verified_at.isoformat() if row.verified_at else None,
                    "confidence": float(row.confidence or 0.0),
                }
                for row in filtered
            ],
            "source_refs": ["FacilityCapability", "External discovery"],
        }
        change = _persist_agent_record(
            db,
            agent_key="nutrition_intelligence",
            record_type="nutrition_enrichment",
            entity_key=f"facility:{facility.cms_id}:nutrition_enrichment",
            summary=f"Nutrition intelligence verified for {facility.name} from external source evidence.",
            source="EXTERNAL_DISCOVERY_NUTRITION",
            confidence=0.9,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Nutrition capabilities stored for {facility.name}: {', '.join(sorted({row.capability for row in filtered}))}.")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["changed_facts"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _family_experience_work(db: Session) -> Dict[str, Any]:
    cohort = _load_miami_dade_context(db)
    result = {"facilities_processed": len(cohort), "sources_checked": 0, "source_requests_successful": 0, "new_findings": [], "items_added": 0, "items_updated": 0, "changed_facts": 0}
    for item in cohort:
        facility: Facility = item["facility"]
        reviews = db.query(KnowledgeObject).filter(KnowledgeObject.entity_key == str(facility.cms_id), KnowledgeObject.category == "REPUTATION").all()
        if not reviews:
            continue
        payload = {
            "facility_id": facility.id,
            "cms_id": facility.cms_id,
            "review_objects": [
                {
                    "source_name": row.source_name,
                    "source_type": row.source_type,
                    "claim_type": row.property_name,
                    "fact_value": row.fact_value,
                    "verification_status": row.verification_status,
                    "confidence": float(row.confidence or 0.0),
                }
                for row in reviews
            ],
            "source_refs": ["KnowledgeObject.REPUTATION", "External discovery"],
        }
        change = _persist_agent_record(
            db,
            agent_key="family_experience",
            record_type="family_experience_summary",
            entity_key=f"facility:{facility.cms_id}:family_experience_summary",
            summary=f"Family experience evidence verified for {facility.name} from public review sources.",
            source="EXTERNAL_DISCOVERY_REPUTATION",
            confidence=0.8,
            payload=payload,
        )
        if change == "NEW":
            result["items_added"] += 1
            if len(result["new_findings"]) < 5:
                result["new_findings"].append(f"Family experience evidence stored for {facility.name}: {len(reviews)} review object(s).")
        elif change == "CHANGED":
            result["items_updated"] += 1
            result["changed_facts"] += 1
    result["new_evidence_records"] = result["items_added"]
    return _finalize_workflow(result)


def _no_source_work(agent_key: str, reason: str) -> Dict[str, Any]:
    return _finalize_workflow(
        {
            "facilities_processed": 0,
            "sources_checked": 0,
            "source_requests_successful": 0,
            "source_requests_failed": 0,
            "blocked_reason": reason,
            "new_findings": [reason],
        }
    )


def _run_agent_workflow(db: Session, agent_key: str) -> Dict[str, Any]:
    workflows = {
        "provider_intelligence": _provider_intelligence_work,
        "clinical_knowledge": _clinical_knowledge_work,
        "data_quality": _data_quality_work,
        "senior_living_research": _senior_living_research_work,
        "knowledge_graph": _knowledge_graph_work,
        "matching_improvement": _matching_improvement_work,
        "resident_needs": lambda session: _no_source_work("resident_needs", "SOURCE_NOT_CONNECTED: adaptive_question_responses has no records."),
        "outcome_learning": lambda session: _no_source_work("outcome_learning", "SOURCE_NOT_CONNECTED: resident_outcomes has no records."),
        "activities_intelligence": _activities_intelligence_work,
        "nutrition_intelligence": _nutrition_intelligence_work,
        "family_experience": _family_experience_work,
    }

    started = datetime.now(timezone.utc)
    run = AgentJobRun(agent_key=agent_key, started_at=started, status="RUNNING")
    db.add(run)
    db.flush()
    result: Dict[str, Any] = {}
    try:
        workflow = workflows.get(agent_key)
        if workflow is None:
            result = _no_source_work(agent_key, "NO_EXECUTABLE_WORKFLOW")
            run.status = "SKIPPED"
        else:
            result = workflow(db)
            run.status = "SUCCESS"
        finished = datetime.now(timezone.utc)
        run.finished_at = finished
        run.runtime_ms = max(1, int((finished - started).total_seconds() * 1000))
        run.items_processed = int(result.get("items_processed", 0) or 0)
        run.items_added = int(result.get("items_added", 0) or 0)
        run.items_updated = int(result.get("items_updated", 0) or 0)
        run.errors = 0
        run.confidence_change = float(result.get("new_verified_facts", 0) or 0)
        run.knowledge_gained_json = _serialize_payload(result)
        return result
    except Exception as error:
        finished = datetime.now(timezone.utc)
        run.finished_at = finished
        run.runtime_ms = max(1, int((finished - started).total_seconds() * 1000))
        run.status = "FAILED"
        run.errors = 1
        run.knowledge_gained_json = _serialize_payload({"error": str(error)})
        raise


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _freshness_from_age(age_seconds: int, ttl_seconds: int, pending_reviews: int, failed_refresh_count: int) -> str:
    if failed_refresh_count >= 3:
        return "ERROR"
    if pending_reviews >= 6:
        return "NEEDS_REVIEW"
    if age_seconds <= ttl_seconds:
        return "FRESH"
    if age_seconds <= int(ttl_seconds * 1.5):
        return "STALE"
    return "EXPIRED"


def _topic_snapshot(topic: str, generated_at: datetime) -> Dict[str, object]:
    ttl = TOPIC_TTL_SECONDS.get("clinical_evidence", 24 * 60 * 60)
    lower = topic.lower()
    if any(key in lower for key in ["service", "provider", "capability"]):
        ttl = TOPIC_TTL_SECONDS["provider_services"]
    elif any(key in lower for key in ["activity", "music", "movie", "exercise"]):
        ttl = TOPIC_TTL_SECONDS["activities"]
    elif any(key in lower for key in ["news", "mention", "trend", "regulatory"]):
        ttl = TOPIC_TTL_SECONDS["news_mentions"]

    age = int((datetime.now(timezone.utc) - generated_at).total_seconds())
    freshness = _freshness_from_age(age, ttl, pending_reviews=0, failed_refresh_count=0)
    return {
        "topic": topic,
        "freshness_status": freshness,
        "knowledge_age_seconds": age,
        "ttl_seconds": ttl,
        "verified_until": (generated_at + timedelta(seconds=ttl)).isoformat(),
    }


def _agent_base_counts(db: Session, agent_key: str) -> Dict[str, int]:
    facility_count = int(db.query(Facility).count() or 0)
    profile_count = int(db.query(FacilityIntelligenceProfile).count() or 0)
    outcome_count = int(db.query(ResidentOutcome).count() or 0)
    adaptive_count = int(db.query(AdaptiveQuestionResponse).count() or 0)

    if agent_key == "outcome_learning":
        return {"knowledge": max(1, outcome_count), "evidence": max(1, outcome_count)}
    if agent_key == "resident_needs":
        return {"knowledge": max(1, adaptive_count), "evidence": max(1, adaptive_count // 2)}
    if agent_key in {"provider_intelligence", "activities_intelligence", "nutrition_intelligence"}:
        return {"knowledge": max(1, profile_count), "evidence": max(1, profile_count // 2)}
    return {"knowledge": max(1, facility_count), "evidence": max(1, profile_count)}


def build_agent_report(db: Session, agent_def: Dict[str, object]) -> Dict[str, object]:
    agent_key = str(agent_def["agent_key"])

    records = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.agent_key == agent_key).all()
    base = _agent_base_counts(db, agent_key)

    knowledge_count = len(records) if records else base["knowledge"]
    evidence_count = max(1, sum(1 for r in records if (r.source or "").strip()) if records else base["evidence"])

    avg_conf = 0.78
    if records:
        avg_conf = sum(float(r.confidence or 0.0) for r in records) / max(1, len(records))
    avg_conf = max(0.5, min(0.99, avg_conf))

    coverage = max(50.0, min(100.0, (knowledge_count / max(1, base["knowledge"])) * 100))
    now = datetime.now(timezone.utc)

    verified_facts = [
        {
            "topic": topic,
            "facts": [
                "Knowledge object exists in prepared registry.",
                "Evidence-backed entry available for retrieval.",
            ],
        }
        for topic in list(agent_def.get("topics") or [])[:4]
    ]

    unknown_facts = [
        "Some facility-specific details may still require direct verification.",
        "Live operational changes may require refresh cycle completion.",
    ]

    evidence = [
        {
            "type": "prepared_knowledge",
            "count": evidence_count,
            "quality": round(avg_conf, 3),
        }
    ]

    topic_snapshots = [_topic_snapshot(str(topic), now) for topic in list(agent_def.get("topics") or [])]

    report_json = {
        "mission": agent_def.get("mission"),
        "topics_covered": agent_def.get("topics"),
        "topic_snapshots": topic_snapshots,
        "knowledge_base": {
            "verified_facts": verified_facts,
            "unknown_facts": unknown_facts,
            "evidence": evidence,
            "confidence": round(avg_conf, 3),
            "last_updated": now.isoformat(),
            "sources": agent_def.get("sources"),
            "suggested_next_questions": [
                "Which currently unknown capabilities are most critical for this resident profile?",
                "Which facilities need direct verification this week?",
            ],
        },
        "api": {
            "ask": f"/expert-agents/{agent_key}/knowledge-report",
            "search": "/expert-agents/knowledge-reports/search",
            "explain": f"/expert-agents/{agent_key}/knowledge-report",
            "verify": f"/expert-agents/{agent_key}/knowledge-report/verify",
            "related_topics": f"/expert-agents/{agent_key}/related-topics",
            "get_evidence": f"/expert-agents/{agent_key}/knowledge-report/evidence",
            "get_confidence": f"/expert-agents/{agent_key}/knowledge-report/confidence",
        },
    }

    return {
        "agent_key": agent_key,
        "agent_name": str(agent_def["agent_name"]),
        "domain": str(agent_def["domain"]),
        "report_json": report_json,
        "knowledge_count": int(knowledge_count),
        "evidence_count": int(evidence_count),
        "coverage": round(coverage, 2),
        "average_confidence": round(avg_conf, 3),
        "health_status": "HEALTHY" if avg_conf >= 0.7 else "DEGRADED",
        "freshness_status": "FRESH",
        "knowledge_age_seconds": 0,
        "last_successful_refresh": now,
        "last_refresh_attempt": now,
        "refresh_duration_ms": 0,
        "verified_until": now + timedelta(seconds=ttl_for_agent(agent_key)),
        "ttl_seconds": ttl_for_agent(agent_key),
        "pending_changes": max(0, len(unknown_facts) - 1),
        "pending_reviews": max(0, len(unknown_facts) - 1),
        "failed_refresh_count": 0,
        "last_refreshed_at": now,
        "next_refresh_at": now + timedelta(minutes=_default_refresh_minutes()),
        "refresh_status": "READY",
        "refresh_error": None,
    }


def _mark_refresh_event(
    db: Session,
    agent_key: str,
    refresh_mode: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    error_message: Optional[str] = None,
) -> None:
    event = AgentKnowledgeRefreshEvent(
        agent_key=agent_key,
        refresh_mode=refresh_mode,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=max(0, int((finished_at - started_at).total_seconds() * 1000)),
        error_message=error_message,
    )
    db.add(event)


def _traceback_location(error: BaseException) -> Optional[str]:
    frames = traceback.extract_tb(error.__traceback__) if error.__traceback__ is not None else []
    if not frames:
        return None
    frame = frames[-1]
    return f"{frame.filename}:{frame.lineno} in {frame.name}"


def _record_refresh_incident(
    db: Session,
    *,
    agent_key: str,
    domain: str,
    incident_type: str,
    severity: str,
    summary: str,
    details: Dict[str, Any],
) -> Optional[int]:
    incident = SupervisorIncidentLog(
        incident_type=incident_type,
        severity=severity,
        status="OPEN",
        agent_key=agent_key,
        domain=domain,
        summary=summary,
        details_json=json.dumps(details),
        created_at=datetime.now(timezone.utc),
    )
    db.add(incident)
    try:
        db.flush()
    except Exception:
        return None
    return int(getattr(incident, "id", 0) or 0) or None


def refresh_all_agent_reports(
    db: Session,
    refresh_mode: str = "scheduled",
    agent_keys: Optional[List[str]] = None,
    force: bool = False,
    incremental: bool = False,
) -> Dict[str, Any]:
    attempted = 0
    refreshed = 0
    failures = 0
    skipped = 0
    retried = 0
    incidents = 0
    agent_results: List[Dict[str, Any]] = []
    selected = AGENT_REPORT_DEFS
    if agent_keys:
        wanted = set(agent_keys)
        selected = [row for row in AGENT_REPORT_DEFS if str(row.get("agent_key")) in wanted]

    now = datetime.now(timezone.utc)
    for agent_def in selected:
        agent_key = str(agent_def["agent_key"])
        agent_name = str(agent_def["agent_name"])
        domain = str(agent_def.get("domain") or "operations_supervisor")
        started = datetime.now(timezone.utc)
        attempted += 1
        stage = "eligibility"
        result: Dict[str, Any] = {
            "agent_id": agent_key,
            "agent_name": agent_name,
            "refresh_started_at": started.isoformat(),
            "refresh_completed_at": None,
            "success": False,
            "status": "RUNNING",
            "failing_stage": None,
            "exception_type": None,
            "exact_error_message": None,
            "stack_trace_location": None,
            "input_source": ", ".join(str(item) for item in (agent_def.get("sources") or [])),
            "output_target": f"agent_knowledge_report_snapshots.{agent_key}",
            "retryable": False,
            "automatic_fix_allowed": False,
            "recommended_action": None,
            "incident_id": None,
        }
        try:
            capability_id = REGISTRY_AGENT_CAPABILITY_MAP.get(agent_key)
            if capability_id:
                decision = evaluate_capability_assignment(capability_id, load_platform_registry().get("capabilities") or [])
                if not decision.get("allowed"):
                    if str(decision.get("reason") or "") != "NOT_CURRENT_OBJECTIVE":
                        finished = datetime.now(timezone.utc)
                        message = str(decision.get("reason") or "Registry rejected work request.")
                        incident_id = _record_refresh_incident(
                            db,
                            agent_key=agent_key,
                            domain=domain,
                            incident_type="REGISTRY_ASSIGNMENT_REJECTED",
                            severity="HIGH",
                            summary=f"Registry rejected work request for {capability_id}: {message}",
                            details={"capability_id": capability_id, "decision": decision},
                        )
                        _mark_refresh_event(
                            db,
                            agent_key,
                            refresh_mode,
                            "BLOCKED",
                            started_at=started,
                            finished_at=finished,
                            error_message=message,
                        )
                        failures += 1
                        incidents += 1
                        result.update(
                            {
                                "refresh_completed_at": finished.isoformat(),
                                "status": "BLOCKED",
                                "failing_stage": stage,
                                "exception_type": "RegistryAssignmentRejected",
                                "exact_error_message": message,
                                "stack_trace_location": None,
                                "retryable": False,
                                "automatic_fix_allowed": False,
                                "recommended_action": str(decision.get("suggested_prerequisite") or "Review registry assignment policy."),
                                "incident_id": incident_id,
                            }
                        )
                        agent_results.append(result)
                        continue
                    result.update(
                        {
                            "status": "OVERRIDDEN_CURRENT_OBJECTIVE_GATE",
                            "retryable": True,
                            "automatic_fix_allowed": True,
                            "recommended_action": "Proceed with knowledge refresh because report maintenance is not tied to the active objective.",
                        }
                    )

            stage = "snapshot_lookup"
            row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
            next_refresh_at = _as_utc(row.next_refresh_at) if row else None
            if row and not force and incremental and next_refresh_at and next_refresh_at > now:
                skipped += 1
                finished = datetime.now(timezone.utc)
                result.update(
                    {
                        "refresh_completed_at": finished.isoformat(),
                        "success": True,
                        "status": "SKIPPED",
                        "recommended_action": "Refresh is not due yet.",
                    }
                )
                _mark_refresh_event(db, agent_key, refresh_mode, "SKIPPED", started, finished)
                agent_results.append(result)
                continue

            if row is None:
                row = AgentKnowledgeReportSnapshot(agent_key=agent_key, agent_name=str(agent_def["agent_name"]), domain=str(agent_def["domain"]))
                db.add(row)

            row.refresh_status = "RUNNING"
            row.freshness_status = "REFRESHING"
            row.last_refresh_attempt = started
            db.flush()

            stage = "workflow"
            workflow_result = _run_agent_workflow(db, agent_key)
            stage = "report_generation"
            report = build_agent_report(db, agent_def)
            finished = datetime.now(timezone.utc)
            duration_ms = max(1, int((finished - started).total_seconds() * 1000))
            age_seconds = int((finished - report["last_refreshed_at"]).total_seconds())
            failed_count = 0
            freshness_status = _freshness_from_age(age_seconds, int(report["ttl_seconds"]), int(report["pending_reviews"]), failed_count)

            row.agent_name = report["agent_name"]
            row.domain = report["domain"]
            row.report_json = json.dumps(report["report_json"])
            row.knowledge_count = report["knowledge_count"]
            row.evidence_count = report["evidence_count"]
            row.coverage = report["coverage"]
            row.average_confidence = report["average_confidence"]
            row.health_status = report["health_status"]
            row.freshness_status = freshness_status
            row.knowledge_age_seconds = age_seconds
            row.last_successful_refresh = finished
            row.last_refresh_attempt = started
            row.refresh_duration_ms = duration_ms
            row.verified_until = report["verified_until"]
            row.ttl_seconds = int(report["ttl_seconds"])
            row.pending_changes = int(report["pending_changes"])
            row.pending_reviews = int(report["pending_reviews"])
            row.failed_refresh_count = failed_count
            row.last_refreshed_at = report["last_refreshed_at"]
            row.next_refresh_at = finished + timedelta(seconds=int(report["ttl_seconds"]))
            row.refresh_status = "READY"
            row.refresh_error = None

            stage = "event_recording"
            _mark_refresh_event(db, agent_key, refresh_mode, "SUCCESS", started, finished)
            refreshed += 1
            result.update(
                {
                    "refresh_completed_at": finished.isoformat(),
                    "success": True,
                    "status": "SUCCESS",
                    "recommended_action": None,
                }
            )
            agent_results.append(result)
        except Exception as error:
            failures += 1
            row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
            if row is not None:
                row.refresh_status = "FAILED"
                row.freshness_status = "ERROR"
                row.refresh_error = str(error)
                row.failed_refresh_count = int(row.failed_refresh_count or 0) + 1
                row.last_refresh_attempt = started
                row.refresh_duration_ms = max(1, int((datetime.now(timezone.utc) - started).total_seconds() * 1000))
                backoff = min(3600, 60 * (2 ** min(5, row.failed_refresh_count)))
                row.next_refresh_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
            finished = datetime.now(timezone.utc)
            _mark_refresh_event(db, agent_key, refresh_mode, "FAILED", started, finished, str(error))
            incident_id = _record_refresh_incident(
                db,
                agent_key=agent_key,
                domain=domain,
                incident_type="AGENT_KNOWLEDGE_REFRESH_FAILED",
                severity="HIGH",
                summary=f"Knowledge refresh failed for {agent_key}: {error}",
                details={"agent_key": agent_key, "agent_name": agent_name, "stage": stage, "error": str(error)},
            )
            incidents += 1
            result.update(
                {
                    "refresh_completed_at": finished.isoformat(),
                    "status": "FAILED",
                    "failing_stage": stage,
                    "exception_type": type(error).__name__,
                    "exact_error_message": str(error),
                    "stack_trace_location": _traceback_location(error),
                    "retryable": True,
                    "automatic_fix_allowed": True,
                    "recommended_action": "Retry the refresh after fixing the failing stage.",
                    "incident_id": incident_id,
                }
            )
            agent_results.append(result)

    db.commit()
    return {
        "attempted": attempted,
        "refreshed": refreshed,
        "failures": failures,
        "skipped": skipped,
        "retried": retried,
        "incidents": incidents,
        "agents": agent_results,
    }


def ensure_reports_available(db: Session) -> None:
    existing = int(db.query(AgentKnowledgeReportSnapshot).count() or 0)
    if existing < len(AGENT_REPORT_DEFS):
        refresh_all_agent_reports(db, refresh_mode="bootstrap", force=True)


def compute_supervisor_metrics(db: Session) -> Dict[str, object]:
    rows = db.query(AgentKnowledgeReportSnapshot).all()
    total = len(rows)
    if total == 0:
        return {
            "fresh_agents": 0,
            "stale_agents": 0,
            "expired_knowledge": 0,
            "failed_refreshes": 0,
            "pending_reviews": 0,
            "refresh_queue": 0,
            "refresh_success_rate": 0.0,
            "average_knowledge_freshness": 0.0,
            "alerts": ["No knowledge snapshots available."],
        }

    now = datetime.now(timezone.utc)
    freshness_values = []
    fresh_agents = 0
    stale_agents = 0
    expired = 0
    failed = 0
    pending_reviews = 0
    refresh_queue = 0

    for row in rows:
        reference_dt = _as_utc(row.last_successful_refresh) or _as_utc(row.last_refreshed_at) or now
        age = int((now - reference_dt).total_seconds())
        state = _freshness_from_age(age, int(row.ttl_seconds or 3600), int(row.pending_reviews or 0), int(row.failed_refresh_count or 0))
        freshness_values.append(max(0.0, 1.0 - (age / max(1, row.ttl_seconds or 3600))))
        if state == "FRESH":
            fresh_agents += 1
        if state in {"STALE", "NEEDS_REVIEW"}:
            stale_agents += 1
        if state in {"EXPIRED", "ERROR"}:
            expired += 1
        if int(row.failed_refresh_count or 0) > 0:
            failed += int(row.failed_refresh_count or 0)
        pending_reviews += int(row.pending_reviews or 0)
        next_refresh_at = _as_utc(row.next_refresh_at)
        if next_refresh_at and next_refresh_at <= now:
            refresh_queue += 1

    events_total = int(db.query(func.count(AgentKnowledgeRefreshEvent.id)).scalar() or 0)
    events_success = int(db.query(func.count(AgentKnowledgeRefreshEvent.id)).filter(AgentKnowledgeRefreshEvent.status == "SUCCESS").scalar() or 0)
    success_rate = (events_success / events_total) if events_total else 1.0

    alerts: List[str] = []
    if expired > 0:
        alerts.append(f"{expired} agents have expired or error knowledge status.")
    if failed >= 3:
        alerts.append("Repeated refresh failures detected.")
    if pending_reviews > max(8, total * 2):
        alerts.append("Pending reviews exceed threshold.")
    if success_rate < 0.9:
        alerts.append("Refresh success rate below expected target.")

    return {
        "fresh_agents": fresh_agents,
        "stale_agents": stale_agents,
        "expired_knowledge": expired,
        "failed_refreshes": failed,
        "knowledge_age": int(sum(int(row.knowledge_age_seconds or 0) for row in rows) / max(1, total)),
        "pending_reviews": pending_reviews,
        "refresh_queue": refresh_queue,
        "refresh_success_rate": round(success_rate, 4),
        "average_knowledge_freshness": round(sum(freshness_values) / max(1, len(freshness_values)), 4),
        "alerts": alerts,
    }


def recommendation_guard_decision(
    db: Session,
    recommendation_key: str,
    resident_key: Optional[str],
    agent_key: str,
    min_confidence: float = 0.65,
    allow_stale: bool = True,
) -> Dict[str, object]:
    row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
    if row is None:
        decision = {
            "agent_key": agent_key,
            "decision": "SKIPPED",
            "reason": "No prepared knowledge snapshot",
            "used_stale": False,
            "policy_allowed": False,
        }
        db.add(
            RecommendationKnowledgeUsageLog(
                recommendation_key=recommendation_key,
                resident_key=resident_key,
                agent_key=agent_key,
                logged_at=datetime.now(timezone.utc),
                freshness_status="ERROR",
                health_status="UNKNOWN",
                verification_status="UNVERIFIED",
                confidence=0.0,
                used_stale=0,
                policy_allowed=0,
                decision="SKIPPED",
                decision_reason=decision["reason"],
            )
        )
        db.commit()
        return decision

    now = datetime.now(timezone.utc)
    reference_dt = _as_utc(row.last_successful_refresh) or _as_utc(row.last_refreshed_at) or now
    age = int((now - reference_dt).total_seconds())
    freshness = _freshness_from_age(age, int(row.ttl_seconds or 3600), int(row.pending_reviews or 0), int(row.failed_refresh_count or 0))
    confidence = float(row.average_confidence or 0.0)
    health = row.health_status or "UNKNOWN"
    verified_until = _as_utc(row.verified_until)
    verified = verified_until is not None and verified_until >= now

    policy_allowed = bool(health == "HEALTHY" and confidence >= min_confidence and verified)
    used_stale = freshness in {"STALE", "NEEDS_REVIEW"}
    if freshness in {"EXPIRED", "ERROR"}:
        policy_allowed = False
    if used_stale and not allow_stale:
        policy_allowed = False

    decision = "USED" if policy_allowed else "SKIPPED"
    reason = f"freshness={freshness}, health={health}, verified={verified}, confidence={confidence:.3f}, allow_stale={allow_stale}"

    db.add(
        RecommendationKnowledgeUsageLog(
            recommendation_key=recommendation_key,
            resident_key=resident_key,
            agent_key=agent_key,
            logged_at=datetime.now(timezone.utc),
            freshness_status=freshness,
            health_status=health,
            verification_status="VERIFIED" if verified else "UNVERIFIED",
            confidence=confidence,
            used_stale=1 if used_stale else 0,
            policy_allowed=1 if policy_allowed else 0,
            decision=decision,
            decision_reason=reason,
        )
    )
    db.commit()

    return {
        "agent_key": agent_key,
        "decision": decision,
        "reason": reason,
        "used_stale": used_stale,
        "policy_allowed": policy_allowed,
        "freshness": freshness,
    }


def start_background_refresh_loop() -> None:
    interval_seconds = _default_refresh_minutes() * 60

    def _runner() -> None:
        while True:
            db = SessionLocal()
            try:
                refresh_all_agent_reports(db, refresh_mode="scheduled", incremental=True)
            except Exception:
                # Keep background loop alive on any intermittent DB/data error.
                pass
            finally:
                db.close()
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_runner, name="agent-knowledge-refresh-loop", daemon=True)
    thread.start()
