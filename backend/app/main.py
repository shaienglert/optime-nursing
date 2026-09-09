import os
import json
import hashlib
import logging
import time
from datetime import datetime

# Uvicorn configures its own named loggers (uvicorn, uvicorn.error, uvicorn.access) but
# never touches the root logger, so any application logger.info()/warning() call was
# silently dropped -- created but never written anywhere, no handler, no visible error.
# This must run before any application logger is used.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
from statistics import mean
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.facility import AdaptiveQuestionResponse, Facility, FacilityIntelligenceProfile, HumanIntelligenceScore, Inspection, QualityMeasure, ResidentOutcome, Staffing
import app.models.clinical_evidence
import app.models.agent_execution
import app.models.external_discovery
import app.models.knowledge_fabric
import app.models.personal_report_case
import app.models.facility_room_offering
import app.models.facility_outreach
import app.models.placement_referral
import app.models.competitive_intelligence
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
from app.services.chief_ai_supervisor import recent_incidents, run_supervisor_cycle, stale_usage_summary, start_supervisor_scheduler
from app.services.cms_inspection_import import import_inspection_data
from app.services.cms_provider_import import import_provider_information
from app.services.cms_quality_import import import_quality_data
from app.services.cms_staffing_import import import_staffing_data
from app.services.activity_intelligence import ALLOWED_ACTIVITY_CATEGORIES, get_public_activity_categories, import_activity_categories
from app.services.facility_memory_persistence import apply_provider_verification_answers, facility_memory_overlay
from app.services.schema_migrations import ensure_facility_intelligence_profile_schema, ensure_provider_identity_schema
from app.services.schema_migrations import ensure_agent_knowledge_report_snapshot_schema
from app.services.schema_migrations import ensure_market_metric_observation_schema, ensure_market_supply_signal_schema, ensure_state_license_schema
from app.services.market_report_service import market_report


from app.services.schema_migrations import ensure_deferred_report_schema
from app.services.deferred_report_service import (
    pending_report_summary,
    process_pending_reports,
    request_deferred_report,
)
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
from app.services.facility_profile_portal import (
    add_photo,
    deactivate_photo,
    facility_profile_snapshot,
    recompute_completeness,
    save_capabilities,
    search_claimable_facilities,
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
from app.services.patient_decision_engine import (
    _regulatory_index,
    build_patient_comparison_context,
    build_patient_needs_profile,
    run_patient_decision_engine,
)
from app.services.personal_decision_report_builder import (
    build_personal_decision_report,
    serialize_personal_report_payload,
)
from app.services.personal_decision_report_contract import ReportContractViolation
from app.services.personal_report_case_service import case_inputs, create_case, get_case_by_token, save_snapshot
from app.services.facility_room_service import list_room_types
from app.services import facility_outreach_service
from app.services import placement_referral_service
from app.services.competitive_intelligence_service import (
    latest_signals as competitive_intelligence_latest_signals,
    run_competitive_intelligence_cycle,
    start_competitive_intelligence_scheduler,
)
from app.services.market_supply_intelligence_service import (
    latest_market_supply_signals,
    run_las_vegas_market_supply_pilot,
    run_market_supply_intelligence_cycle,
    start_market_supply_intelligence_scheduler,
)
from app.services.runtime_sync_service import get_runtime_sync_status

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


class FacilityRoomPhotoOut(BaseModel):
    url: str
    caption: Optional[str] = None


class FacilityRoomTypeOut(BaseModel):
    room_type_name: str
    description: str
    monthly_price: Optional[float] = None
    availability_status: str
    source: str
    last_verified_at: Optional[str] = None
    photos: List[FacilityRoomPhotoOut] = Field(default_factory=list)


class FacilityRoomsOut(BaseModel):
    canonical_facility_id: str
    facility_name: str
    has_data: bool
    room_types: List[FacilityRoomTypeOut] = Field(default_factory=list)


class FacilityOutreachDraftOut(BaseModel):
    to: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None


class FacilityOutreachRequestOut(BaseModel):
    id: int
    canonical_facility_id: str
    facility_name: str
    status: str
    contact_email: Optional[str] = None
    failure_reason: Optional[str] = None
    requested_at: str
    sent_at: Optional[str] = None
    responded_at: Optional[str] = None
    draft: Optional[FacilityOutreachDraftOut] = None


class FacilityOutreachPublicStatusOut(BaseModel):
    canonical_facility_id: str
    facility_name: str
    status: str


class RoomSubmissionIn(BaseModel):
    room_type_name: str
    description: str = ""
    monthly_price_cents: Optional[int] = None
    availability_status: str = "UNKNOWN"
    photo_urls: List[str] = Field(default_factory=list)


class FacilityOutreachSubmissionIn(BaseModel):
    room_types: List[RoomSubmissionIn]


class PlacementReferralCreateIn(BaseModel):
    canonical_facility_id: str
    case_token: Optional[str] = None


class PlacementReferralConfirmEntryIn(BaseModel):
    entry_date: str
    confirmed_by: Optional[str] = None


class PlacementReferralDepartureIn(BaseModel):
    departure_date: str
    reason: str


class PlacementReferralOut(BaseModel):
    referral_code: str
    canonical_facility_id: str
    facility_name: str
    billable_status: str
    benefit_amount: float
    facility_credit_amount: float
    commission_amount: float
    commission_due: float
    entry_confirmed_at: Optional[str] = None
    departure_date: Optional[str] = None
    departure_reason: Optional[str] = None
    created_at: str


class CompetitiveIntelligenceSignalOut(BaseModel):
    competitor_key: str
    competitor_name: str
    signal_type: str
    source_url: str
    detail_text: str
    first_observed_at: str
    last_observed_at: str
    last_changed_at: Optional[str] = None


class CompetitiveIntelligenceCycleOut(BaseModel):
    started_at: str
    finished_at: str
    runtime_ms: int
    items_added: int
    items_updated: int
    errors: int
    results: List[Dict[str, Any]]


class MarketSupplySignalOut(BaseModel):
    category: str
    headline: str
    snippet: str
    city_state: Optional[str] = None
    market_key: Optional[str] = None
    project_name: Optional[str] = None
    service_lines: Optional[str] = None
    units_or_beds: Optional[int] = None
    expected_opening: Optional[str] = None
    occupancy_rate: Optional[str] = None
    occupancy_period: Optional[str] = None
    evidence_status: str
    nursing_relevance: str
    source_url: str
    source_domain: str
    first_observed_at: str


class MarketSupplyCycleOut(BaseModel):
    market_key: Optional[str] = None
    started_at: str
    finished_at: str
    runtime_ms: int
    items_added: int
    errors: int
    categories: List[Dict[str, Any]]


class MarketReportMetricOut(BaseModel):
    metric_key: str
    label: str
    unit: str
    scope: str
    status: str
    observations: List[Dict[str, Any]]
    reason: Optional[str] = None


class MarketReportOut(BaseModel):
    geography_key: str
    ranking_input: bool
    metrics: List[MarketReportMetricOut]


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
    questionnaire_state: Dict[str, Any]
    natural_language_query: Optional[str] = ""
    limit: int = 50


class PersonalDecisionReportRequestIn(BaseModel):
    # Omit questionnaire_state and pass case_token instead to request an updated
    # report for a case created by an earlier call -- the stored inputs are used and
    # the pipeline is re-run fresh against current facility data.
    questionnaire_state: Dict[str, Any] = Field(default_factory=dict)
    natural_language_query: Optional[str] = ""
    limit: int = 50
    decision_result: Optional[Dict[str, Any]] = None
    case_token: Optional[str] = None


class PatientNeedsProfileRequestIn(BaseModel):
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
    market_coverage_notice: Optional[str] = None
    availability_policy: str
    care_setting_policy: Dict[str, Any] = Field(default_factory=dict)
    decision_intelligence: Dict[str, Any] = Field(default_factory=dict)
    recommendation_audit_trace: Dict[str, Any] = Field(default_factory=dict)
    decision_pipeline_trace: Dict[str, Any] = Field(default_factory=dict)
    # Optional because an ordinary result carries no notice at all -- absent rather than
    # present-and-false, so a caller that forgets to check finds nothing to render. It must
    # be declared here regardless: a field the response model does not know about is
    # dropped in serialisation, and the notice would never reach the family it is for.
    degraded_result_notice: Optional[Dict[str, Any]] = None


class PersonalDecisionReportOut(BaseModel):
    case_token: str
    user_role: str
    report_ready: bool
    sections: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    omitted_sections: List[str] = Field(default_factory=list)


class PatientNeedsProfileOut(BaseModel):
    generated_from: Dict[str, Any]
    needs: List[Dict[str, Any]]
    need_tags: List[str]
    priority_parameter_ids: List[str]
    profile_key: Optional[str] = None
    location_city: Optional[str] = None
    natural_language_mapping: Dict[str, Any]
    decision_intelligence: Dict[str, Any] = Field(default_factory=dict)


class PatientComparisonContextOut(BaseModel):
    required_needs: List[Dict[str, Any]]
    high_priority_needs: List[Dict[str, Any]]
    preferences: List[Dict[str, Any]]
    comparison_parameter_ids: List[str]
    facilities: List[Dict[str, Any]]


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


class DeferredReportIn(BaseModel):
    email: str
    questionnaire: Dict[str, Any] = Field(default_factory=dict)
    query_text: str
    market: Optional[str] = None
    limit: int = 5
    degraded_reason: Optional[str] = None
    eligible_at_request: Optional[int] = None


class DeferredReportOut(BaseModel):
    request_id: int
    status: str
    created: bool


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


class ClaimSearchOut(BaseModel):
    facility_id: int
    cms_id: str
    name: str
    address: str
    city: str
    state: str
    zip_code: str
    beds: Optional[int] = None
    overall_rating: Optional[int] = None
    already_claimed: bool


class CapabilitySaveIn(BaseModel):
    user_id: int
    answers: Dict[str, str]
    ip_address: Optional[str] = None


class CapabilitySaveOut(BaseModel):
    updated: int
    unchanged: int
    completeness: Dict[str, object]


class PhotoAddIn(BaseModel):
    user_id: int
    url: str
    category: str = "general"
    caption: Optional[str] = None
    ip_address: Optional[str] = None


class PhotoRemoveIn(BaseModel):
    user_id: int
    ip_address: Optional[str] = None


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


class AgentKnowledgeRefreshAgentOut(BaseModel):
    agent_id: str
    agent_name: str
    refresh_started_at: Optional[str] = None
    refresh_completed_at: Optional[str] = None
    success: bool
    status: str
    failing_stage: Optional[str] = None
    exception_type: Optional[str] = None
    exact_error_message: Optional[str] = None
    stack_trace_location: Optional[str] = None
    input_source: Optional[str] = None
    output_target: Optional[str] = None
    retryable: bool = False
    automatic_fix_allowed: bool = False
    recommended_action: Optional[str] = None
    incident_id: Optional[int] = None


class AgentKnowledgeRefreshOut(BaseModel):
    attempted: int
    refreshed: int
    failures: int
    skipped: int = 0
    retried: int = 0
    incidents: int = 0
    agents: List[AgentKnowledgeRefreshAgentOut] = Field(default_factory=list)


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


def require_admin_token(x_admin_token: Optional[str] = Header(default=None)) -> None:
    """Gate for staff-only actions with real consequences (sending a real email to a
    real facility, viewing the internal outreach queue). There is no broader
    authentication system in this codebase yet -- this is a minimal, fail-closed
    stopgap: if OPTIME_ADMIN_TOKEN isn't configured, every request is denied rather
    than silently left open, unlike everything else in this API today.
    """
    expected = os.getenv("OPTIME_ADMIN_TOKEN", "").strip()
    if not expected or not x_admin_token or x_admin_token != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid admin token")


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


def _to_agent_knowledge_report_summary(row: AgentKnowמ5򚤺{-Ωܪםٝ\ۈ٘ۛ[Y[٘][ۑݘ\ِڙXړݝ
٘ۛ[Y[٘][ۗڙ^O\^[ؙܙXۛ[Y[٘][ۗڙ^KXڜڛۜϙXڜڛۜʂИ\ܛܝ
˚[X[˚[ݙ[YؙٛHˈٜܛۜٗۛٙ[R[X[қݙ[YؙٛSݝ
B؜ޛ؈YȘܙX]Wڝ[X[ך[ݙ[YؙٛJ^[ؙȒ[X[қݙ[YؙٛR[ˈΈٜܚ[ۈH\[ٜʙٝ٘ʊNYȘۚ\ۜ[ۘ[
؛YNȓܝ[ۘ[ٛ؝JHOȓܝ[ۘ[ٛ؝NYȝ؛YH\ȓَۛٝ\ۈۛقȈٝ\ۈۚ\̗̌
؛YJB٘ۜوH[X[қݙ[YؙٛT؛ܙJȈٜڙ[ݗڙ^O\^[ؙܙ\ڙ[ݗڙ^KȈٛ][ۜښ\\^[ؙܙ[][ۜښ\ȈYٜٗ۝\\^[ؙؙٜٗ۝\Ȉۘژ[ܜۙڛWܘُۜXۚ\̗̌
^[ؙܛؚX[ܜۙڛWܘۜيKȈ؛Z[Wܝ\ܝܘُۜXۚ\̗̌
^[ؙ٘[Z[Wܝ\ܝܘۜيKȈݛ\؛ۘ]ڗܘُۜXۚ\̗̌
^[ؙ؝[\؛ۘ]ڗܘۜيKȈۙ[[ٜܗܚ\ڗܘُۜXۚ\̗̌
^[ؙۛۙ[[ٜܗܚ\ڗܘۜيKȈ؛ܚ][ۗܚ\ڗܘُۜXۚ\̗̌
^[ؙݜ؛ܚ][ۗܚ\ڗܘۜيKȈݝ\ؘٗ\ٗܘُۜXۚ\̗̌
^[ؙٝ]\ؘٗ\ٗܘۜيKȈۘژ[ٚ]ܘُۜXۚ\ۜ[ۘ[
^[ؙܛؚX[ٚ]ܘۜيKȈ؛Z[Wٚ]ܘُۜXۚ\ۜ[ۘ[
^[ؙ٘[Z[Wٚ]ܘۜيKȈ[ٝXYٗۘ]ڗܘُۜXۚ\ۜ[ۘ[
^[ؙۘ[ٝXYٗۘ]ڗܘۜيKȈٛYڛݜיڝܘُۜXۚ\ۜ[ۘ[
^[ؙܙ[YڛݜיڝܘۜيKȈ[ٝXYٗٚ]ܘُۜXۚ\ۜ[ۘ[
^[ؙۘ[ٝXYٗٚ]ܘۜيKȈݛ\؛ٚ]ܘُۜXۚ\ۜ[ۘ[
^[ؙ؝[\؛ٚ]ܘۜيKȈۛٗٚ]ܘُۜXۚ\ۜ[ۘ[
^[ؙٛۙٚ]ܘۜيKȈ؛Z[Wٛ٘YٛY[ݗܘُۜXۚ\ۜ[ۘ[
^[ؙ٘[Z[Wٛ٘YٛY[ݗܘۜيKȈۛ[][ڝWܝ[WܘُۜXۚ\ۜ[ۘ[
^[ؙ؛ۛ][ڝWܝ[WܘۜيKȈ[ٙ\[ٙ[ؙWٚ]ܘُۜXۚ\ۜ[ۘ[
^[ؙڛٙ\[ٙ[ؙWٚ]ܘۜيKȈ؛ܚ][ۗܝXؙ\ܗܜؘۘڛ]OXۚ\ۜ[ۘ[
^[ؙݜ؛ܚ][ۗܝXؙ\ܗܜؘۘڛ]JKȈY]Y]WڜۛϜ^[ؙۙ]Y]Wڜۛ˂Ȉ
BȈ˘Y
٘ۜيBȈ˘ۛ[Z]

BȈ˜ٙܙ\ڊ٘ۜيBȈٝ\ۈ[X[қݙ[YؙٛSݝۛٙ[ݘ[Y]J٘ۜيBИ\ܛܝ
˚[X[˚[ݙ[YؙٛKؙ\]ً\ٜܛۜوˈٜܛۜٗۛٙ[PY\]ٔ]Y\ݚ[۔ٜܛۜٓݝ
BٙYȘܙX]Wؙ\]ٗܙ\ܛۜي^[ؙȐY\]ٔ]Y\ݚ[۔ٜܛْۜ[ˈΈٜܚ[ۈH\[ٜʙٝ٘ʊN٘ۜوHY\]ٔ]Y\ݚ[۔ٜܛۜيȈٜڙ[ݗڙ^O\^[ؙܙ\ڙ[ݗڙ^KȈ]Y\ݚ[ۗڙ^O\^[ؙܝY\ݚ[ۗڙ^KȈ[ܝٜϜ^[ؙ؛ܝٜ˂Ȉڙۘ[ݞ\O\^[ؙܚYۘ[ݞ\KȈڙۘ[ڜۛϜ^[ؙܚYۘ[ڜۛ˂ȈٚYڝךܛۏ\^[ؙݙZYڝךܛۋȈ[\Xݗٞ[؝[ۏ\^[ؙڛ\Xݗٞ[؝[ۋȈ[ٛיؚ[ל؛ܙO[X^
̋Z[ʌL̋^[ؙڛٛיؚ[ל؛ܙJJKȈ
BȈ˘Y
٘ۜيBȈ˘ۛ[Z]

BȈ˜ٙܙ\ڊ٘ۜيBȈٝ\ۈY\]ٔ]Y\ݚ[۔ٜܛۜٓݝۛٙ[ݘ[Y]J٘ۜيBИ\ܛܝ
˜ٜڙ[݋[ݝۛY\ȋٜܛۜٗۛٙ[Tٜڙ[ݓݝۛYSݝ
B؜ޛ؈YȘܙX]Wܙ\ڙ[ݗ۝]ۛYJ^[ؙȔٜڙ[ݓݝۛYR[ˈΈٜܚ[ۈH\[ٜʙٝ٘ʊNYȜ^[ؙڝ[X[ך[ݙ[YؙٛWܘۜٗڙ\ț۝َۛ؛ܙWܙXۜوH˜]Y\ފ[X[қݙ[YؙٛT؛ܙJKٚ[\ʒ[X[қݙ[YؙٛT؛ܙKڙOH^[ؙڝ[X[ך[ݙ[YؙٛWܘۜٗڙ
Kٚ\ܝ

BȈYț۝؛ܙWܙXَۜؚ\و^ٜ[ۊݘ]\טۙOM]Z[Hҝ[X[Ț[ݙ[YؙٛH؛ܙH۝۝[وʂYȜ^[ؙ٘Xڛ]Wڙ\ț۝َۛؘڛ]HH˜]Y\ފؘڛ]JKٚ[\ʑؘڛ]KڙOH^[ؙ٘Xڛ]Wڙ
Kٚ\ܝ

BȈYț۝ؘڛ]Nؚ\و^ٜ[ۊݘ]\טۙOM]Z[HјXڛ]H۝۝[وʂ٘ۜوHٜڙ[ݓݝۛYJȈٜڙ[ݗڙ^O\^[ؙܙ\ڙ[ݗڙ^KȈ[X[ך[ݙ[YؙٛWܘۜٗڙ\^[ؙڝ[X[ך[ݙ[YؙٛWܘۜٗڙȈؘڛ]Wڙ\^[ؙ٘Xڛ]WڙȈݘؙ\ܙݛؙݜݛY[ݏLHYȜ^[ؙܝXؙ\ܙݛؙݜݛY[݈[وȈۙ[[ٜܗٝٛݏLHYȜ^[ؙۛۙ[[ٜܗ݈ٝٛ[وȈٛؘ]Yݚ][׌͛OLHYȜ^[ؙܙ[ؘ]Yݚ][׌͛H[وȈ۝\Ϝ^[ؙۛݙ\˂Ȉ
BȈ˘Y
٘ۜيBȈ˘ۛ[Z]

BȈ˜ٙܙ\ڊ٘ۜيBٝ\ۈٜڙ[ݓݝۛYSݝ
ȈY\ً٘ۜڙȈٜڙ[ݗڙ^O\ً٘ۜܙ\ڙ[ݗڙ^KȈ[X[ך[ݙ[YؙٛWܘۜٗڙ\ً٘ۜڝ[X[ך[ݙ[YؙٛWܘۜٗڙȈؘڛ]Wڙ\ً٘ۜ٘Xڛ]WڙȈݘؙ\ܙݛؙݜݛY[ݏXۛۊً٘ۜܝXؙ\ܙݛؙݜݛY[݊KȈۙ[[ٜܗٝٛݏXۛۊً٘ۜۛۙ[[ٜܗٝٛ݊KȈٛؘ]Yݚ][׌͛OXۛۊً٘ۜܙ[ؘ]Yݚ][׌͛JKȈ۝\Ϝً٘ۜۛݙ\˂Ȉ
BИ\ٙ]
˝؛Y][ۋYٙYؘڈˈٜܛۜٗۛٙ[U؛Y][ۑٙYؘړݝ
B؜ޛ؈Yșٝݘ[Y][ۗٙYYؘڊΈٜܚ[ۈH\[ٜʙٝ٘ʊNݝۛY\ט۝[݈H˜]Y\ފݛ؋؛ݛ݊ٜڙ[ݓݝۛYKڙ
JKܘ؛\ʊH܈ȈYțݝۛY\ט۝[݈OHٝ\ۈ؛Y][ۑٙYؘړݝ
ȈݝۛY\ט۝[ݏLȈYݜݛY[ݗܝXؙ\ܗܘ]OL̋Ȉۙ[[ٜܗٝٛݗܘ]OL̋Ȉٛؘ][ۗܘ]W̍OL̋Ȉ]ؙٜٗܘٜۜיۜלݘؙ\ܙݛؙݜݛY[ݏ^ܛؚX[ܜۙڛWܘۜوΈ̋Ȉ٘[Z[Wܝ\ܝܘۜوΈ̋Ȉ؝[\؛ۘ]ڗܘۜوΈ̋Ȉۛۙ[[ٜܗܚ\ڗܘۜوΈ̋Ȉݜ؛ܚ][ۗܚ\ڗܘۜوΈ̋Ȉٝ]\ؘٗ\ٗܘۜوΈ̋ȈKȈ]ؙٜٗܘٜۜיۜם[ܝXؙ\ܙݛؙݜݛY[ݏ^ܛؚX[ܜۙڛWܘۜوΈ̋Ȉ٘[Z[Wܝ\ܝܘۜوΈ̋Ȉ؝[\؛ۘ]ڗܘۜوΈ̋Ȉۛۙ[[ٜܗܚ\ڗܘۜوΈ̋Ȉݜ؛ܚ][ۗܚ\ڗܘۜوΈ̋Ȉٝ]\ؘٗ\ٗܘۜوΈ̋ȈKȈ
Bݘؙ\ܗ؛ݛ݈H˜]Y\ފݛ؋ܝ[Jٜڙ[ݓݝۛYKܝXؙ\ܙݛؙݜݛY[݊JKܘ؛\ʊH܈Ȉۙ[[ٜܗ؛ݛ݈H˜]Y\ފݛ؋ܝ[Jٜڙ[ݓݝۛYKۛۙ[[ٜܗٝٛ݊JKܘ؛\ʊH܈Ȉٛؘ][ۗ؛ݛ݈H˜]Y\ފݛ؋ܝ[Jٜڙ[ݓݝۛYKܙ[ؘ]Yݚ][׌͛JJKܘ؛\ʊH܈ٝ\ۈ؛Y][ۑٙYؘړݝ
ȈݝۛY\ט۝[ݏZ[݊ݝۛY\ט۝[݊KȈYݜݛY[ݗܝXؙ\ܗܘ]O\۝[ي
ۛ؝
ݘؙ\ܗ؛ݛ݊Hșۛ؝
ݝۛY\ט۝[݊JH
ȌLʋȈۙ[[ٜܗٝٛݗܘ]O\۝[ي
ۛ؝
ۙ[[ٜܗ؛ݛ݊Hșۛ؝
ݝۛY\ט۝[݊JH
ȌLʋȈٛؘ][ۗܘ]W̍O\۝[ي
ۛ؝
ٛؘ][ۗ؛ݛ݊Hșۛ؝
ݝۛY\ט۝[݊JH
ȌLʋȈ]ؙٜٗܘٜۜיۜלݘؙ\ܙݛؙݜݛY[ݏWٜ۝\؝ؙٜٗܘٜۜʙˈJKȈ]ؙٜٗܘٜۜיۜם[ܝXؙ\ܙݛؙݜݛY[ݏWٜ۝\؝ؙٜٗܘٜۜʙˈ
KȈ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKؘݚ]ڝY\˚[\ܝˈٜܛۜٗۛٙ[PXݚ]ڝR[\ܝݝ
B؜ޛ؈YȚ[\ܝ٘Xڛ]Wؘݚ]ڝY\ʂȈؘڛ]WڙȚ[݋Ȉ^[ؙȐXݚ]ڝR[\ܝ[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎؘڛ]HH˜]Y\ފؘڛ]JKٚ[\ʑؘڛ]KڙOHؘڛ]Wڙ
Kٚ\ܝ

BȈYț۝ؘڛ]Nؚ\و^ٜ[ۊݘ]\טۙOM]Z[HјXڛ]H۝۝[وʂ۝\ؙWݞ\HH
^[ؙܛݜؙWݞ\H܈ȊKܝڜ

Kۛݙ\ʊBȈYȜ۝\ؙWݞ\H۝[ȞșۛٛWؘ[[٘\ȋژ܈ˈ؜݈ˈܙȟNؚ\و^ٜ[ۊݘ]\טۙOM]Z[HܛݜؙWݞ\H]\݈وۙHَșۛٛWؘ[[٘\ˈX܋ܝˈȊBގٜݛH[\ܝؘݚ]ڝWؘ]Yۜڙ\ʂȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ۝\ؙWݞ\O\۝\ؙWݞ\KȈۛݙ[ݏ\^[ؙ؛۝[݋Ȉ\]Y؞WݜٜךY\^[ؙݜ]Y؞WݜٜךYȈ
BȈ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈXݚ]ڝR[\ܝݝ
Ȉؘڛ]WڙZ[݊ٜݛșؘڛ]Wڙ׊KȈ۝\ؙWݞ\O\ݜʜٜݛȜ۝\ؙWݞ\H׊KȈ[\ܝY؝\ݜʜٜݛȚ[\ܝY؝׊KȈ؝Yۜڙ\ϖИݚ]ڝP؝Yۜޓݝ

ʚ][JHۜȚ][H[ȜٜݛȘ؝Yۜڙ\ȗWKȈڝؘޗܛۚXޏ\ݜʜٜݛȜڝؘޗܛۚXވ׊KȈ
BИ\ٙ]
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKؘݚ]ڝY\˘؝Yۜڙ\ȋٜܛۜٗۛٙ[S\ݖИݚ]ڝP؝YۜޓݝJB؜ޛ؈Yșٝ٘Xڛ]Wؘݚ]ڝWؘ]Yۜڙ\ʂȈؘڛ]WڙȚ[݋ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎؘڛ]HH˜]Y\ފؘڛ]JKٚ[\ʑؘڛ]KڙOHؘڛ]Wڙ
Kٚ\ܝ

BȈYț۝ؘڛ]Nؚ\و^ٜ[ۊݘ]\טۙOM]Z[HјXڛ]H۝۝[وʂٝ\ۈИݚ]ڝP؝Yۜޓݝ

ʚ][JHۜȚ][H[șٝܝXۚXטXݚ]ڝWؘ]Yۜڙ\ʙˈؘڛ]Wڙ
WBИ\ٙ]
˜۝ڙ\˘Xݚ]ڝKZ[ݙ[YؙٛKܛۚXވʂ؜ޛ؈Yșٝؘݚ]ڝWڛݙ[YؙٛWܛۚXފ
Nٝ\ۈܝ\ܝYڛ\ܝȎȖșۛٛWؘ[[٘\ȋژ܈ˈ؜݈ˈܙȗKȈܝܙYܝXۚXט؝Yۜڙ\ȎȐSՑQАՒUҕWАUQӔґT˂ȈܜڝؘވΈўX݈ؚY[\Ș\وٜٝș^ܙYXۚX۞NțۛH؝Yۜދ[]ٛ]ؚ[Xڛ]H[وۛٚY[ؙH\وٝ\ۙYȋȈBИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKݙ\ڙژ؝[ۋܙ\ܚ\݈ˈٜܛۜٗۛٙ[T۝ڙ\ԙ\ܚ\ݓݝ
B؜ޛ؈YȜ\ܚ\ݗܜ۝ڙ\םٜڙژ؝[ۗ؛ܝٜ܊Ȉؘڛ]WڙȚ[݋Ȉ^[ؙȔ۝ڙ\ԙ\ܚ\ݒ[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎؘڛ]HH˜]Y\ފؘڛ]JKٚ[\ʑؘڛ]KڙOHؘڛ]Wڙ
Kٚ\ܝ

BȈYț۝ؘڛ]Nؚ\و^ٜ[ۊݘ]\טۙOM]Z[HјXڛ]H۝۝[وʂٜݛH\Wܜ۝ڙ\םٜڙژ؝[ۗ؛ܝٜ܊Ȉϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ[ܝٜ܏Vؘ\Xڛ]Wڙ^HΈ][Kؘ\Xڛ]Wڙ^KȈݘ[YHΈ][Kݘ[YKȈܛݜؙHΈ][KܛݜؙKȈBȈۜȚ][H[Ȝ^[ؙ؛ܝٜ܂ȈKȈٜڙڙY؞WݜٜךY\^[ؙݙ\ڙڙY؞WݜٜךYȈٜڙژ؝[ۗۙ]ُ\^[ؙݙ\ڙژ؝[ۗۙ]ًȈٜ]Y\ݗܝXڙXݏ\^[ؙܙ\]Y\ݗܝXڙX݋Ȉٜ]Y\ݗ؛ٞO\^[ؙܙ\]Y\ݗ؛ٞKȈ
Bٝ\ۈ۝ڙ\ԙ\ܚ\ݓݝ
Ȉؘڛ]WڙZ[݊ٜݛșؘڛ]Wڙ׊KȈٜ]Y\ݗڙZ[݊ٜݛȜٜ]Y\ݗڙ׊KȈ\ܚ\ݙY؛ܝٜ܏Z[݊ٜݛȜ\ܚ\ݙY؛ܝٜ܈׊KȈۛٛXݗܙXٜۜϚ[݊ٜݛȘۛٛXݗܙXٜۜȗJKȈ
BИ\ٙ]
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKۙ[[ܞHˈٜܛۜٗۛٙ[Qؘڛ]SY[[ܞSݝ
B؜ޛ؈Yșٝ٘Xڛ]Wۙ[[ܞJȈؘڛ]WڙȚ[݋ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎؘڛ]HH˜]Y\ފؘڛ]JKٚ[\ʑؘڛ]KڙOHؘڛ]Wڙ
Kٚ\ܝ

BȈYț۝ؘڛ]Nؚ\و^ٜ[ۊݘ]\טۙOM]Z[HјXڛ]H۝۝[وʂY[[ܞHHؘڛ]Wۙ[[ܞW۝ٜۘ^Jˈؘڛ]Wڙ
BȈٝ\ۈؘڛ]SY[[ܞSݝ
Ȉؘڛ]WڙZ[݊Y[[ܞVșؘڛ]Wڙ׊KȈݙ\؛؛ۙڙ[ؙOYۛ؝
Y[[ܞVțݙ\؛؛ۙڙ[ؙH׊KȈ؜Xڛ]Y\ϖә[[ܞP؜Xڛ]Sݝ

ʚ][JHۜȚ][H[țY[[ܞVȘ؜Xڛ]Y\ȗWKȈ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]KܙYڜݙ\˜ݘ\݈ˈٜܛۜٗۛٙ[RY[ݚ]Tٙڜݜ؝[۔ݘ\ݓݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]WܙYڜݙ\לݘ\݊Ȉؘڛ]WڙȚ[݋Ȉ^[ؙȒY[ݚ]Tٙڜݜ؝[۔ݘ\ݒ[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛHݘ\ݗٛXZ[ݙ\ڙژ؝[ۊȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ[XZ[\^[ؙٛXZ[Ȉݛۘ[YO\^[ؙٝ[ۘ[YKȈۛO\^[ؙܛۙKȈ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈY[ݚ]Tٙڜݜ؝[۔ݘ\ݓݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]KܙYڜݙ\˝ٜڙވˈٜܛۜٗۛٙ[RY[ݚ]Uٜڙژ؝[ېۛ\]Sݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]WܙYڜݙ\םٜڙފȈؘڛ]WڙȚ[݋Ȉ^[ؙȒY[ݚ]Uٜڙژ؝[ېۛ\]R[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛHۛ\]WٛXZ[ݙ\ڙژ؝[ۊȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ[XZ[\^[ؙٛXZ[ȈۙO\^[ؙ؛ٙKȈ
BȈ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈY[ݚ]Uٜڙژ؝[ېۛ\]Sݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]KۚXٛܙKݘ[Y]Hˈٜܛۜٗۛٙ[SXٛܙU؛Y][ۓݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]WۚXٛܙWݘ[Y]JȈؘڛ]WڙȚ[݋Ȉ^[ؙȓXٛܙU؛Y][ے[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛH؛Y]WۚXٛܙW۝ۙ\ܚ\
Ȉϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈۜל۝ڙ\ךY\^[ؙ؛\ל۝ڙ\ךYȈZؗۚXٛܙW۝[XٜϜ^[ؙؚؗۚXٛܙW۝[Xٜ˂ȈYYX؜ٗܜ۝ڙ\כݛXٜϜ^[ؙۙYX؜ٗܜ۝ڙ\כݛXٜ˂ȈY؛ۘ[YO\^[ؙۙY؛ۘ[YKȈY؛ؙٜ܏\^[ؙۙY؛ؙٜ܋ȈۘZ[Ϝ^[ؙٛۘZ[˂Ȉ
BȈ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈXٛܙU؛Y][ۓݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˚Y[ݚ]Kؘؙ\܋XڙXڈˈٜܛۜٗۛٙ[PXؙ\ܐڙXړݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]Wؘؙ\ܗؚXڊ^[ؙȐXؙ\ܐڙXڒ[ʎٝ\ۈXؙ\ܐڙXړݝ
[ݙY\ۛWؘ[יY]ؘ]Yۜފ^[ؙܛۙK^[ؙؘ]YۜފJBИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]KٚY[]\]Hˈٜܛۜٗۛٙ[Qڙ[\]Sݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]WٚY[ݜ]JȈؘڛ]WڙȚ[݋Ȉ^[ؙȑڙ[\]R[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛH\W٘Xڛ]WٚY[ݜ]JȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ\ٜךY\^[ؙݜٜךYȈڙ[ۘ[YO\^[ؙٚY[ۘ[YKȈٝם؛YO\^[ؙۙ]ם؛YKȈ؝Yۜޏ\^[ؙؘ]YۜދȈ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈڙ[\]Sݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]K؝Y]ޘ]Y]ڙKܙ]ٜ݈ˈٜܛۜٗۛٙ[Tٜٝݐ]Y]ݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]Wܙ]ٜݗ؝Y]
Ȉؘڛ]WڙȚ[݋Ȉ]Y]ڙȚ[݋Ȉ^[ؙȔٜٝݐ]Y][˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛHٜٝݗ؝Y]ؚ[ٙJȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ]Y]ڙX]Y]ڙȈٜٝݙY؞WݜٜךY\^[ؙܙ]ٜݙY؞WݜٜךYȈ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈٜٝݐ]Y]ݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]KܝYًڛݚ]Hˈٜܛۜٗۛٙ[RY[ݚ]Tٙڜݜ؝[۔ݘ\ݓݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]WܝYٗڛݚ]JȈؘڛ]WڙȚ[݋Ȉ^[ؙȔݘYْ[ݚ]R[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛH[ݚ]WܝYٗۙ[XٜʂȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ[ݚ]\ם\ٜךY\^[ؙڛݚ]\ם\ٜךYȈ[XZ[\^[ؙٛXZ[Ȉݛۘ[YO\^[ؙٝ[ۘ[YKȈۛO\^[ؙܛۙKȈ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈY[ݚ]Tٙڜݜ؝[۔ݘ\ݓݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKڙ[ݚ]KܛۙKؚ[ٙHˈٜܛۜٗۛٙ[TۛPژ[ٙSݝ
B؜ޛ؈YȜ۝ڙ\ךY[ݚ]WܛۙWؚ[ٙJȈؘڛ]WڙȚ[݋Ȉ^[ؙȔۛPژ[ٙR[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛHٜ]Y\ݗܛۙWؚ[ٙJȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈXݛܗݜٜךY\^[ؙؘݛܗݜٜךYȈ\ٙ]ݜٜךY\^[ؙݘ\ٙ]ݜٜךYȈٝלۛO\^[ؙۙ]לۛKȈ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂ٝ\ۈۛPژ[ٙSݝ

ʜٜݛ
BИ\ٙ]
˜۝ڙ\˙ؘڛ]Y\˜٘\ؚˈٜܛۜٗۛٙ[S\ݖЛZ[T٘\ؚݝJB؜ޛ؈YȜ۝ڙ\יؘڛ]WܙX\ؚ
ȈNȜݜ˂Ȉݘ]Nȓܝ[ۘ[ܝ׈HًۛȈڝNȓܝ[ۘ[ܝ׈HًۛȈ[Z]Ț[݈H͋ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎٝ\ۈЛZ[T٘\ؚݝ

ʜ۝ʈۜȜ۝Ț[Ȝ٘\ؚ؛Z[XXۙW٘Xڛ]Y\ʙˈKݘ]KڝK[Z]
WBИ\ٙ]
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKܜۙڛHʂ؜ޛ؈YȜ۝ڙ\יؘڛ]WܜۙڛJؘڛ]WڙȚ[݋Έٜܚ[ۈH\[ٜʙٝ٘ʊNގٝ\ۈؘڛ]WܜۙڛWܛ؜ڛ݊ˈؘڛ]Wڙ
BȈ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂И\ܝ]
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKؘ\Xڛ]Y\ȋٜܛۜٗۛٙ[P؜Xڛ]T؝ٓݝ
B؜ޛ؈YȜ۝ڙ\יؘڛ]Wܘ]ؘٗ\Xڛ]Y\ʂȈؘڛ]WڙȚ[݋Ȉ^[ؙȐ؜Xڛ]T؝ْ[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٜݛH؝ؘٗ\Xڛ]Y\ʂȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ\ٜךY\^[ؙݜٜךYȈ[ܝٜ܏\^[ؙ؛ܝٜ܋Ȉ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉٝ\ۈ؜Xڛ]T؝ٓݝ

ʜٜݛ
BИ\ܛܝ
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKܚݛ܈ʂ؜ޛ؈YȜ۝ڙ\יؘڛ]WؙܚݛʂȈؘڛ]WڙȚ[݋Ȉ^[ؙȔݛЙ[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٝ\ۈYܚݛʂȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ\ٜךY\^[ؙݜٜךYȈ؝Yۜޏ\^[ؙؘ]YۜދȈ\ۏ\^[ؙݜۋȈ؜[ۏ\^[ؙؘ\[ۋȈ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂И\ٙ[]J˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙKܚݛ܋ޜݛךYHʂ؜ޛ؈YȜ۝ڙ\יؘڛ]Wܙ[[ݙWܚݛʂȈؘڛ]WڙȚ[݋ȈݛךYȚ[݋Ȉ^[ؙȔݛԙ[[ݙR[˂ȈΈٜܚ[ۈH\[ٜʙٝ٘ʋʎގٝ\ۈXXݚ]؝WܚݛʂȈϙ˂Ȉؘڛ]WڙYؘڛ]WڙȈ\ٜךY\^[ؙݜٜךYȈݛךY\ݛךYȈ\ؙٜ܏\^[ؙڜؙٜ܋Ȉ
BȈ^ٜ\ۚ\ܚ[ۑ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOMˈ]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂Ȉ^ٜ؛YQ\ܛ܈\ș\ܛ܎ؚ\و^ٜ[ۊݘ]\טۙOM]Z[\ݜʙ\ܛ܊JHܛۈ\ܛ܂И\ٙ]
˜۝ڙ\˙ؘڛ]Y\˞٘Xڛ]WڙK؛ۜ][ٜ܈ʂ؜ޛ؈YȜ۝ڙ\יؘڛ]W؛ۜ][ٜ܊ؘڛ]WڙȚ[݋Έٜܚ[ۈH\[ٜʙٝ٘ʊNٝ\ۈ٘ۛ\]W؛ۜ][ٜ܊ˈؘڛ]Wڙ
BИ\ܛܝ
˜۝ڙ\˚Y[ݚ]Kܙ]ٜڙژ؝[ۋܝ[ȊB؜ޛ؈YȜ۝ڙ\ךY[ݚ]Wܙ]ٜڙژ؝[ۗܝ[ʙΈٜܚ[ۈH\[ٜʙٝ٘ʊNٝ\ۈݛט[۝X[ܙ]ٜڙژ؝[ۊʂИ\ٙ]
˙^Xݝ]ً\ٜܝۘ]\݈ʂ؜ޛ؈Yș^Xݝ]ٗܙ\ܝۘ]\݊
N]\݈Hٝۘ]\ݗٞXݝ]ٗܙ\ܝ

BȈYț۝]\ݎؚ\و^ٜ[ۊݘ]\טۙOM]Z[Hӛș^Xݝ]وٜܝٜٛ؝YY]ʂȈٝ\ۈ]\݂И\ٙ]
˙^Xݝ]ً\ٜܝۘ]\݋ٝ[ʂ؜ޛ؈Yș^Xݝ]ٗܙ\ܝۘ]\ݗٝ[

N^[ؙHٝٞXݝ]ٗܙ\ܝܘ^[ؙ

BȈYț۝^[ؙؚ\و^ٜ[ۊݘ]\טۙOM]Z[Hӛș^Xݝ]وٜܝٜٛ؝YY]ʂȈٝ\ۈ^[ؙИ\ٙ]
˙^Xݝ]ً\ٜܝ؞KZYޜٜܝڙHʂ؜ޛ؈Yș^Xݝ]ٗܙ\ܝ؞Wڙ
ٜܝڙȜݜʎ^[ؙHٝٞXݝ]ٗܙ\ܝܘ^[ؙ
ٜܝڙ\ٜܝڙ
BȈYț۝^[ؙؚ\و^ٜ[ۊݘ]\טۙOM]Z[HўXݝ]وٜܝ۝۝[وʂȈٝ\ۈ^[ؙИ\ٙ]
˙^Xݝ]ً\ٜܝښ\ݛܞHʂ؜ޛ؈Yș^Xݝ]ٗܙ\ܝښ\ݛܞJ[Z]Ț[݈H]Y\ފY؝[L̋ُLKOL͍JJNٝ\ۈȜٜܝȎșٝٞXݝ]ٗܙ\ܝښ\ݛܞJ[Z][[Z]
_BИ\ٙ]
˙^Xݝ]ً\ٜܝ؛ۜ\وʂ؜ޛ؈Yș^Xݝ]ٗܙ\ܝ؛ۜ\ي
Nٝ\ۈۛ\\ٗۘ]\ݗݜלٝڛݜʊBИ\ٙ]
˙]ڙ[ؙKݜؘ٘Xڛ]K؝Y]ʂ؜ޛ؈Yș]ڙ[ؙWݜؘ٘Xڛ]W؝Y]
Έٜܚ[ۈH\[ٜʙٝ٘ʊNٝ\ۈ]Y]ݜؘ٘Xڛ]JʂИ\ٙ]
˙]ڙ[ؙK٘Xڛ]Y\˞٘Xڛ]WڙKۘ]\ژ[XۘZ[\ȊB؜ޛ؈Yș]ڙ[ؙW٘Xڛ]Wۘ]\ژ[؛Z[\ʙؘڛ]WڙȚ[݋Έٜܚ[ۈH\[ٜʙٝ٘ʊN^[ؙHؘڛ]Wۘ]\ژ[؛Z[Wݜؘيˈؘڛ]Wڙ
BȈYȜ^[ؙٙ]
ٜܛ܈ʈOH٘Xڛ]Wۛݗٛݛو΂Ȉؚ\و^ٜ[ۊݘ]\טۙOM]Z[HјXڛ]H۝۝[وʂȈٝ\ۈ^[ؙИ\ٙ]
˙]ڙ[ؙKܙXۛ[Y[٘][ۜ˞ܙXۛ[Y[٘][ۗڙ^_Kܘًۜ]ؘوʂ؜ޛ؈Yș]ڙ[ؙWܙXۛ[Y[٘][ۗܘۜٗݜؘي٘ۛ[Y[٘][ۗڙ^NȜݜˈΈٜܚ[ۈH\[ٜʙٝ٘ʊNٝ\ۈ٘ۛ[Y[٘][ۗܘۜٗݜؘيˈ٘ۛ[Y[٘][ۗڙ^JB