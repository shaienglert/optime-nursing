import os
import json
import hashlib
import logging
import time
from datetime import datetime
from statistics import mean
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.facility import AdaptiveQuestionResponse, Facility, FacilityIntelligenceProfile, HumanIntelligenceScore, Inspection, QualityMeasure, ResidentOutcome, Staffing
import app.models.clinical_evidence
import app.models.agent_execution
import app.models.external_discovery
import app.models.knowledge_fabric
from app.models.agent_execution import (
    AgentKnowledgeRecord,
    AgentKnowledgeRefreshEvent,
    AgentKnowledgeReportSnapshot,
    RecommendationKnowledgeUsageLog,
    AgentVersionSnapshot,
    AgentWorker,
    RecommendationAgentVersionTrace,
)
from app.services.agent_knowledge_reports import (
    AGENT_REPORT_DEFS,
    FRESHNESS_STATES,
    TTL_POLICY_SECONDS,
    compute_supervisor_metrics,
    ensure_reports_available,
    recommendation_guard_decision,
    refresh_all_agent_reports,
    start_background_refresh_loop,
)
from app.services.chief_ai_supervisor import recent_incidents, run_supervisor_cycle, stale_usage_summary
from app.services.cms_inspection_import import import_inspection_data
from app.services.cms_provider_import import import_provider_information
from app.services.cms_quality_import import import_quality_data
from app.services.cms_staffing_import import import_staffing_data
from app.services.activity_intelligence import ALLOWED_ACTIVITY_CATEGORIES, get_public_activity_categories, import_activity_categories
from app.services.facility_memory_persistence import apply_provider_verification_answers, facility_memory_overlay
from app.services.schema_migrations import ensure_facility_intelligence_profile_schema, ensure_provider_identity_schema
from app.services.provider_identity import (
    apply_facility_field_update,
    complete_email_verification,
    invite_staff_member,
    request_role_change,
    revert_audit_change,
    role_can_edit_category,
    run_annual_reverification,
    start_email_verification,
    validate_license_ownership,
)
from app.services.intelligence_agent import UPDATE_FREQUENCY, run_intelligence_collection
from app.services.evidence_source_integrity import (
    audit_traceability,
    facility_material_claim_trace,
    recommendation_score_trace,
)
from app.services.executive_report_service import (
    compare_latest_vs_previous,
    get_executive_report_history,
    get_latest_executive_report,
    get_executive_report_payload,
    start_executive_report_scheduler,
)
from app.services.email_service import send_startup_test_email_once
from app.services.cms_service import (
    CMS_PROVIDER_DATASET_ID,
    clean_state,
    clip_0_100,
    download_dataset,
    env_int,
    inverse_count,
    invert_percent,
    iter_csv_rows,
    normalize_hours,
    stars_to_score,
    to_float,
)
from app.services.facility_parameter_service import (
    compare_facility_parameter_tables,
    get_canonical_facility_index,
    get_facility_parameter_table,
    get_parameter_registry_payload,
    get_personalized_parameter_order,
)
from app.services.facility_media_registry import build_visual_media_payload, get_facility_media_record
from app.services.live_facility_profile_service import get_live_facility_profile
from app.services.patient_decision_engine import (
    build_patient_comparison_context,
    build_patient_needs_profile,
    run_patient_decision_engine,
)
from app.services.unified_patient_case_service import (
    build_legacy_patient_profile_adapter,
    get_patient_case,
    get_patient_case_history,
    get_patient_case_missing,
    get_patient_case_summary,
    migrate_legacy_patient_profiles,
    resolve_case_for_decision,
    run_unified_patient_case_validation,
    upsert_from_chat,
    upsert_from_free_text,
    upsert_from_generic_update,
    upsert_from_questionnaire,
)

app = FastAPI(
    title="OPTIME Nursing API",
    version="0.3.0",
    description="OPTIME Phase 1 CMS ingestion pipeline for Florida nursing homes",
)

logger = logging.getLogger("optime.api")

REQUIRED_FRONTEND_ORIGINS = ["https://optime-nursing.vercel.app"]
DEVELOPMENT_FRONTEND_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

def _get_dev_network_origins() -> list[str]:
    candidates = [
        os.getenv("DEV_NETWORK_ORIGIN", ""),
        f"http://{os.getenv('HOSTNAME', '')}:3000",
    ]
    return [origin for origin in (_normalize_origin(candidate) for candidate in candidates) if origin]

def _normalize_origin(origin: str) -> str:
    value = origin.strip().strip('"').strip("'")
    return value.rstrip("/")


def _parse_frontend_origins(raw_origins: str) -> list[str]:
    normalized: list[str] = []
    for candidate in raw_origins.split(","):
        value = _normalize_origin(candidate)
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _build_allowed_origins(raw_origins: str) -> list[str]:
    configured = _parse_frontend_origins(raw_origins)
    merged: list[str] = []

    for candidate in [*configured, *REQUIRED_FRONTEND_ORIGINS, *DEVELOPMENT_FRONTEND_ORIGINS, *_get_dev_network_origins()]:
        value = _normalize_origin(candidate)
        if value and value not in merged:
            merged.append(value)

    return merged


frontend_origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = _build_allowed_origins(frontend_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FacilityListOut(BaseModel):
    id: int
    cms_id: str
    name: str
    city: str
    state: str
    address: str
    zip_code: str
    phone: Optional[str] = None
    overall_rating: Optional[int] = None
    staffing_rating: Optional[int] = None
    quality_rating: Optional[int] = None
    inspection_rating: Optional[int] = None
    beds: Optional[int] = None
    medical_quality_score: Optional[float] = None
    staffing_score: Optional[float] = None
    safety_score: Optional[float] = None
    overall_optime_score: Optional[float] = None
    confidence_level: Optional[str] = None
    intelligence_confidence: Optional[float] = None
    intelligence_sources_used: List[str] = Field(default_factory=list)
    intelligence_positive_signals: List[str] = Field(default_factory=list)
    intelligence_negative_signals: List[str] = Field(default_factory=list)
    intelligence_signal_details: List[Dict[str, object]] = Field(default_factory=list)
    family_satisfaction_index: Optional[float] = None
    staff_stability_index: Optional[float] = None
    regulatory_risk_index: Optional[float] = None
    litigation_risk_index: Optional[float] = None
    social_energy_index: Optional[float] = None
    community_engagement_index: Optional[float] = None
    reputation_index: Optional[float] = None
    cultural_match_signals: Optional[float] = None
    visual_hero_image: Dict[str, object] = Field(default_factory=dict)
    visual_gallery_images: List[Dict[str, object]] = Field(default_factory=list)
    visual_lifestyle_tags: List[Dict[str, object]] = Field(default_factory=list)
    visual_confidence_score: Optional[float] = None
    visual_coverage_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ScoreBreakdownOut(BaseModel):
    medical_quality_score: float
    staffing_score: float
    safety_score: float
    overall_optime_score: float
    medical_components: Dict[str, float]
    staffing_components: Dict[str, float]
    safety_components: Dict[str, float]


class FacilityDetailsOut(BaseModel):
    id: int
    cms_id: str
    canonical_facility_id: Optional[str] = None
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str] = None
    overall_rating: Optional[int] = None
    staffing_rating: Optional[int] = None
    quality_rating: Optional[int] = None
    inspection_rating: Optional[int] = None
    beds: Optional[int] = None
    confidence_level: Optional[str] = None
    visual_hero_image: Dict[str, object] = Field(default_factory=dict)
    visual_gallery_images: List[Dict[str, object]] = Field(default_factory=list)
    visual_lifestyle_tags: List[Dict[str, object]] = Field(default_factory=list)
    visual_confidence_score: Optional[float] = None
    visual_coverage_score: Optional[float] = None
    score_breakdown: ScoreBreakdownOut


class ParameterTableRowOut(BaseModel):
    parameter_id: str
    category: str
    parameter: str
    status_value: Any
    raw_value: Any = None
    detail_scope: str
    scope_name: Optional[str] = None
    source: str
    last_verified: Optional[str] = None
    evidence_count: int
    evidence_records: List[Dict[str, Any]] = Field(default_factory=list)


class FacilityParameterTableOut(BaseModel):
    canonical_facility_id: str
    facility_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    zip: Optional[str] = None
    canonical_type: Optional[str] = None
    role_classification: Optional[str] = None
    match_status: Optional[str] = None
    need_tags: List[str] = Field(default_factory=list)
    priority_parameter_ids: List[str] = Field(default_factory=list)
    profile_key: Optional[str] = None
    rows: List[ParameterTableRowOut]


class FacilityParameterComparisonIn(BaseModel):
    canonical_facility_ids: List[str]
    need_tags: List[str] = Field(default_factory=list)
    priority_parameter_ids: List[str] = Field(default_factory=list)
    profile_key: Optional[str] = None


class FacilityParameterComparisonOut(BaseModel):
    parameter_ids: List[str]
    need_tags: List[str] = Field(default_factory=list)
    priority_parameter_ids: List[str] = Field(default_factory=list)
    profile_key: Optional[str] = None
    facilities: List[FacilityParameterTableOut]


class PersonalizedParameterOrderIn(BaseModel):
    need_tags: List[str] = Field(default_factory=list)
    priority_parameter_ids: List[str] = Field(default_factory=list)
    profile_key: Optional[str] = None


class PersonalizedParameterOrderRowOut(BaseModel):
    parameter_id: str
    family: str
    display_name: str
    applicable_scope: str
    sort_score: float


class PersonalizedParameterOrderOut(BaseModel):
    generated_at_utc: Optional[str] = None
    profile_key: Optional[str] = None
    need_tags: List[str] = Field(default_factory=list)
    priority_parameter_ids: List[str] = Field(default_factory=list)
    ordered_parameters: List[PersonalizedParameterOrderRowOut]


class ParameterRegistryOut(BaseModel):
    generated_at_utc: Optional[str] = None
    record_count: int
    missing_registry_definitions: List[str] = Field(default_factory=list)
    records: List[Dict[str, Any]]


class PatientDecisionEngineRequestIn(BaseModel):
    patient_case_id: Optional[int] = None
    questionnaire_state: Dict[str, Any]
    natural_language_query: Optional[str] = ""
    limit: int = 50


class PatientNeedsProfileRequestIn(BaseModel):
    patient_case_id: Optional[int] = None
    questionnaire_state: Dict[str, Any]
    natural_language_query: Optional[str] = ""


class PatientComparisonContextRequestIn(BaseModel):
    canonical_facility_ids: List[str]
    patient_needs_profile: Dict[str, Any]


class PatientDecisionEngineOut(BaseModel):
    patient_needs_profile: Dict[str, Any]
    results: List[Dict[str, Any]]
    result_count: int
    total_candidates_scored: int
    availability_policy: str


class PatientNeedsProfileOut(BaseModel):
    generated_from: Dict[str, Any]
    needs: List[Dict[str, Any]]
    need_tags: List[str]
    priority_parameter_ids: List[str]
    profile_key: Optional[str] = None
    location_city: Optional[str] = None
    natural_language_mapping: Dict[str, Any]


class PatientComparisonContextOut(BaseModel):
    required_needs: List[Dict[str, Any]]
    high_priority_needs: List[Dict[str, Any]]
    preferences: List[Dict[str, Any]]
    comparison_parameter_ids: List[str]
    facilities: List[Dict[str, Any]]


class CaseUnderstandingRequestIn(BaseModel):
    patient_case_id: Optional[int] = None
    case_text: str


class CaseRefinementRequestIn(BaseModel):
    profile_id: Optional[int] = None
    patient_case_id: Optional[int] = None
    refinement_text: str


class PatientCaseQuestionnaireIn(BaseModel):
    patient_case_id: Optional[int] = None
    questionnaire_state: Dict[str, Any]
    source_name: Optional[str] = "homepage_questionnaire"
    reason: Optional[str] = "questionnaire_update"


class PatientCaseFreeTextIn(BaseModel):
    patient_case_id: Optional[int] = None
    case_text: str
    source_name: Optional[str] = "natural_language"
    reason: Optional[str] = "free_text_update"


class PatientCaseChatIn(BaseModel):
    patient_case_id: Optional[int] = None
    message: str
    source_name: Optional[str] = "ai_chat"
    reason: Optional[str] = "chat_update"


class PatientCaseGenericUpdateIn(BaseModel):
    patient_case_id: int
    updates: Dict[str, Any]
    source_type: str = "FAMILY_UPDATE"
    source_name: str = "manual_update"
    reason: str = "manual_update"


class PatientCaseOut(BaseModel):
    id: int
    case_key: str
    display_label: str
    current_version: int
    profile_confidence: float
    canonical_profile: Dict[str, Any]
    questionnaire_state: Dict[str, Any]
    summary: str
    readiness: Dict[str, Any]
    missing: List[Dict[str, Any]] = Field(default_factory=list)
    follow_up_questions: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: Dict[str, Any] = Field(default_factory=dict)
    source_matrix: Dict[str, Any] = Field(default_factory=dict)
    decision_handoff: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


class PatientCaseHistoryOut(BaseModel):
    id: int
    case_key: str
    current_version: int
    history: List[Dict[str, Any]] = Field(default_factory=list)


class PatientCaseMissingOut(BaseModel):
    id: int
    missing: List[Dict[str, Any]] = Field(default_factory=list)
    follow_up_questions: List[Dict[str, Any]] = Field(default_factory=list)


class PatientCaseSummaryOut(BaseModel):
    id: int
    summary: str
    readiness: Dict[str, Any]
    profile_confidence: float


class PatientProfileVersionOut(BaseModel):
    version_number: int
    operation: str
    input_case_text: str
    profile_confidence: float
    structured_profile: Dict[str, Any]
    missing_critical_fields: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    ambiguity_notes: List[Dict[str, Any]] = Field(default_factory=list)
    case_summary: str
    questionnaire_state: Dict[str, Any]
    decision_handoff: Dict[str, Any]
    created_at: Optional[str] = None


class PatientProfileOut(BaseModel):
    id: int
    case_key: str
    current_version: int
    profile_confidence: float
    original_case_text: str
    latest_case_text: str
    structured_profile: Dict[str, Any]
    missing_critical_fields: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    ambiguity_notes: List[Dict[str, Any]] = Field(default_factory=list)
    case_summary: str
    questionnaire_state: Dict[str, Any]
    decision_handoff: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    versions: List[PatientProfileVersionOut] = Field(default_factory=list)


class CaseUnderstandingValidationOut(BaseModel):
    generated_at: str
    workload: Dict[str, int]
    results: Dict[str, Any]


class ImportSummaryOut(BaseModel):
    facilities_imported: int
    missing_records: int
    failed_mappings: int
    score_distributions: Dict[str, Dict[str, float]]


class HumanIntelligenceIn(BaseModel):
    resident_key: str
    relationship: Optional[str] = None
    age_group: Optional[str] = None
    social_profile_score: float
    family_support_score: float
    cultural_match_score: float
    loneliness_risk_score: float
    transition_risk_score: float
    future_care_score: float
    social_fit_score: Optional[float] = None
    family_fit_score: Optional[float] = None
    language_match_score: Optional[float] = None
    religious_fit_score: Optional[float] = None
    language_fit_score: Optional[float] = None
    cultural_fit_score: Optional[float] = None
    food_fit_score: Optional[float] = None
    family_engagement_score: Optional[float] = None
    community_style_score: Optional[float] = None
    independence_fit_score: Optional[float] = None
    transition_success_probability: Optional[float] = None
    metadata_json: Optional[str] = None


class HumanIntelligenceOut(HumanIntelligenceIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ResidentOutcomeIn(BaseModel):
    resident_key: str
    human_intelligence_score_id: Optional[int] = None
    facility_id: Optional[int] = None
    successful_adjustment: bool
    loneliness_event: bool
    relocated_within_24m: bool
    notes: Optional[str] = None


class AdaptiveQuestionResponseIn(BaseModel):
    resident_key: str
    question_key: str
    answer: str
    signal_type: str
    signal_json: Optional[str] = None
    weights_json: Optional[str] = None
    impact_explanation: str
    info_gain_score: float = 0.0


class AdaptiveQuestionResponseOut(AdaptiveQuestionResponseIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ResidentOutcomeOut(BaseModel):
    id: int
    resident_key: str
    human_intelligence_score_id: Optional[int] = None
    facility_id: Optional[int] = None
    successful_adjustment: bool
    loneliness_event: bool
    relocated_within_24m: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ValidationFeedbackOut(BaseModel):
    outcomes_count: int
    adjustment_success_rate: float
    loneliness_event_rate: float
    relocation_rate_24m: float
    average_scores_for_successful_adjustment: Dict[str, float]
    average_scores_for_unsuccessful_adjustment: Dict[str, float]


class ActivityImportIn(BaseModel):
    source_type: str
    content: str
    updated_by_user_id: Optional[int] = None


class ActivityCategoryOut(BaseModel):
    category: str
    availability: str
    confidence: float


class ActivityImportOut(BaseModel):
    facility_id: int
    source_type: str
    imported_at: str
    categories: List[ActivityCategoryOut]
    privacy_policy: str


class ProviderAnswerIn(BaseModel):
    capability_key: str
    value: str
    source: str = "PROVIDER_PORTAL"


class ProviderPersistIn(BaseModel):
    answers: List[ProviderAnswerIn]
    verified_by_user_id: Optional[int] = None
    verification_method: str = "provider_portal"
    request_subject: Optional[str] = None
    request_body: Optional[str] = None


class ProviderPersistOut(BaseModel):
    facility_id: int
    request_id: int
    persisted_answers: int
    conflict_records: int


class MemoryCapabilityOut(BaseModel):
    capability_key: str
    value: str
    source: str
    verified_at: str
    expires_at: str
    expired: bool
    confidence: float
    verification_count: int
    conflict_count: int
    status: str


class FacilityMemoryOut(BaseModel):
    facility_id: int
    overall_confidence: float
    capabilities: List[MemoryCapabilityOut]


class IdentityRegistrationStartIn(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str
    ip_address: Optional[str] = None


class IdentityRegistrationStartOut(BaseModel):
    facility_id: int
    user_id: int
    email: str
    verification_sent_at: str
    verification_method: str
    debug_verification_code: str


class IdentityVerificationCompleteIn(BaseModel):
    email: str
    code: str


class IdentityVerificationCompleteOut(BaseModel):
    facility_id: int
    user_id: int
    verification_completed_at: str
    verification_method: str


class LicenseValidationIn(BaseModel):
    cms_provider_id: Optional[str] = None
    ahca_license_number: Optional[str] = None
    medicare_provider_number: Optional[str] = None
    legal_name: Optional[str] = None
    legal_address: Optional[str] = None
    domain: Optional[str] = None


class LicenseValidationOut(BaseModel):
    facility_id: int
    status: str
    name_match: bool
    address_match: bool
    domain_allowed: bool
    provider_match: bool


class AccessCheckIn(BaseModel):
    role: str
    category: str


class AccessCheckOut(BaseModel):
    allowed: bool


class FieldUpdateIn(BaseModel):
    user_id: int
    field_name: str
    new_value: Optional[str] = None
    category: str
    ip_address: Optional[str] = None


class FieldUpdateOut(BaseModel):
    facility_id: int
    audit_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class RevertAuditIn(BaseModel):
    reverted_by_user_id: int
    ip_address: Optional[str] = None


class RevertAuditOut(BaseModel):
    facility_id: int
    reverted_audit_id: int
    reversal_audit_id: int


class StaffInviteIn(BaseModel):
    inviter_user_id: int
    email: str
    full_name: Optional[str] = None
    role: str
    ip_address: Optional[str] = None


class RoleChangeIn(BaseModel):
    actor_user_id: int
    target_user_id: int
    new_role: str


class RoleChangeOut(BaseModel):
    facility_id: int
    target_user_id: int
    old_role: str
    new_role: str


class FacilityIntelligenceProfileOut(BaseModel):
    facility_id: int
    last_updated: str
    sources_used: List[str]
    clinical_score: float
    family_score: float
    employee_score: float
    social_score: float
    reputation_score: float
    legal_risk_score: float
    regulatory_risk_score: float
    intelligence_confidence: float
    verified_facts: List[str]
    public_allegations: List[str]
    public_opinions: List[str]
    missing_information: List[str]
    positive_signals: List[str]
    negative_signals: List[str]
    signal_details: List[Dict[str, object]]
    unresolved_risks: List[str]
    intelligence_summary: str
    social_energy_index: float
    family_satisfaction_index: float
    staff_stability_index: float
    regulatory_risk_index: float
    litigation_risk_index: float
    cultural_match_signals: float
    activity_density_index: float
    community_engagement_index: float
    clinical_quality_index: float
    reputation_index: float
    visual_hero_image: Dict[str, object]
    visual_gallery_images: List[Dict[str, object]]
    visual_lifestyle_tags: List[Dict[str, object]]
    visual_confidence_score: float
    visual_coverage_score: float


class IntelligenceRunSummaryOut(BaseModel):
    processed: int
    facility_ids: List[int]
    update_frequency: Dict[str, str]


class AgentKnowledgeReportOut(BaseModel):
    agent_key: str
    agent_name: str
    domain: str
    mission: Optional[str] = None
    topics_covered: List[str] = Field(default_factory=list)
    knowledge_base: Dict[str, object] = Field(default_factory=dict)
    last_update: Optional[str] = None
    confidence: float
    evidence_count: int
    coverage: float
    api: Dict[str, str] = Field(default_factory=dict)
    health_status: str
    freshness_status: str
    knowledge_age_seconds: int
    last_successful_refresh: Optional[str] = None
    last_refresh_attempt: Optional[str] = None
    refresh_duration_ms: int
    verified_until: Optional[str] = None
    ttl_seconds: int
    pending_changes: int
    pending_reviews: int
    failed_refresh_count: int
    refresh_status: str
    next_refresh_at: Optional[str] = None


class AgentKnowledgeReportSummaryOut(BaseModel):
    agent_key: str
    agent_name: str
    domain: str
    confidence: float
    evidence_count: int
    coverage: float
    health_status: str
    freshness_status: str
    knowledge_age_seconds: int
    ttl_seconds: int
    pending_reviews: int
    last_update: Optional[str] = None
    next_refresh_at: Optional[str] = None


class AgentKnowledgeSearchOut(BaseModel):
    query: str
    matched_agents: List[AgentKnowledgeReportSummaryOut]


class AgentKnowledgeRefreshOut(BaseModel):
    refreshed: int
    failures: int


class RecommendationGuardCheckIn(BaseModel):
    recommendation_key: str
    resident_key: Optional[str] = None
    agent_keys: List[str]
    min_confidence: float = 0.65
    allow_stale: bool = True


class RecommendationGuardDecisionOut(BaseModel):
    agent_key: str
    decision: str
    reason: str
    used_stale: bool
    policy_allowed: bool
    freshness: Optional[str] = None


class RecommendationGuardCheckOut(BaseModel):
    recommendation_key: str
    decisions: List[RecommendationGuardDecisionOut]


class KnowledgeSupervisorOut(BaseModel):
    fresh_agents: int
    stale_agents: int
    expired_knowledge: int
    failed_refreshes: int
    knowledge_age: int
    pending_reviews: int
    refresh_queue: int
    refresh_success_rate: float
    average_knowledge_freshness: float
    alerts: List[str]



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_measure_score(measures: List[QualityMeasure], keywords: List[str]) -> Optional[float]:
    values: List[float] = []
    for measure in measures:
        name = (measure.measure_name or "").lower()
        if any(keyword in name for keyword in keywords) and measure.measure_value is not None:
            values.append(float(measure.measure_value))
    if not values:
        return None
    return mean(values)


def _build_provider_row_map(facilities: List[Facility], state: str) -> Dict[str, dict]:
    ccn_set = {facility.cms_id for facility in facilities}
    file_path = download_dataset(CMS_PROVIDER_DATASET_ID, "provider_information.csv")
    row_map: Dict[str, dict] = {}
    for row in iter_csv_rows(file_path):
        if clean_state(row.get("State")) != state:
            continue
        ccn = row.get("CMS Certification Number (CCN)") or ""
        if ccn in ccn_set:
            row_map[ccn] = row
    return row_map


def _calculate_scores(db: Session, state: str = "FL") -> dict:
    facilities = db.query(Facility).filter(Facility.state == state).order_by(Facility.id.asc()).all()
    provider_rows = _build_provider_row_map(facilities, state)

    medical_values: List[float] = []
    staffing_values: List[float] = []
    safety_values: List[float] = []
    overall_values: List[float] = []

    for facility in facilities:
        quality_rows = db.query(QualityMeasure).filter(QualityMeasure.facility_id == facility.id).all()
        staffing_row = (
            db.query(Staffing)
            .filter(Staffing.facility_id == facility.id)
            .order_by(Staffing.id.desc())
            .first()
        )
        inspection_rows = db.query(Inspection).filter(Inspection.facility_id == facility.id).all()
        provider_row = provider_rows.get(facility.cms_id, {})

        # Medical Quality Score components (0-100)
        cms_rating = stars_to_score(facility.quality_rating or facility.overall_rating)
        hospitalization = invert_percent(_get_measure_score(quality_rows, ["hospital", "rehospital"]))
        er_visits = invert_percent(_get_measure_score(quality_rows, ["emergency", "er visit"]))
        falls = invert_percent(_get_measure_score(quality_rows, ["fall"]))
        pressure_ulcers = invert_percent(_get_measure_score(quality_rows, ["pressure ulcer", "pressure"]))
        weight_loss = invert_percent(_get_measure_score(quality_rows, ["weight loss"]))

        medical_quality_score = clip_0_100(
            0.25 * cms_rating
            + 0.25 * hospitalization
            + 0.15 * er_visits
            + 0.15 * falls
            + 0.10 * pressure_ulcers
            + 0.10 * weight_loss
        )

        # Staffing Score components (0-100)
        rn_hours = staffing_row.rn_hours_per_resident_day if staffing_row else None
        total_staffing_hours = staffing_row.total_nurse_hours_per_resident_day if staffing_row else None
        rn_score = normalize_hours(rn_hours, benchmark=0.75)
        total_staffing_score = normalize_hours(total_staffing_hours, benchmark=3.5)

        agency_staff_raw = to_float(provider_row.get("Agency staff") if provider_row else None)
        agency_staff_score = invert_percent(agency_staff_raw) if agency_staff_raw is not None else 50.0

        turnover_rate = to_float(provider_row.get("Total nursing staff turnover") if provider_row else None)
        turnover_score = invert_percent(turnover_rate)

        staffing_score = clip_0_100(
            0.35 * rn_score
            + 0.25 * total_staffing_score
            + 0.20 * agency_staff_score
            + 0.20 * turnover_score
        )

        # Safety Score components (0-100)
        serious_deficiencies = float(sum(item.severe_deficiency_count or 0 for item in inspection_rows))
        complaints = float(sum(item.payment_denials_count or 0 for item in inspection_rows))
        fines = to_float(provider_row.get("Total Amount of Fines in Dollars") if provider_row else None)
        infection_control = to_float(provider_row.get("Number of Citations from Infection Control Inspections") if provider_row else None)

        serious_score = inverse_count(serious_deficiencies, max_bad=10)
        complaint_score = inverse_count(complaints, max_bad=25)
        fine_score = inverse_count(fines, max_bad=500000)
        infection_score = inverse_count(infection_control, max_bad=10)

        safety_score = clip_0_100(
            0.35 * serious_score
            + 0.25 * complaint_score
            + 0.20 * fine_score
            + 0.20 * infection_score
        )

        overall_optime_score = clip_0_100(
            0.4 * medical_quality_score + 0.35 * staffing_score + 0.25 * safety_score
        )

        facility.medical_quality_score = round(medical_quality_score, 2)
        facility.staffing_score = round(staffing_score, 2)
        facility.safety_score = round(safety_score, 2)
        facility.overall_optime_score = round(overall_optime_score, 2)

        medical_values.append(facility.medical_quality_score)
        staffing_values.append(facility.staffing_score)
        safety_values.append(facility.safety_score)
        overall_values.append(facility.overall_optime_score)

    db.commit()

    def summarize(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"min": 0.0, "max": 0.0, "avg": 0.0}
        return {"min": min(values), "max": max(values), "avg": round(mean(values), 2)}

    return {
        "medical_quality_score": summarize(medical_values),
        "staffing_score": summarize(staffing_values),
        "safety_score": summarize(safety_values),
        "overall_optime_score": summarize(overall_values),
    }


def run_phase1_ingestion(db: Session, state: str = "FL", limit: int = 100) -> dict:
    ccn_to_facility_id, provider_summary = import_provider_information(db, state=state, limit=limit)
    staffing_summary = import_staffing_data(db, ccn_to_facility_id, state=state)
    quality_summary = import_quality_data(db, ccn_to_facility_id, state=state)
    inspection_summary = import_inspection_data(db, ccn_to_facility_id, state=state)
    distributions = _calculate_scores(db, state=state)

    return {
        "facilities_imported": provider_summary["facilities_imported"],
        "missing_records": provider_summary["missing_records"]
        + staffing_summary["missing_records"]
        + quality_summary["missing_records"]
        + inspection_summary["missing_records"],
        "failed_mappings": provider_summary["failed_mappings"]
        + staffing_summary["failed_mappings"]
        + quality_summary["failed_mappings"]
        + inspection_summary["failed_mappings"],
        "score_distributions": distributions,
    }


def _avg_or_zero(value: Optional[float]) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def _group_average_scores(db: Session, success_value: int) -> Dict[str, float]:
    row = (
        db.query(
            func.avg(HumanIntelligenceScore.social_profile_score),
            func.avg(HumanIntelligenceScore.family_support_score),
            func.avg(HumanIntelligenceScore.cultural_match_score),
            func.avg(HumanIntelligenceScore.loneliness_risk_score),
            func.avg(HumanIntelligenceScore.transition_risk_score),
            func.avg(HumanIntelligenceScore.future_care_score),
        )
        .join(ResidentOutcome, ResidentOutcome.human_intelligence_score_id == HumanIntelligenceScore.id)
        .filter(ResidentOutcome.successful_adjustment == success_value)
        .one()
    )

    return {
        "social_profile_score": _avg_or_zero(row[0]),
        "family_support_score": _avg_or_zero(row[1]),
        "cultural_match_score": _avg_or_zero(row[2]),
        "loneliness_risk_score": _avg_or_zero(row[3]),
        "transition_risk_score": _avg_or_zero(row[4]),
        "future_care_score": _avg_or_zero(row[5]),
    }


def _parse_json_array(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _parse_json_objects(raw: Optional[str]) -> List[Dict[str, object]]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _parse_json_object(raw: Optional[str]) -> Dict[str, object]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return {str(key): value[key] for key in value}
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_for_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_lookup(canonical_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_cms: Dict[str, Dict[str, Any]] = {}
    for index, row in enumerate(canonical_records, start=1):
        cms_id = str(row.get("cms_certification_number") or "").strip()
        if cms_id:
            by_cms[cms_id] = {
                "canonical_facility_id": index,
                "community_name": row.get("community_name"),
                "county": row.get("county"),
                "state": row.get("state"),
                "cms_certification_number": cms_id,
                "source_refs": row.get("source_refs") or [],
            }
    return by_cms


def _compute_confidence_level_for_facility(facility: Facility, profile: Optional[FacilityIntelligenceProfile]) -> Dict[str, Any]:
    explicit = str(facility.confidence_level or "").upper().strip()
    if explicit in {"HIGH", "MEDIUM", "LOW"}:
        return {"confidence": explicit, "reason": "facility.confidence_level"}

    profile_confidence = float(profile.intelligence_confidence or 0.0) if profile else 0.0
    known_sources = len(_parse_json_array(profile.sources_used) if profile else [])

    if profile_confidence >= 0.85 and known_sources >= 2:
        return {"confidence": "HIGH", "reason": "derived_from_intelligence_profile"}
    if profile_confidence >= 0.65 and known_sources >= 1:
        return {"confidence": "MEDIUM", "reason": "derived_from_intelligence_profile"}
    if profile_confidence >= 0.45 and known_sources >= 1:
        return {"confidence": "LOW", "reason": "derived_from_intelligence_profile"}

    return {"confidence": "UNKNOWN", "reason": "insufficient_evidence_provenance"}


def _to_intelligence_profile_out(profile: FacilityIntelligenceProfile) -> FacilityIntelligenceProfileOut:
    return FacilityIntelligenceProfileOut(
        facility_id=profile.facility_id,
        last_updated=(profile.last_updated.isoformat() if profile.last_updated else ""),
        sources_used=_parse_json_array(profile.sources_used),
        clinical_score=profile.clinical_score,
        family_score=profile.family_score,
        employee_score=profile.employee_score,
        social_score=profile.social_score,
        reputation_score=profile.reputation_score,
        legal_risk_score=profile.legal_risk_score,
        regulatory_risk_score=profile.regulatory_risk_score,
        intelligence_confidence=profile.intelligence_confidence,
        verified_facts=_parse_json_array(profile.verified_facts),
        public_allegations=_parse_json_array(profile.public_allegations),
        public_opinions=_parse_json_array(profile.public_opinions),
        missing_information=_parse_json_array(profile.missing_information),
        positive_signals=_parse_json_array(profile.positive_signals),
        negative_signals=_parse_json_array(profile.negative_signals),
        signal_details=_parse_json_objects(profile.signal_details),
        unresolved_risks=_parse_json_array(profile.unresolved_risks),
        intelligence_summary=profile.intelligence_summary,
        social_energy_index=profile.social_energy_index,
        family_satisfaction_index=profile.family_satisfaction_index,
        staff_stability_index=profile.staff_stability_index,
        regulatory_risk_index=profile.regulatory_risk_index,
        litigation_risk_index=profile.litigation_risk_index,
        cultural_match_signals=profile.cultural_match_signals,
        activity_density_index=profile.activity_density_index,
        community_engagement_index=profile.community_engagement_index,
        clinical_quality_index=profile.clinical_quality_index,
        reputation_index=profile.reputation_index,
        visual_hero_image=_parse_json_object(profile.visual_hero_image),
        visual_gallery_images=_parse_json_objects(profile.visual_gallery_images),
        visual_lifestyle_tags=_parse_json_objects(profile.visual_lifestyle_tags),
        visual_confidence_score=profile.visual_confidence_score,
        visual_coverage_score=profile.visual_coverage_score,
    )


_AGENT_REPORT_DEF_BY_KEY = {str(item["agent_key"]): item for item in AGENT_REPORT_DEFS}


def _to_agent_knowledge_report_summary(row: AgentKnowledgeReportSnapshot) -> AgentKnowledgeReportSummaryOut:
    return AgentKnowledgeReportSummaryOut(
        agent_key=row.agent_key,
        agent_name=row.agent_name,
        domain=row.domain,
        confidence=float(row.average_confidence or 0.0),
        evidence_count=int(row.evidence_count or 0),
        coverage=float(row.coverage or 0.0),
        health_status=row.health_status,
        freshness_status=row.freshness_status,
        knowledge_age_seconds=int(row.knowledge_age_seconds or 0),
        ttl_seconds=int(row.ttl_seconds or 0),
        pending_reviews=int(row.pending_reviews or 0),
        last_update=row.last_refreshed_at.isoformat() if row.last_refreshed_at else None,
        next_refresh_at=row.next_refresh_at.isoformat() if row.next_refresh_at else None,
    )


def _to_agent_knowledge_report(row: AgentKnowledgeReportSnapshot) -> AgentKnowledgeReportOut:
    payload = _parse_json_object(row.report_json)
    defn = _AGENT_REPORT_DEF_BY_KEY.get(row.agent_key, {})
    return AgentKnowledgeReportOut(
        agent_key=row.agent_key,
        agent_name=row.agent_name,
        domain=row.domain,
        mission=str(payload.get("mission") or defn.get("mission") or ""),
        topics_covered=[str(item) for item in (payload.get("topics_covered") or defn.get("topics") or [])],
        knowledge_base=payload.get("knowledge_base") if isinstance(payload.get("knowledge_base"), dict) else {},
        last_update=row.last_refreshed_at.isoformat() if row.last_refreshed_at else None,
        confidence=float(row.average_confidence or 0.0),
        evidence_count=int(row.evidence_count or 0),
        coverage=float(row.coverage or 0.0),
        api={str(k): str(v) for k, v in ((payload.get("api") or {}) if isinstance(payload.get("api"), dict) else {}).items()},
        health_status=row.health_status,
        freshness_status=row.freshness_status,
        knowledge_age_seconds=int(row.knowledge_age_seconds or 0),
        last_successful_refresh=row.last_successful_refresh.isoformat() if row.last_successful_refresh else None,
        last_refresh_attempt=row.last_refresh_attempt.isoformat() if row.last_refresh_attempt else None,
        refresh_duration_ms=int(row.refresh_duration_ms or 0),
        verified_until=row.verified_until.isoformat() if row.verified_until else None,
        ttl_seconds=int(row.ttl_seconds or 0),
        pending_changes=int(row.pending_changes or 0),
        pending_reviews=int(row.pending_reviews or 0),
        failed_refresh_count=int(row.failed_refresh_count or 0),
        refresh_status=row.refresh_status,
        next_refresh_at=row.next_refresh_at.isoformat() if row.next_refresh_at else None,
    )


@app.on_event("startup")
def startup() -> None:
    print(f"CORS_ALLOWED_ORIGINS={allowed_origins}")
    # Preserve provider memory and verification history across restarts.
    Base.metadata.create_all(bind=engine)
    ensure_provider_identity_schema(engine)
    ensure_facility_intelligence_profile_schema(engine)
    db = SessionLocal()
    try:
        state = os.getenv("OPTIME_IMPORT_STATE", "FL")
        limit = env_int("OPTIME_IMPORT_LIMIT", 100)
        should_reingest = os.getenv("OPTIME_REINGEST_ON_STARTUP", "0") == "1"
        has_facilities = (db.query(func.count(Facility.id)).scalar() or 0) > 0
        if should_reingest or not has_facilities:
            app.state.import_summary = run_phase1_ingestion(db, state=state, limit=limit)
        else:
            app.state.import_summary = {
                "facilities_imported": int(db.query(func.count(Facility.id)).scalar() or 0),
                "missing_records": 0,
                "failed_mappings": 0,
                "score_distributions": {},
            }

        # Prepared knowledge reports can be generated lazily to keep startup memory bounded.
        eager_reports = os.getenv("OPTIME_EAGER_REPORTS_ON_STARTUP", "0") == "1"
        if eager_reports:
            ensure_reports_available(db)
    finally:
        db.close()

    # One-time SMTP validation email on deployment startup.
    print("SMTP_TEST: ATTEMPTING")
    smtp_test_result = send_startup_test_email_once()
    if not smtp_test_result.get("attempted"):
        print(f"SMTP_TEST: SKIPPED reason={smtp_test_result.get('reason', 'unknown')}")
    elif smtp_test_result.get("smtp_accepted"):
        print("SMTP_TEST: SUCCESS smtp_accepted=true")
    else:
        err_type = smtp_test_result.get("error_type", "UNKNOWN")
        err_msg = smtp_test_result.get("error_message", "unknown")
        print(f"SMTP_TEST: FAILED error_type={err_type} message={err_msg}")

    # Refresh reports continuously in background so user requests never wait on research.
    start_background_refresh_loop()
    # Trigger daily executive intelligence report at 08:00 local server time.
    start_executive_report_scheduler()
    logger.info(
        "startup_completed facilities_imported=%s origins=%s",
        app.state.import_summary.get("facilities_imported"),
        len(allowed_origins),
    )


@app.middleware("http")
async def request_observability_middleware(request, call_next):
    start = time.perf_counter()
    path = request.url.path
    method = request.method
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception("request_failed method=%s path=%s duration_ms=%s", method, path, duration_ms)
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    if path in {"/health", "/decision-engine/recommendations", "/facilities"}:
        logger.info(
            "request_completed method=%s path=%s status=%s duration_ms=%s",
            method,
            path,
            response.status_code,
            duration_ms,
        )
    return response


@app.get("/")
async def root():
    return {
        "project": "OPTIME Nursing",
        "status": "running",
        "version": "0.3.0",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/import-summary", response_model=ImportSummaryOut)
async def import_summary():
    summary = getattr(app.state, "import_summary", None)
    if not summary:
        raise HTTPException(status_code=404, detail="Import summary not found")
    return summary


@app.get("/governance/runtime-context")
async def get_governance_runtime_context(db: Session = Depends(get_db)):
    registry_path = REPO_ROOT / "database" / "professional_rule_registry.json"
    three_layer_path = REPO_ROOT / "database" / "three_layer_decision_model_schema.json"
    evidence_path = REPO_ROOT / "database" / "facility_evidence_matrix_snapshot.json"
    candidate_policy_path = REPO_ROOT / "database" / "candidate_governance_policy.json"
    canonical_path = REPO_ROOT / "database" / "florida_senior_living_inventory.json"

    registry_payload = _load_json_file(registry_path)
    three_layer_payload = _load_json_file(three_layer_path)
    evidence_payload = _load_json_file(evidence_path)
    candidate_policy_payload = _load_json_file(candidate_policy_path)
    canonical_payload = _load_json_file(canonical_path)

    facilities = db.query(Facility).filter(Facility.state == "FL").order_by(Facility.id.asc()).all()
    profile_rows = db.query(FacilityIntelligenceProfile).filter(
        FacilityIntelligenceProfile.facility_id.in_([facility.id for facility in facilities])
    ).all() if facilities else []
    profiles_by_facility = {row.facility_id: row for row in profile_rows}

    canonical_records = canonical_payload.get("records") or []
    canonical_by_cms = _canonical_lookup(canonical_records)

    reconciliation_rows: List[Dict[str, Any]] = []
    confidence_totals = {"total_evaluated": len(facilities), "known_confidence": 0, "unknown_confidence": 0}
    confidence_reasons: Dict[str, int] = {}

    for facility in facilities:
        cms_id = str(facility.cms_id or "").strip()
        canonical = canonical_by_cms.get(cms_id)
        identity_status = "CONFIRMED_CANONICAL_ID" if canonical else "UNRESOLVED_IDENTITY"
        reconciliation_rows.append(
            {
                "runtime_facility_id": facility.id,
                "canonical_facility_id": canonical.get("canonical_facility_id") if canonical else None,
                "cms_certification_number": cms_id or None,
                "identity_status": identity_status,
                "source_provenance": canonical.get("source_refs") if canonical else ["runtime_db_only"],
            }
        )

        confidence_result = _compute_confidence_level_for_facility(facility, profiles_by_facility.get(facility.id))
        if confidence_result["confidence"] == "UNKNOWN":
            confidence_totals["unknown_confidence"] += 1
        else:
            confidence_totals["known_confidence"] += 1
        reason_key = str(confidence_result["reason"])
        confidence_reasons[reason_key] = int(confidence_reasons.get(reason_key) or 0) + 1

    confirmed_count = sum(1 for row in reconciliation_rows if row["identity_status"] == "CONFIRMED_CANONICAL_ID")

    return {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "professional_rule_registry": {
            "version": registry_payload.get("phase"),
            "rule_count": len(registry_payload.get("rules") or []),
            "hash": _sha256_for_file(registry_path),
            "rules": registry_payload.get("rules") or [],
            "validator_policy": registry_payload.get("validator_policy") or {},
            "authority_model": registry_payload.get("authority_model") or {},
        },
        "three_layer_model": {
            "hash": _sha256_for_file(three_layer_path),
            "allowed_classifications": three_layer_payload.get("allowed_classifications") or [],
            "governance_boundaries": three_layer_payload.get("governance_boundaries") or {},
        },
        "candidate_governance": {
            "hash": _sha256_for_file(candidate_policy_path),
            "candidate_lifecycle": candidate_policy_payload.get("candidate_lifecycle") or [],
            "hard_rejection_taxonomy": candidate_policy_payload.get("hard_rejection_taxonomy") or [],
            "governance_rules": candidate_policy_payload.get("governance_rules") or [],
        },
        "facility_evidence_runtime": {
            "hash": _sha256_for_file(evidence_path),
            "verification_status_counts": evidence_payload.get("verification_status_counts") or {},
            "source_level_counts": evidence_payload.get("source_level_counts") or {},
            "unknown_field_counts": evidence_payload.get("unknown_field_counts") or {},
            "policies": evidence_payload.get("policies") or {
                "unknown_is_not_no": True,
                "conflict_requires_review": True,
            },
        },
        "canonical_runtime_coverage": {
            "canonical_total": canonical_payload.get("record_count") or len(canonical_records),
            "runtime_total": len(facilities),
            "confirmed_canonical_identity": confirmed_count,
            "unresolved_identity": len(facilities) - confirmed_count,
            "reconciliation": reconciliation_rows,
        },
        "confidence_status": {
            **confidence_totals,
            "reason_breakdown": confidence_reasons,
        },
        "validation_truth": {
            "external_professional_validation": "PARTIAL",
            "benchmark_52_status": "FAIL",
        },
    }


@app.get("/facilities", response_model=List[FacilityListOut])
async def get_facilities(q: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Facility).filter(Facility.state == "FL")

    term = (q or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Facility.name.ilike(like),
                Facility.city.ilike(like),
                Facility.address.ilike(like),
                Facility.zip_code.ilike(like),
                Facility.cms_id.ilike(like),
            )
        )

    facilities = query.order_by(Facility.overall_optime_score.desc().nullslast(), Facility.id.asc()).all()

    if facilities and db.query(FacilityIntelligenceProfile).count() == 0:
        run_intelligence_collection(db)

    intelligence_profiles = {
        profile.facility_id: profile
        for profile in db.query(FacilityIntelligenceProfile).filter(
            FacilityIntelligenceProfile.facility_id.in_([facility.id for facility in facilities])
        ).all()
    }

    canonical_index = get_canonical_facility_index()
    cms_to_canonical_id: Dict[str, str] = {}
    for candidate_id, candidate in canonical_index.items():
        source_identity_ids = candidate.get("source_identity_ids") or {}
        cms_ccn = str(source_identity_ids.get("cms_ccn") or "").strip()
        if cms_ccn:
            cms_to_canonical_id[cms_ccn] = candidate_id

    payload: List[FacilityListOut] = []
    for facility in facilities:
        profile = intelligence_profiles.get(facility.id)
        canonical_facility_id = cms_to_canonical_id.get(str(facility.cms_id or "").strip())
        media_payload = build_visual_media_payload(get_facility_media_record(canonical_facility_id))
        profile_hero = _parse_json_object(profile.visual_hero_image) if profile else {}
        profile_gallery = _parse_json_objects(profile.visual_gallery_images) if profile else []
        visual_hero_image = media_payload["hero"] if media_payload else profile_hero
        visual_gallery_images = media_payload["gallery"] if media_payload else profile_gallery

        payload.append(
            FacilityListOut(
                id=facility.id,
                cms_id=facility.cms_id,
                name=facility.name,
                city=facility.city,
                state=facility.state,
                address=facility.address,
                zip_code=facility.zip_code,
                phone=facility.phone,
                overall_rating=facility.overall_rating,
                staffing_rating=facility.staffing_rating,
                quality_rating=facility.quality_rating,
                inspection_rating=facility.inspection_rating,
                beds=facility.beds,
                medical_quality_score=facility.medical_quality_score,
                staffing_score=facility.staffing_score,
                safety_score=facility.safety_score,
                overall_optime_score=facility.overall_optime_score,
                confidence_level=facility.confidence_level,
                intelligence_confidence=profile.intelligence_confidence if profile else None,
                intelligence_sources_used=_parse_json_array(profile.sources_used) if profile else [],
                intelligence_positive_signals=_parse_json_array(profile.positive_signals) if profile else [],
                intelligence_negative_signals=_parse_json_array(profile.negative_signals) if profile else [],
                intelligence_signal_details=_parse_json_objects(profile.signal_details) if profile else [],
                family_satisfaction_index=profile.family_satisfaction_index if profile else None,
                staff_stability_index=profile.staff_stability_index if profile else None,
                regulatory_risk_index=profile.regulatory_risk_index if profile else None,
                litigation_risk_index=profile.litigation_risk_index if profile else None,
                social_energy_index=profile.social_energy_index if profile else None,
                community_engagement_index=profile.community_engagement_index if profile else None,
                reputation_index=profile.reputation_index if profile else None,
                cultural_match_signals=profile.cultural_match_signals if profile else None,
                visual_hero_image=visual_hero_image,
                visual_gallery_images=visual_gallery_images,
                visual_lifestyle_tags=_parse_json_objects(profile.visual_lifestyle_tags) if profile else [],
                visual_confidence_score=profile.visual_confidence_score if profile else None,
                visual_coverage_score=profile.visual_coverage_score if profile else None,
            )
        )

    return payload


@app.get("/facilities/{id}", response_model=FacilityDetailsOut)
async def get_facility(id: int, db: Session = Depends(get_db)):
    facility = db.query(Facility).filter(Facility.id == id, Facility.state == "FL").first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    quality_rows = db.query(QualityMeasure).filter(QualityMeasure.facility_id == facility.id).all()
    staffing_row = (
        db.query(Staffing)
        .filter(Staffing.facility_id == facility.id)
        .order_by(Staffing.id.desc())
        .first()
    )
    inspection_rows = db.query(Inspection).filter(Inspection.facility_id == facility.id).all()
    profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == facility.id).first()

    medical_components = {
        "cms_rating": round(stars_to_score(facility.quality_rating or facility.overall_rating), 2),
        "hospitalizations": round(invert_percent(_get_measure_score(quality_rows, ["hospital", "rehospital"])), 2),
        "er_visits": round(invert_percent(_get_measure_score(quality_rows, ["emergency", "er visit"])), 2),
        "falls": round(invert_percent(_get_measure_score(quality_rows, ["fall"])), 2),
        "pressure_ulcers": round(invert_percent(_get_measure_score(quality_rows, ["pressure ulcer", "pressure"])), 2),
        "weight_loss": round(invert_percent(_get_measure_score(quality_rows, ["weight loss"])), 2),
    }

    staffing_components = {
        "rn_hours": round(normalize_hours(staffing_row.rn_hours_per_resident_day if staffing_row else None, 0.75), 2),
        "total_staffing": round(normalize_hours(staffing_row.total_nurse_hours_per_resident_day if staffing_row else None, 3.5), 2),
        "agency_staff": 50.0,
        "turnover": 50.0,
    }

    safety_components = {
        "serious_deficiencies": round(inverse_count(sum(item.severe_deficiency_count or 0 for item in inspection_rows), 10), 2),
        "complaints": round(inverse_count(sum(item.payment_denials_count or 0 for item in inspection_rows), 25), 2),
        "fines": 50.0,
        "infection_control": 50.0,
    }

    canonical_facility_id = None
    if facility.cms_id:
        canonical_index = get_canonical_facility_index()
        for candidate_id, candidate in canonical_index.items():
            source_identity_ids = candidate.get("source_identity_ids") or {}
            if str(source_identity_ids.get("cms_ccn") or "") == str(facility.cms_id):
                canonical_facility_id = candidate_id
                break

    media_payload = build_visual_media_payload(get_facility_media_record(canonical_facility_id))
    profile_hero = _parse_json_object(profile.visual_hero_image) if profile else {}
    profile_gallery = _parse_json_objects(profile.visual_gallery_images) if profile else []
    visual_hero_image = media_payload["hero"] if media_payload else profile_hero
    visual_gallery_images = media_payload["gallery"] if media_payload else profile_gallery

    return FacilityDetailsOut(
        id=facility.id,
        cms_id=facility.cms_id,
        canonical_facility_id=canonical_facility_id,
        name=facility.name,
        address=facility.address,
        city=facility.city,
        state=facility.state,
        zip_code=facility.zip_code,
        phone=facility.phone,
        overall_rating=facility.overall_rating,
        staffing_rating=facility.staffing_rating,
        quality_rating=facility.quality_rating,
        inspection_rating=facility.inspection_rating,
        beds=facility.beds,
        confidence_level=facility.confidence_level,
        visual_hero_image=visual_hero_image,
        visual_gallery_images=visual_gallery_images,
        visual_lifestyle_tags=_parse_json_objects(profile.visual_lifestyle_tags) if profile else [],
        visual_confidence_score=profile.visual_confidence_score if profile else None,
        visual_coverage_score=profile.visual_coverage_score if profile else None,
        score_breakdown=ScoreBreakdownOut(
            medical_quality_score=facility.medical_quality_score or 0.0,
            staffing_score=facility.staffing_score or 0.0,
            safety_score=facility.safety_score or 0.0,
            overall_optime_score=facility.overall_optime_score or 0.0,
            medical_components=medical_components,
            staffing_components=staffing_components,
            safety_components=safety_components,
        ),
    )


@app.get("/optime-parameter-registry", response_model=ParameterRegistryOut)
async def get_optime_parameter_registry():
    return get_parameter_registry_payload()


@app.get("/live-facility-profiles/{cms_ccn}")
async def get_live_profile_by_ccn(cms_ccn: str):
    try:
        return get_live_facility_profile(cms_ccn)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Audited facility profile not found") from exc


@app.get("/canonical-facilities/{canonical_id}/parameter-table", response_model=FacilityParameterTableOut)
async def get_canonical_facility_parameter_table(
    canonical_id: str,
    need_tags: Optional[str] = Query(default=None),
    priority_parameter_ids: Optional[str] = Query(default=None),
    profile_key: Optional[str] = Query(default=None),
):
    parsed_need_tags = [item.strip() for item in (need_tags or "").split(",") if item.strip()]
    parsed_priority_ids = [item.strip() for item in (priority_parameter_ids or "").split(",") if item.strip()]
    try:
        return get_facility_parameter_table(
            canonical_id,
            need_tags=parsed_need_tags,
            priority_parameter_ids=parsed_priority_ids,
            profile_key=profile_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Canonical facility not found") from exc


@app.post("/canonical-facilities/parameter-comparison", response_model=FacilityParameterComparisonOut)
async def post_canonical_facility_parameter_comparison(payload: FacilityParameterComparisonIn):
    try:
        return compare_facility_parameter_tables(
            payload.canonical_facility_ids,
            need_tags=payload.need_tags,
            priority_parameter_ids=payload.priority_parameter_ids,
            profile_key=payload.profile_key,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Canonical facility not found: {exc.args[0]}") from exc


@app.post("/canonical-facilities/personalized-parameter-order", response_model=PersonalizedParameterOrderOut)
async def post_personalized_parameter_order(payload: PersonalizedParameterOrderIn):
    return get_personalized_parameter_order(
        need_tags=payload.need_tags,
        priority_parameter_ids=payload.priority_parameter_ids,
        profile_key=payload.profile_key,
    )


@app.post("/decision-engine/patient-needs-profile", response_model=PatientNeedsProfileOut)
async def post_patient_needs_profile(payload: PatientNeedsProfileRequestIn, db: Session = Depends(get_db)):
    resolved = resolve_case_for_decision(
        db,
        patient_case_id=payload.patient_case_id,
        questionnaire_state=payload.questionnaire_state,
        natural_language_query=payload.natural_language_query or "",
    )
    return build_patient_needs_profile(
        resolved.get("questionnaire_state") or {},
        resolved.get("natural_language_query") or "",
    )


@app.post("/decision-engine/recommendations", response_model=PatientDecisionEngineOut)
async def post_patient_decision_recommendations(payload: PatientDecisionEngineRequestIn, db: Session = Depends(get_db)):
    started = time.perf_counter()
    logger.info("decision_request_received limit=%s", payload.limit)
    resolved = resolve_case_for_decision(
        db,
        patient_case_id=payload.patient_case_id,
        questionnaire_state=payload.questionnaire_state,
        natural_language_query=payload.natural_language_query or "",
    )
    response = run_patient_decision_engine(
        questionnaire_state=resolved.get("questionnaire_state") or {},
        natural_language_query=resolved.get("natural_language_query") or "",
        limit=payload.limit,
    )
    response["patient_case_id"] = resolved.get("patient_case_id")

    ccn_to_facility_id = {
        str(facility.cms_id): int(facility.id)
        for facility in db.query(Facility.id, Facility.cms_id).filter(Facility.state == "FL").all()
    }
    for result in response.get("results", []):
        source_identity_ids = result.get("source_identity_ids") or {}
        cms_ccn = str(source_identity_ids.get("cms_ccn") or "")
        result["facility_profile_id"] = ccn_to_facility_id.get(cms_ccn)

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "decision_request_completed result_count=%s total_candidates_scored=%s duration_ms=%s",
        response.get("result_count"),
        response.get("total_candidates_scored"),
        duration_ms,
    )

    return response


@app.post("/decision-engine/comparison-context", response_model=PatientComparisonContextOut)
async def post_patient_comparison_context(payload: PatientComparisonContextRequestIn):
    return build_patient_comparison_context(payload.canonical_facility_ids, payload.patient_needs_profile)


@app.post("/patient-case/free-text", response_model=PatientCaseOut)
async def post_patient_case_free_text(payload: PatientCaseFreeTextIn, db: Session = Depends(get_db)):
    try:
        return upsert_from_free_text(
            db,
            case_text=payload.case_text,
            patient_case_id=payload.patient_case_id,
            source_name=payload.source_name or "natural_language",
            reason=payload.reason or "free_text_update",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/patient-case/questionnaire", response_model=PatientCaseOut)
async def post_patient_case_questionnaire(payload: PatientCaseQuestionnaireIn, db: Session = Depends(get_db)):
    return upsert_from_questionnaire(
        db,
        questionnaire_state=payload.questionnaire_state,
        patient_case_id=payload.patient_case_id,
        source_name=payload.source_name or "homepage_questionnaire",
        reason=payload.reason or "questionnaire_update",
    )


@app.post("/patient-case/chat", response_model=PatientCaseOut)
async def post_patient_case_chat(payload: PatientCaseChatIn, db: Session = Depends(get_db)):
    try:
        return upsert_from_chat(
            db,
            message=payload.message,
            patient_case_id=payload.patient_case_id,
            source_name=payload.source_name or "ai_chat",
            reason=payload.reason or "chat_update",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/patient-case/update", response_model=PatientCaseOut)
async def post_patient_case_update(payload: PatientCaseGenericUpdateIn, db: Session = Depends(get_db)):
    try:
        return upsert_from_generic_update(
            db,
            updates=payload.updates,
            patient_case_id=payload.patient_case_id,
            source_type=payload.source_type,
            source_name=payload.source_name,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/patient-case/{id}", response_model=PatientCaseOut)
async def get_patient_case_by_id(id: int, db: Session = Depends(get_db)):
    try:
        return get_patient_case(db, id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/patient-case/{id}/history", response_model=PatientCaseHistoryOut)
async def get_patient_case_history_by_id(id: int, db: Session = Depends(get_db)):
    try:
        return get_patient_case_history(db, id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/patient-case/{id}/missing", response_model=PatientCaseMissingOut)
async def get_patient_case_missing_by_id(id: int, db: Session = Depends(get_db)):
    try:
        return get_patient_case_missing(db, id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/patient-case/{id}/summary", response_model=PatientCaseSummaryOut)
async def get_patient_case_summary_by_id(id: int, db: Session = Depends(get_db)):
    try:
        return get_patient_case_summary(db, id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/ai/understand-case", response_model=PatientProfileOut)
async def post_ai_understand_case(payload: CaseUnderstandingRequestIn, db: Session = Depends(get_db)):
    try:
        case_payload = upsert_from_free_text(
            db,
            case_text=payload.case_text,
            patient_case_id=payload.patient_case_id,
            source_name="natural_language",
            reason="legacy_understand_case",
        )
        return build_legacy_patient_profile_adapter(case_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/ai/refine-case", response_model=PatientProfileOut)
async def post_ai_refine_case(payload: CaseRefinementRequestIn, db: Session = Depends(get_db)):
    try:
        patient_case_id = payload.patient_case_id or payload.profile_id
        if patient_case_id is None:
            raise ValueError("profile_id or patient_case_id is required")
        case_payload = upsert_from_free_text(
            db,
            case_text=payload.refinement_text,
            patient_case_id=patient_case_id,
            source_name="natural_language",
            reason="legacy_refine_case",
        )
        return build_legacy_patient_profile_adapter(case_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/patient-profile/{id}", response_model=PatientProfileOut)
async def get_patient_profile_by_id(id: int, db: Session = Depends(get_db)):
    try:
        case_payload = get_patient_case(db, id)
        return build_legacy_patient_profile_adapter(case_payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/ai/understand-case/validation", response_model=CaseUnderstandingValidationOut)
async def get_ai_case_understanding_validation(
    db: Session = Depends(get_db),
):
    return run_unified_patient_case_validation(db)


@app.post("/intelligence/run", response_model=IntelligenceRunSummaryOut)
async def run_intelligence(facility_id: Optional[int] = Query(default=None), db: Session = Depends(get_db)):
    if facility_id is not None:
        facility = db.query(Facility).filter(Facility.id == facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

    result = run_intelligence_collection(db, facility_id=facility_id)
    return IntelligenceRunSummaryOut(
        processed=int(result["processed"]),
        facility_ids=[int(value) for value in result["facility_ids"]],
        update_frequency={str(key): str(value) for key, value in result["update_frequency"].items()},
    )


@app.get("/intelligence/facilities/{id}", response_model=FacilityIntelligenceProfileOut)
async def get_facility_intelligence_profile(id: int, db: Session = Depends(get_db)):
    profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == id).first()
    if not profile:
        facility = db.query(Facility).filter(Facility.id == id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")
        run_intelligence_collection(db, facility_id=id)
        profile = db.query(FacilityIntelligenceProfile).filter(FacilityIntelligenceProfile.facility_id == id).first()

    if not profile:
        raise HTTPException(status_code=500, detail="Intelligence profile generation failed")

    return _to_intelligence_profile_out(profile)


@app.get("/intelligence/schedule")
async def intelligence_schedule():
    return {
        "update_frequency": UPDATE_FREQUENCY,
        "policy": "Only publicly available information is used.",
    }


@app.get("/expert-agents/knowledge-reports", response_model=List[AgentKnowledgeReportSummaryOut])
async def list_agent_knowledge_reports(db: Session = Depends(get_db)):
    ensure_reports_available(db)
    rows = db.query(AgentKnowledgeReportSnapshot).order_by(AgentKnowledgeReportSnapshot.agent_name.asc()).all()
    return [_to_agent_knowledge_report_summary(row) for row in rows]


@app.get("/expert-agents/{agent_key}/knowledge-report", response_model=AgentKnowledgeReportOut)
async def get_agent_knowledge_report(agent_key: str, db: Session = Depends(get_db)):
    ensure_reports_available(db)
    row = db.query(AgentKnowledgeReportSnapshot).filter(AgentKnowledgeReportSnapshot.agent_key == agent_key).first()
    if not row:
        raise HTTPException(status_code=404, detail="Agent knowledge report not found")
    return _to_agent_knowledge_report(row)


@app.get("/expert-agents/knowledge-reports/search", response_model=AgentKnowledgeSearchOut)
async def search_agent_knowledge_reports(query: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    ensure_reports_available(db)
    term = query.strip().lower()
    rows = db.query(AgentKnowledgeReportSnapshot).all()

    matched: List[AgentKnowledgeReportSummaryOut] = []
    for row in rows:
        payload = _parse_json_object(row.report_json)
        topics = [str(item).lower() for item in (payload.get("topics_covered") or [])]
        mission = str(payload.get("mission") or "").lower()
        haystack = " ".join([row.agent_name.lower(), row.domain.lower(), mission] + topics)
        if term in haystack:
            matched.append(_to_agent_knowledge_report_summary(row))

    return AgentKnowledgeSearchOut(query=query, matched_agents=matched)


@app.post("/expert-agents/knowledge-reports/refresh", response_model=AgentKnowledgeRefreshOut)
async def refresh_agent_knowledge_reports(db: Session = Depends(get_db)):
    result = refresh_all_agent_reports(db, refresh_mode="manual", force=True)
    return AgentKnowledgeRefreshOut(refreshed=int(result.get("refreshed", 0)), failures=int(result.get("failures", 0)))


@app.get("/expert-agents/freshness/states")
async def knowledge_freshness_states():
    return {
        "states": sorted(FRESHNESS_STATES),
        "ttl_policy_seconds": TTL_POLICY_SECONDS,
    }


@app.get("/supervisor/overview", response_model=KnowledgeSupervisorOut)
async def supervisor_overview(db: Session = Depends(get_db)):
    ensure_reports_available(db)
    summary = compute_supervisor_metrics(db)
    return KnowledgeSupervisorOut(**summary)


@app.post("/supervisor/run-cycle")
async def supervisor_run_cycle(db: Session = Depends(get_db)):
    ensure_reports_available(db)
    return run_supervisor_cycle(db)


@app.get("/supervisor/incidents")
async def supervisor_incidents(limit: int = Query(default=200, ge=1, le=1000), db: Session = Depends(get_db)):
    return {"incidents": recent_incidents(db, limit=limit)}


@app.get("/supervisor/stale-usage")
async def supervisor_stale_usage(hours: int = Query(default=24, ge=1, le=24 * 30), db: Session = Depends(get_db)):
    return stale_usage_summary(db, hours=hours)


@app.post("/recommendation/knowledge-guard", response_model=RecommendationGuardCheckOut)
async def recommendation_knowledge_guard(payload: RecommendationGuardCheckIn, db: Session = Depends(get_db)):
    ensure_reports_available(db)
    decisions: List[RecommendationGuardDecisionOut] = []
    for agent_key in payload.agent_keys:
        decision = recommendation_guard_decision(
            db,
            recommendation_key=payload.recommendation_key,
            resident_key=payload.resident_key,
            agent_key=agent_key,
            min_confidence=float(payload.min_confidence),
            allow_stale=bool(payload.allow_stale),
        )
        decisions.append(RecommendationGuardDecisionOut(**decision))

    return RecommendationGuardCheckOut(recommendation_key=payload.recommendation_key, decisions=decisions)


@app.post("/human-intelligence", response_model=HumanIntelligenceOut)
async def create_human_intelligence(payload: HumanIntelligenceIn, db: Session = Depends(get_db)):
    def clip_optional(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return clip_0_100(value)

    record = HumanIntelligenceScore(
        resident_key=payload.resident_key,
        relationship=payload.relationship,
        age_group=payload.age_group,
        social_profile_score=clip_0_100(payload.social_profile_score),
        family_support_score=clip_0_100(payload.family_support_score),
        cultural_match_score=clip_0_100(payload.cultural_match_score),
        loneliness_risk_score=clip_0_100(payload.loneliness_risk_score),
        transition_risk_score=clip_0_100(payload.transition_risk_score),
        future_care_score=clip_0_100(payload.future_care_score),
        social_fit_score=clip_optional(payload.social_fit_score),
        family_fit_score=clip_optional(payload.family_fit_score),
        language_match_score=clip_optional(payload.language_match_score),
        religious_fit_score=clip_optional(payload.religious_fit_score),
        language_fit_score=clip_optional(payload.language_fit_score),
        cultural_fit_score=clip_optional(payload.cultural_fit_score),
        food_fit_score=clip_optional(payload.food_fit_score),
        family_engagement_score=clip_optional(payload.family_engagement_score),
        community_style_score=clip_optional(payload.community_style_score),
        independence_fit_score=clip_optional(payload.independence_fit_score),
        transition_success_probability=clip_optional(payload.transition_success_probability),
        metadata_json=payload.metadata_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return HumanIntelligenceOut.model_validate(record)


@app.post("/human-intelligence/adaptive-response", response_model=AdaptiveQuestionResponseOut)
async def create_adaptive_response(payload: AdaptiveQuestionResponseIn, db: Session = Depends(get_db)):
    record = AdaptiveQuestionResponse(
        resident_key=payload.resident_key,
        question_key=payload.question_key,
        answer=payload.answer,
        signal_type=payload.signal_type,
        signal_json=payload.signal_json,
        weights_json=payload.weights_json,
        impact_explanation=payload.impact_explanation,
        info_gain_score=max(0.0, min(100.0, payload.info_gain_score)),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return AdaptiveQuestionResponseOut.model_validate(record)


@app.post("/resident-outcomes", response_model=ResidentOutcomeOut)
async def create_resident_outcome(payload: ResidentOutcomeIn, db: Session = Depends(get_db)):
    if payload.human_intelligence_score_id is not None:
        score_record = db.query(HumanIntelligenceScore).filter(HumanIntelligenceScore.id == payload.human_intelligence_score_id).first()
        if not score_record:
            raise HTTPException(status_code=404, detail="Human intelligence score not found")

    if payload.facility_id is not None:
        facility = db.query(Facility).filter(Facility.id == payload.facility_id).first()
        if not facility:
            raise HTTPException(status_code=404, detail="Facility not found")

    record = ResidentOutcome(
        resident_key=payload.resident_key,
        human_intelligence_score_id=payload.human_intelligence_score_id,
        facility_id=payload.facility_id,
        successful_adjustment=1 if payload.successful_adjustment else 0,
        loneliness_event=1 if payload.loneliness_event else 0,
        relocated_within_24m=1 if payload.relocated_within_24m else 0,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ResidentOutcomeOut(
        id=record.id,
        resident_key=record.resident_key,
        human_intelligence_score_id=record.human_intelligence_score_id,
        facility_id=record.facility_id,
        successful_adjustment=bool(record.successful_adjustment),
        loneliness_event=bool(record.loneliness_event),
        relocated_within_24m=bool(record.relocated_within_24m),
        notes=record.notes,
    )


@app.get("/validation-feedback", response_model=ValidationFeedbackOut)
async def get_validation_feedback(db: Session = Depends(get_db)):
    outcomes_count = db.query(func.count(ResidentOutcome.id)).scalar() or 0
    if outcomes_count == 0:
        return ValidationFeedbackOut(
            outcomes_count=0,
            adjustment_success_rate=0.0,
            loneliness_event_rate=0.0,
            relocation_rate_24m=0.0,
            average_scores_for_successful_adjustment={
                "social_profile_score": 0.0,
                "family_support_score": 0.0,
                "cultural_match_score": 0.0,
                "loneliness_risk_score": 0.0,
                "transition_risk_score": 0.0,
                "future_care_score": 0.0,
            },
            average_scores_for_unsuccessful_adjustment={
                "social_profile_score": 0.0,
                "family_support_score": 0.0,
                "cultural_match_score": 0.0,
                "loneliness_risk_score": 0.0,
                "transition_risk_score": 0.0,
                "future_care_score": 0.0,
            },
        )

    success_count = db.query(func.sum(ResidentOutcome.successful_adjustment)).scalar() or 0
    loneliness_count = db.query(func.sum(ResidentOutcome.loneliness_event)).scalar() or 0
    relocation_count = db.query(func.sum(ResidentOutcome.relocated_within_24m)).scalar() or 0

    return ValidationFeedbackOut(
        outcomes_count=int(outcomes_count),
        adjustment_success_rate=round((float(success_count) / float(outcomes_count)) * 100, 2),
        loneliness_event_rate=round((float(loneliness_count) / float(outcomes_count)) * 100, 2),
        relocation_rate_24m=round((float(relocation_count) / float(outcomes_count)) * 100, 2),
        average_scores_for_successful_adjustment=_group_average_scores(db, 1),
        average_scores_for_unsuccessful_adjustment=_group_average_scores(db, 0),
    )


@app.post("/provider/facilities/{facility_id}/activities/import", response_model=ActivityImportOut)
async def import_facility_activities(
    facility_id: int,
    payload: ActivityImportIn,
    db: Session = Depends(get_db),
):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    source_type = (payload.source_type or "").strip().lower()
    if source_type not in {"google_calendar", "ics", "csv", "pdf"}:
        raise HTTPException(status_code=400, detail="source_type must be one of: google_calendar, ics, csv, pdf")

    try:
        result = import_activity_categories(
            db=db,
            facility_id=facility_id,
            source_type=source_type,
            content=payload.content,
            updated_by_user_id=payload.updated_by_user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return ActivityImportOut(
        facility_id=int(result["facility_id"]),
        source_type=str(result["source_type"]),
        imported_at=str(result["imported_at"]),
        categories=[ActivityCategoryOut(**item) for item in result["categories"]],
        privacy_policy=str(result["privacy_policy"]),
    )


@app.get("/provider/facilities/{facility_id}/activities/categories", response_model=List[ActivityCategoryOut])
async def get_facility_activity_categories(
    facility_id: int,
    db: Session = Depends(get_db),
):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    return [ActivityCategoryOut(**item) for item in get_public_activity_categories(db, facility_id)]


@app.get("/provider/activity-intelligence/policy")
async def get_activity_intelligence_policy():
    return {
        "supported_imports": ["google_calendar", "ics", "csv", "pdf"],
        "stored_public_categories": ALLOWED_ACTIVITY_CATEGORIES,
        "privacy": "Exact schedules are never exposed publicly; only category-level availability and confidence are returned.",
    }


@app.post("/provider/facilities/{facility_id}/verification/persist", response_model=ProviderPersistOut)
async def persist_provider_verification_answers(
    facility_id: int,
    payload: ProviderPersistIn,
    db: Session = Depends(get_db),
):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    result = apply_provider_verification_answers(
        db=db,
        facility_id=facility_id,
        answers=[
            {
                "capability_key": item.capability_key,
                "value": item.value,
                "source": item.source,
            }
            for item in payload.answers
        ],
        verified_by_user_id=payload.verified_by_user_id,
        verification_method=payload.verification_method,
        request_subject=payload.request_subject,
        request_body=payload.request_body,
    )

    return ProviderPersistOut(
        facility_id=int(result["facility_id"]),
        request_id=int(result["request_id"]),
        persisted_answers=int(result["persisted_answers"]),
        conflict_records=int(result["conflict_records"]),
    )


@app.get("/provider/facilities/{facility_id}/memory", response_model=FacilityMemoryOut)
async def get_facility_memory(
    facility_id: int,
    db: Session = Depends(get_db),
):
    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    memory = facility_memory_overlay(db, facility_id)
    return FacilityMemoryOut(
        facility_id=int(memory["facility_id"]),
        overall_confidence=float(memory["overall_confidence"]),
        capabilities=[MemoryCapabilityOut(**item) for item in memory["capabilities"]],
    )


@app.post("/provider/facilities/{facility_id}/identity/register/start", response_model=IdentityRegistrationStartOut)
async def provider_identity_register_start(
    facility_id: int,
    payload: IdentityRegistrationStartIn,
    db: Session = Depends(get_db),
):
    try:
        result = start_email_verification(
            db=db,
            facility_id=facility_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            ip_address=payload.ip_address,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return IdentityRegistrationStartOut(**result)


@app.post("/provider/facilities/{facility_id}/identity/register/verify", response_model=IdentityVerificationCompleteOut)
async def provider_identity_register_verify(
    facility_id: int,
    payload: IdentityVerificationCompleteIn,
    db: Session = Depends(get_db),
):
    try:
        result = complete_email_verification(
            db=db,
            facility_id=facility_id,
            email=payload.email,
            code=payload.code,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return IdentityVerificationCompleteOut(**result)


@app.post("/provider/facilities/{facility_id}/identity/license/validate", response_model=LicenseValidationOut)
async def provider_identity_license_validate(
    facility_id: int,
    payload: LicenseValidationIn,
    db: Session = Depends(get_db),
):
    try:
        result = validate_license_ownership(
            db=db,
            facility_id=facility_id,
            cms_provider_id=payload.cms_provider_id,
            ahca_license_number=payload.ahca_license_number,
            medicare_provider_number=payload.medicare_provider_number,
            legal_name=payload.legal_name,
            legal_address=payload.legal_address,
            domain=payload.domain,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return LicenseValidationOut(**result)


@app.post("/provider/identity/access-check", response_model=AccessCheckOut)
async def provider_identity_access_check(payload: AccessCheckIn):
    return AccessCheckOut(allowed=role_can_edit_category(payload.role, payload.category))


@app.post("/provider/facilities/{facility_id}/identity/field-update", response_model=FieldUpdateOut)
async def provider_identity_field_update(
    facility_id: int,
    payload: FieldUpdateIn,
    db: Session = Depends(get_db),
):
    try:
        result = apply_facility_field_update(
            db=db,
            facility_id=facility_id,
            user_id=payload.user_id,
            field_name=payload.field_name,
            new_value=payload.new_value,
            category=payload.category,
            ip_address=payload.ip_address,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return FieldUpdateOut(**result)


@app.post("/provider/facilities/{facility_id}/identity/audit/{audit_id}/revert", response_model=RevertAuditOut)
async def provider_identity_revert_audit(
    facility_id: int,
    audit_id: int,
    payload: RevertAuditIn,
    db: Session = Depends(get_db),
):
    try:
        result = revert_audit_change(
            db=db,
            facility_id=facility_id,
            audit_id=audit_id,
            reverted_by_user_id=payload.reverted_by_user_id,
            ip_address=payload.ip_address,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return RevertAuditOut(**result)


@app.post("/provider/facilities/{facility_id}/identity/staff/invite", response_model=IdentityRegistrationStartOut)
async def provider_identity_staff_invite(
    facility_id: int,
    payload: StaffInviteIn,
    db: Session = Depends(get_db),
):
    try:
        result = invite_staff_member(
            db=db,
            facility_id=facility_id,
            inviter_user_id=payload.inviter_user_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            ip_address=payload.ip_address,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return IdentityRegistrationStartOut(**result)


@app.post("/provider/facilities/{facility_id}/identity/role/change", response_model=RoleChangeOut)
async def provider_identity_role_change(
    facility_id: int,
    payload: RoleChangeIn,
    db: Session = Depends(get_db),
):
    try:
        result = request_role_change(
            db=db,
            facility_id=facility_id,
            actor_user_id=payload.actor_user_id,
            target_user_id=payload.target_user_id,
            new_role=payload.new_role,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return RoleChangeOut(**result)


@app.post("/provider/identity/reverification/run")
async def provider_identity_reverification_run(db: Session = Depends(get_db)):
    return run_annual_reverification(db)


@app.get("/executive-report/latest")
async def executive_report_latest():
    latest = get_latest_executive_report()
    if not latest:
        raise HTTPException(status_code=404, detail="No executive report generated yet")
    return latest


@app.get("/executive-report/latest/full")
async def executive_report_latest_full():
    payload = get_executive_report_payload()
    if not payload:
        raise HTTPException(status_code=404, detail="No executive report generated yet")
    return payload


@app.get("/executive-report/by-id/{report_id}")
async def executive_report_by_id(report_id: str):
    payload = get_executive_report_payload(report_id=report_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Executive report not found")
    return payload


@app.get("/executive-report/history")
async def executive_report_history(limit: int = Query(default=30, ge=1, le=365)):
    return {"reports": get_executive_report_history(limit=limit)}


@app.get("/executive-report/compare")
async def executive_report_compare():
    return compare_latest_vs_previous()


@app.get("/evidence/traceability/audit")
async def evidence_traceability_audit(db: Session = Depends(get_db)):
    return audit_traceability(db)


@app.get("/evidence/facilities/{facility_id}/material-claims")
async def evidence_facility_material_claims(facility_id: int, db: Session = Depends(get_db)):
    payload = facility_material_claim_trace(db, facility_id)
    if payload.get("error") == "facility_not_found":
        raise HTTPException(status_code=404, detail="Facility not found")
    return payload


@app.get("/evidence/recommendations/{recommendation_key}/score-trace")
async def evidence_recommendation_score_trace(recommendation_key: str, db: Session = Depends(get_db)):
    return recommendation_score_trace(db, recommendation_key)
