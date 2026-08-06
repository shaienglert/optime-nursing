from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = REPO_ROOT / "database" / "platform_registry.json"
REPORT_MD_PATH = REPO_ROOT / "reports" / "PLATFORM_REGISTRY.md"
REPORT_JSON_PATH = REPO_ROOT / "reports" / "PLATFORM_REGISTRY.json"

STATUS_VALUES = {
    "NOT_STARTED",
    "IN_PROGRESS",
    "IMPLEMENTED",
    "VERIFIED",
    "PRODUCTION_READY",
    "BLOCKED",
    "FROZEN",
}

BLOCKER_TYPES = {"CODE", "DATA", "CONFIGURATION", "LEGAL", "BUSINESS", "ARCHITECTURE"}

CLAIM_VERIFICATION_VALUES = {
    "UNVERIFIED",
    "PARTIALLY_VERIFIED",
    "VERIFIED",
    "STALE",
    "REGRESSION_DETECTED",
    "OWNER_DECLARED",
    "BLOCKED",
    "UNKNOWN",
}

CLAIM_SOURCE_TYPES = {
    "REPOSITORY_DERIVED",
    "RUNTIME_PROVEN",
    "TEST_PROVEN",
    "OWNER_DECLARED",
    "GENERATED_FROM_VERIFIED_INPUTS",
    "INFERRED",
    "UNKNOWN",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _blocked_issue(*, exact_blocker: str, blocker_owner: str, blocker_evidence: List[str], blocker_type: str) -> Dict[str, object]:
    return {
        "exact_blocker": exact_blocker,
        "blocker_owner": blocker_owner,
        "blocker_evidence": blocker_evidence,
        "blocker_type": blocker_type if blocker_type in BLOCKER_TYPES else "ARCHITECTURE",
    }


def _dedupe_str_list(values: Optional[List[str]]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _cap(
    capability_id: str,
    name: str,
    owner: str,
    purpose: str,
    implementation_status: str,
    verification_status: str,
    production_readiness: str,
    dependencies: List[str],
    downstream_consumers: List[str],
    evidence: List[str],
    implementation_files: List[str],
    test_files: List[str],
    reports: List[str],
    next_action: str,
    blocking_issues: Optional[List[Dict[str, object]]] = None,
    *,
    required_build_dependencies: Optional[List[str]] = None,
    required_runtime_dependencies: Optional[List[str]] = None,
    evidence_dependencies: Optional[List[str]] = None,
    optional_consumers: Optional[List[str]] = None,
    monitoring_relationships: Optional[List[str]] = None,
    documentation_references: Optional[List[str]] = None,
    canonical_responsibility: Optional[str] = None,
) -> Dict[str, object]:
    if implementation_status not in STATUS_VALUES:
        raise ValueError(f"Unsupported implementation status {implementation_status!r} for {capability_id}")
    if verification_status not in STATUS_VALUES:
        raise ValueError(f"Unsupported verification status {verification_status!r} for {capability_id}")
    if production_readiness not in STATUS_VALUES:
        raise ValueError(f"Unsupported production readiness {production_readiness!r} for {capability_id}")
    typed_build_dependencies = _dedupe_str_list(required_build_dependencies if required_build_dependencies is not None else dependencies)
    typed_runtime_dependencies = _dedupe_str_list(required_runtime_dependencies)
    typed_evidence_dependencies = _dedupe_str_list(evidence_dependencies)
    typed_optional_consumers = _dedupe_str_list(optional_consumers if optional_consumers is not None else downstream_consumers)
    typed_monitoring_relationships = _dedupe_str_list(monitoring_relationships)
    typed_documentation_references = _dedupe_str_list(documentation_references if documentation_references is not None else (evidence + reports))
    dependency_projection = _dedupe_str_list(typed_build_dependencies + typed_runtime_dependencies + typed_evidence_dependencies)

    return {
        "id": capability_id,
        "name": name,
        "owner": owner,
        "canonical_responsibility": canonical_responsibility or capability_id,
        "purpose": purpose,
        "implementation_status": implementation_status,
        "verification_status": verification_status,
        "production_readiness": production_readiness,
        "required_build_dependencies": typed_build_dependencies,
        "required_runtime_dependencies": typed_runtime_dependencies,
        "evidence_dependencies": typed_evidence_dependencies,
        "optional_consumers": typed_optional_consumers,
        "monitoring_relationships": typed_monitoring_relationships,
        "documentation_references": typed_documentation_references,
        "dependencies": dependency_projection,
        "downstream_consumers": typed_optional_consumers,
        "blocking_issues": blocking_issues or [],
        "evidence": evidence,
        "implementation_files": implementation_files,
        "test_files": test_files,
        "reports": reports,
        "last_verified": None,
        "next_action": next_action,
    }


CAPABILITY_CATALOG: List[Dict[str, object]] = [
    _cap(
        "constitution_governance",
        "Constitution & Governance",
        "OPTIME Governance",
        "Constitutional constraints, owner gates, and principle authority for the platform.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        [],
        [
            "source_intelligence",
            "market_builder",
            "canonical_universe",
            "government_identity",
            "media_intelligence",
            "knowledge_graph",
            "data_quality_trust",
            "provider_intelligence",
            "clinical_knowledge",
            "clinical_evidence",
            "narrative_intelligence",
            "nutrition_intelligence",
            "outcome_learning",
            "resident_needs_intelligence",
            "senior_living_research",
            "family_experience_intelligence",
            "assessment_experience",
            "recommendation_decision_engine",
            "chief_ai_supervisor",
            "remediation_policy_engine",
            "daily_system_health_report",
            "email_delivery",
            "report_archive",
            "runtime_sync",
            "platform_registry",
        ],
        ["AGENTS.md", "docs/OPTIME_PRINCIPLES.md", "docs/OPTIME_PRINCIPLES_REGISTRY.md"],
        ["AGENTS.md", "docs/OPTIME_PRINCIPLES.md", "docs/OPTIME_PRINCIPLES_REGISTRY.md"],
        [],
        ["reports/OPTIME_AGENT_SYSTEM_AUDIT.md", "reports/OPTIME_DECISION_INTELLIGENCE_ARCHITECTURE.md"],
        "Preserve owner approval gates and keep constitutional checks explicit.",
    ),
    _cap(
        "source_intelligence",
        "Source Intelligence",
        "OPTIME Source Intelligence",
        "Discover, verify, and publish trusted source coverage and lifecycle state.",
        "IN_PROGRESS",
        "VERIFIED",
        "BLOCKED",
        ["constitution_governance"],
        ["market_builder", "canonical_universe", "data_quality_trust", "chief_ai_supervisor"],
        ["reports/SOURCE_LIFECYCLE_STATUS.md", "reports/SOURCE_POLICY_MIGRATION_REPORT.md", "reports/FLORIDA_SOURCE_CONNECTIVITY_AUDIT.md"],
        ["backend/app/services/source_lifecycle_service.py", "backend/app/services/source_policy_engine.py"],
        ["backend/tests/test_source_policy_engine.py"],
        ["reports/SOURCE_LIFECYCLE_STATUS.md", "reports/SOURCE_POLICY_MIGRATION_REPORT.md"],
        "Complete the remaining approved source integrations and unblock market build coverage.",
        [
            _blocked_issue(
                exact_blocker="Approved sources are not fully integrated and Florida state sources remain partially blocked.",
                blocker_owner="OPTIME Source Intelligence",
                blocker_evidence=["reports/SOURCE_LIFECYCLE_STATUS.md", "reports/SOURCE_POLICY_MIGRATION_REPORT.md"],
                blocker_type="DATA",
            )
        ],
    ),
    _cap(
        "market_builder",
        "Market Builder",
        "OPTIME Market Intelligence",
        "Prepare reusable market-specific canonical build runs and validation bundles.",
        "NOT_STARTED",
        "NOT_STARTED",
        "BLOCKED",
        ["constitution_governance", "source_intelligence"],
        ["canonical_universe"],
        ["reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md", "reports/NEVADA_SOURCE_INTEGRATION_REPORT.md"],
        ["scripts/build_nevada_canonical_universe.py", "scripts/run_nevada_authoritative_source_integration.py"],
        ["backend/tests/test_nevada_canonical_universe.py"],
        ["reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md", "reports/NEVADA_SOURCE_INTEGRATION_REPORT.md"],
        "Build the generic market-builder entry point and keep validation reusable across markets.",
        [
            _blocked_issue(
                exact_blocker="No generic builder entry point exists; validation remains state-specific.",
                blocker_owner="OPTIME Market Intelligence",
                blocker_evidence=["reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md", "reports/NEVADA_SOURCE_INTEGRATION_REPORT.md"],
                blocker_type="ARCHITECTURE",
            )
        ],
    ),
    _cap(
        "canonical_universe",
        "Canonical Universe",
        "OPTIME Canonical Universe",
        "Normalize, deduplicate, and publish canonical facility identities and crosswalks.",
        "IMPLEMENTED",
        "VERIFIED",
        "BLOCKED",
        ["market_builder", "source_intelligence"],
        ["government_identity", "media_intelligence", "assessment_experience", "recommendation_decision_engine", "chief_ai_supervisor"],
        ["reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md", "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md", "reports/FLORIDA_CANONICAL_UNIVERSE_AUDIT.md"],
        ["backend/app/services/canonical_universe.py", "scripts/build_nevada_canonical_universe.py"],
        ["backend/tests/test_nevada_canonical_universe.py"],
        ["reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md", "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md"],
        "Finish the remaining market-builder dependency chain and close the Nevada HCQC gap.",
        [
            _blocked_issue(
                exact_blocker="Layer 2 Market Builder remains state-specific and Nevada HCQC remains unintegrated.",
                blocker_owner="OPTIME Market Intelligence",
                blocker_evidence=["reports/PLATFORM_READINESS_MATRIX.json", "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md"],
                blocker_type="DATA",
            )
        ],
    ),
    _cap(
        "government_identity",
        "Government Identity",
        "OPTIME Identity Governance",
        "Resolve legal names, NPI links, state identity, and crosswalks for canonical facilities.",
        "IMPLEMENTED",
        "VERIFIED",
        "BLOCKED",
        ["canonical_universe"],
        ["media_intelligence", "recommendation_decision_engine", "assessment_experience"],
        ["reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md", "reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.json"],
        ["backend/app/services/government_identity_media.py"],
        ["backend/tests/test_government_identity_media.py"],
        ["reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md"],
        "Finish identity crosswalk coverage once canonical universe completeness is settled.",
        [
            _blocked_issue(
                exact_blocker="Government identity resolution still depends on incomplete canonical universe coverage.",
                blocker_owner="OPTIME Identity Governance",
                blocker_evidence=["reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md", "reports/FLORIDA_CANONICAL_UNIVERSE_AUDIT.md"],
                blocker_type="DATA",
            )
        ],
    ),
    _cap(
        "media_intelligence",
        "Media Intelligence",
        "OPTIME Media Intelligence",
        "Verify facility images and media identity without letting generic media become evidence.",
        "IN_PROGRESS",
        "VERIFIED",
        "BLOCKED",
        ["canonical_universe", "government_identity"],
        ["recommendation_decision_engine", "assessment_experience"],
        ["reports/MEDIA_LIVE_PILOT_FAILURE_ANALYSIS.md", "reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md"],
        ["backend/app/services/facility_media_resolution.py", "backend/app/services/facility_media_registry.py"],
        ["backend/tests/test_facility_media_resolution.py"],
        ["reports/MEDIA_LIVE_PILOT_FAILURE_ANALYSIS.md", "reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md"],
        "Complete rights validation and media pilot gating before expanding image coverage.",
        [
            _blocked_issue(
                exact_blocker="Rights validation is not integrated for the media pilot and generic media remains non-facility-specific.",
                blocker_owner="OPTIME Governance",
                blocker_evidence=["reports/MEDIA_LIVE_PILOT_FAILURE_ANALYSIS.md"],
                blocker_type="LEGAL",
            )
        ],
    ),
    _cap(
        "knowledge_graph",
        "Knowledge Graph",
        "OPTIME Knowledge Graph Intelligence",
        "Link knowledge objects into an explainable, deduplicated platform graph.",
        "IMPLEMENTED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["source_intelligence", "canonical_universe"],
        ["provider_intelligence", "clinical_knowledge", "assessment_experience", "recommendation_decision_engine", "chief_ai_supervisor"],
        ["reports/knowledge_graph_design.md", "reports/knowledge_repository_schema.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/knowledge_graph_design.md", "reports/knowledge_repository_schema.md"],
        "Maintain graph integrity and orphan detection while upstream sources continue maturing.",
        required_build_dependencies=[],
        evidence_dependencies=["source_intelligence", "canonical_universe"],
    ),
    _cap(
        "data_quality_trust",
        "Data Quality & Trust",
        "OPTIME Data Quality",
        "Protect freshness, provenance, and conflict resolution across prepared knowledge.",
        "IMPLEMENTED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["source_intelligence"],
        ["chief_ai_supervisor", "recommendation_decision_engine"],
        ["reports/platform_health_report.md", "reports/knowledge_quality_framework.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        ["backend/tests/test_remediation_policy_engine.py"],
        ["reports/platform_health_report.md", "reports/knowledge_quality_framework.md"],
        "Continue freshness and conflict monitoring across all prepared knowledge objects.",
        required_build_dependencies=[],
        monitoring_relationships=["source_intelligence"],
    ),
    _cap(
        "matching_improvement",
        "Matching Improvement",
        "OPTIME Matching Improvement",
        "Apply validated ranking-policy improvements and guardrails.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["knowledge_graph", "data_quality_trust"],
        ["narrative_intelligence", "outcome_learning"],
        ["reports/agent_registry.md", "reports/agent_value_matrix.md", "reports/benchmark_gap_analysis.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        ["backend/tests/test_platform_registry.py", "backend/tests/test_chief_ai_supervisor_operations.py"],
        ["reports/agent_registry.md", "reports/agent_value_matrix.md", "reports/benchmark_gap_analysis.md"],
        "Keep ranking policy guardrails aligned with validated traces and outcomes.",
    ),
    _cap(
        "provider_intelligence",
        "Provider Intelligence",
        "OPTIME Provider Intelligence",
        "Discover and verify provider capabilities so recommendations use prepared provider intelligence.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["activities_intelligence", "nutrition_intelligence", "data_quality_trust", "knowledge_graph"],
        ["canonical_universe", "recommendation_decision_engine", "assessment_experience"],
        ["reports/platform_intelligence_report.md", "reports/agent_registry.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        ["backend/tests/test_chief_ai_supervisor_operations.py"],
        ["reports/platform_intelligence_report.md", "reports/agent_registry.md"],
        "Continue controlled discovery and publish only verified provider updates.",
        required_build_dependencies=["data_quality_trust", "knowledge_graph"],
        optional_consumers=["canonical_universe", "recommendation_decision_engine", "assessment_experience", "activities_intelligence", "nutrition_intelligence", "clinical_knowledge", "resident_needs_intelligence", "senior_living_research", "narrative_intelligence"],
    ),
    _cap(
        "activities_intelligence",
        "Activities Intelligence",
        "OPTIME Lifestyle Intelligence",
        "Publish verified activities and engagement intelligence that improves lifestyle fit recommendations.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["provider_intelligence", "narrative_intelligence", "outcome_learning", "knowledge_graph"],
        ["recommendation_decision_engine", "assessment_experience"],
        ["reports/agent_registry.md", "reports/agent_task_queue.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/agent_registry.md", "reports/agent_task_queue.md"],
        "Keep publishing verified activities intelligence and close stale content gaps.",
        required_build_dependencies=["provider_intelligence", "outcome_learning", "knowledge_graph"],
        optional_consumers=["recommendation_decision_engine", "assessment_experience", "narrative_intelligence"],
    ),
    _cap(
        "clinical_knowledge",
        "Clinical Knowledge",
        "OPTIME Clinical Intelligence",
        "Discover and validate trusted clinical guidance for care-fit recommendations.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["clinical_evidence", "provider_intelligence", "outcome_learning", "knowledge_graph"],
        ["assessment_experience", "recommendation_decision_engine", "family_experience_intelligence"],
        ["reports/clinical_knowledge_platform.md", "reports/clinical_evidence_validation.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/clinical_knowledge_platform.md", "reports/clinical_evidence_validation.md"],
        "Continue validating care-fit guidance against prepared evidence.",
        required_build_dependencies=["provider_intelligence", "knowledge_graph"],
        evidence_dependencies=["clinical_evidence", "outcome_learning"],
    ),
    _cap(
        "clinical_evidence",
        "Clinical Evidence",
        "OPTIME Evidence Intelligence",
        "Attach trusted evidence to clinical and recommendation claims.",
        "IN_PROGRESS",
        "IN_PROGRESS",
        "BLOCKED",
        ["clinical_knowledge", "outcome_learning", "knowledge_graph"],
        ["clinical_knowledge", "recommendation_decision_engine"],
        ["reports/clinical_evidence_validation.md", "reports/knowledge_validation_framework.md"],
        ["backend/app/services/evidence_engine_service.py"],
        [],
        ["reports/clinical_evidence_validation.md", "reports/knowledge_validation_framework.md"],
        "Automate evidence monitoring and close the external evidence gap.",
        [
            _blocked_issue(
                exact_blocker="Automated external evidence monitoring is not configured.",
                blocker_owner="OPTIME Evidence Intelligence",
                blocker_evidence=["reports/clinical_evidence_validation.md", "reports/knowledge_validation_framework.md"],
                blocker_type="DATA",
            )
        ],
        required_build_dependencies=["knowledge_graph"],
        optional_consumers=["clinical_knowledge", "recommendation_decision_engine", "narrative_intelligence"],
    ),
    _cap(
        "narrative_intelligence",
        "Narrative Intelligence",
        "OPTIME Narrative Intelligence",
        "Produce advisor-ready explanations and trust-clarity narratives from prepared knowledge.",
        "IN_PROGRESS",
        "IN_PROGRESS",
        "BLOCKED",
        ["clinical_knowledge", "provider_intelligence", "clinical_evidence", "knowledge_graph", "matching_improvement"],
        ["family_experience_intelligence", "recommendation_decision_engine"],
        ["reports/OPTIME_IMMERSIVE_EDITORIAL_EXPERIENCE_STRATEGY.md", "reports/agent_registry.md"],
        ["frontend/src/components/assessment/advisor-response.tsx"],
        [],
        ["reports/OPTIME_IMMERSIVE_EDITORIAL_EXPERIENCE_STRATEGY.md", "reports/agent_registry.md"],
        "Complete the explanation-quality pipeline once upstream evidence coverage is stronger.",
        [
            _blocked_issue(
                exact_blocker="Upstream evidence and knowledge coverage remain insufficient for fully trusted narratives.",
                blocker_owner="OPTIME Narrative Intelligence",
                blocker_evidence=["reports/agent_registry.md", "reports/OPTIME_AGENT_SYSTEM_AUDIT.md"],
                blocker_type="DATA",
            )
        ],
        required_build_dependencies=["provider_intelligence", "knowledge_graph"],
        evidence_dependencies=["clinical_knowledge", "clinical_evidence", "matching_improvement"],
    ),
    _cap(
        "nutrition_intelligence",
        "Nutrition Intelligence",
        "OPTIME Nutrition Intelligence",
        "Discover and verify dietary support capabilities for nutrition and allergy needs.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["clinical_knowledge", "provider_intelligence", "knowledge_graph"],
        ["recommendation_decision_engine", "assessment_experience"],
        ["reports/agent_registry.md", "reports/knowledge_workforce_architecture.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/agent_registry.md", "reports/knowledge_workforce_architecture.md"],
        "Keep nutrition evidence fresh and close unsupported dietary gaps.",
        required_build_dependencies=["provider_intelligence", "knowledge_graph"],
        evidence_dependencies=["clinical_knowledge"],
    ),
    _cap(
        "outcome_learning",
        "Outcome Learning",
        "OPTIME Outcome Intelligence",
        "Transform outcome signals into prepared knowledge that improves fit, safety, and quality.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["matching_improvement", "clinical_knowledge", "knowledge_graph"],
        ["recommendation_decision_engine", "chief_ai_supervisor"],
        ["reports/agent_registry.md", "reports/knowledge_growth_matrix.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/agent_registry.md", "reports/knowledge_growth_matrix.md"],
        "Keep outcome calibration aligned with verified traces and facts.",
        required_build_dependencies=["knowledge_graph", "matching_improvement"],
        evidence_dependencies=["clinical_knowledge"],
    ),
    _cap(
        "resident_needs_intelligence",
        "Resident Needs Intelligence",
        "OPTIME Resident Needs Intelligence",
        "Model resident needs and constraints for fit and safety.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["provider_intelligence", "knowledge_graph"],
        ["assessment_experience", "recommendation_decision_engine"],
        ["reports/agent_registry.md", "reports/knowledge_workforce_architecture.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/agent_registry.md", "reports/knowledge_workforce_architecture.md"],
        "Keep resident-need modeling aligned with structured evidence inputs.",
    ),
    _cap(
        "senior_living_research",
        "Senior Living Research",
        "OPTIME Senior Living Research",
        "Produce verified senior living research summaries and knowledge signals.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["provider_intelligence", "knowledge_graph"],
        ["chief_ai_supervisor", "knowledge_graph"],
        ["reports/agent_registry.md", "reports/agent_daily_missions.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/agent_registry.md", "reports/agent_daily_missions.md"],
        "Keep research summaries aligned with verified source intelligence.",
    ),
    _cap(
        "family_experience_intelligence",
        "Family Experience Intelligence",
        "OPTIME Family Experience Intelligence",
        "Convert prepared knowledge into family-ready guidance and trust clarity.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["knowledge_graph", "narrative_intelligence"],
        ["assessment_experience", "recommendation_decision_engine"],
        ["reports/family_experience_report.md", "reports/family_journey_review.md"],
        ["backend/app/services/agent_knowledge_reports.py"],
        [],
        ["reports/family_experience_report.md", "reports/family_journey_review.md"],
        "Keep family guidance consistent with verified evidence and uncertainty visibility.",
        required_build_dependencies=["knowledge_graph"],
        evidence_dependencies=["narrative_intelligence"],
    ),
    _cap(
        "assessment_experience",
        "Assessment Experience",
        "OPTIME Assessment Experience",
        "Own the family assessment journey and collect decision-relevant preferences.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["canonical_universe", "knowledge_graph", "family_experience_intelligence", "resident_needs_intelligence"],
        ["recommendation_decision_engine"],
        ["reports/assessment-ux-review", "reports/ADAPTIVE_INTERVIEW_CURRENT_CODE_EXTRACT.md"],
        ["frontend/src/app/assessment/page.tsx", "frontend/src/components/assessment/assessment-advisor-experience.tsx"],
        ["frontend/tests/assessment-conversation.test.ts", "frontend/tests/assessment-profile.test.ts", "frontend/tests/assessment-schema.test.ts"],
        ["reports/ADAPTIVE_INTERVIEW_CURRENT_CODE_EXTRACT.md", "reports/assessment-ux-review"],
        "Preserve the governed assessment flow and keep advice explainable.",
        required_build_dependencies=["knowledge_graph", "resident_needs_intelligence"],
        evidence_dependencies=["family_experience_intelligence"],
        optional_consumers=["recommendation_decision_engine", "canonical_universe"],
    ),
    _cap(
        "recommendation_decision_engine",
        "Recommendation Decision Engine",
        "OPTIME Recommendation Engine",
        "Convert prepared knowledge and assessment inputs into governed recommendations.",
        "IMPLEMENTED",
        "VERIFIED",
        "BLOCKED",
        ["canonical_universe", "knowledge_graph", "assessment_experience"],
        ["family_experience_intelligence", "chief_ai_supervisor"],
        ["reports/OPTIME_END_TO_END_DECISION_SIMULATION.md", "reports/OPTIME_END_TO_END_FAMILY_EXPLANATION.md", "reports/OPTIME_END_TO_END_SENSITIVITY_ANALYSIS.md"],
        ["backend/app/services/patient_decision_engine.py"],
        ["backend/tests/test_patient_decision_engine.py"],
        ["reports/OPTIME_END_TO_END_DECISION_SIMULATION.md", "reports/OPTIME_END_TO_END_FAMILY_EXPLANATION.md"],
        "Keep recommendation logic unchanged while upstream readiness is completed.",
        [
            _blocked_issue(
                exact_blocker="Upstream canonical universe and assessment readiness remain incomplete for full production confidence.",
                blocker_owner="OPTIME Recommendation Engine",
                blocker_evidence=["reports/OPTIME_END_TO_END_DECISION_SIMULATION.md", "reports/PLATFORM_READINESS_MATRIX.json"],
                blocker_type="ARCHITECTURE",
            )
        ],
    ),
    _cap(
        "chief_ai_supervisor",
        "Chief AI Supervisor",
        "OPTIME Platform Governance",
        "Coordinate incidents, scheduler cycles, readiness, and publication readiness.",
        "VERIFIED",
        "VERIFIED",
        "BLOCKED",
        [
            "constitution_governance",
            "source_intelligence",
            "market_builder",
            "canonical_universe",
            "data_quality_trust",
            "report_archive",
            "runtime_sync",
            "remediation_policy_engine",
            "email_delivery",
        ],
        ["daily_system_health_report", "platform_registry", "remediation_policy_engine"],
        ["reports/platform_health_report.md", "reports/platform_intelligence_report.md", "reports/DAILY_SYSTEM_HEALTH.md"],
        ["backend/app/services/chief_ai_supervisor.py", "backend/app/main.py"],
        ["backend/tests/test_chief_ai_supervisor_operations.py", "backend/tests/test_system_health_service.py"],
        ["reports/platform_health_report.md", "reports/platform_intelligence_report.md", "reports/DAILY_SYSTEM_HEALTH.md"],
        "Keep the supervisor operating, but do not claim full production readiness while email is blocked.",
        [
            _blocked_issue(
                exact_blocker="Owner email delivery remains blocked by missing SMTP configuration.",
                blocker_owner="OPTIME Operations",
                blocker_evidence=["reports/DAILY_SYSTEM_HEALTH.md", "database/system_recovery_state.json"],
                blocker_type="CONFIGURATION",
            )
        ],
        required_build_dependencies=["constitution_governance"],
        required_runtime_dependencies=["platform_registry", "report_archive", "runtime_sync", "remediation_policy_engine"],
        monitoring_relationships=["source_intelligence", "market_builder", "canonical_universe", "data_quality_trust", "email_delivery"],
        optional_consumers=["daily_system_health_report", "platform_registry", "remediation_policy_engine"],
    ),
    _cap(
        "remediation_policy_engine",
        "Remediation Policy Engine",
        "OPTIME Platform Governance",
        "Select bounded allowlisted remediation actions for known failure types.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["constitution_governance"],
        ["chief_ai_supervisor", "daily_system_health_report"],
        ["reports/platform_health_report.md", "reports/OPTIME_AGENT_SYSTEM_AUDIT.md"],
        ["backend/app/services/remediation_policy_engine.py"],
        ["backend/tests/test_remediation_policy_engine.py"],
        ["reports/platform_health_report.md"],
        "Maintain allowlisted recovery behavior and keep execution bounded.",
    ),
    _cap(
        "email_delivery",
        "Email Delivery",
        "OPTIME Operations",
        "Send owner-facing reports through the canonical SMTP path.",
        "IMPLEMENTED",
        "VERIFIED",
        "BLOCKED",
        ["report_archive", "constitution_governance"],
        ["daily_system_health_report", "chief_ai_supervisor"],
        ["reports/DAILY_SYSTEM_HEALTH.md", "reports/platform_health_report.md"],
        ["backend/app/services/email_service.py"],
        [],
        ["reports/DAILY_SYSTEM_HEALTH.md", "reports/platform_health_report.md"],
        "Provide SMTP configuration and confirm delivery acceptance.",
        [
            _blocked_issue(
                exact_blocker="OPTIME_SMTP_HOST and OPTIME_SMTP_FROM are missing from environment configuration.",
                blocker_owner="OPTIME Operations",
                blocker_evidence=["backend/app/services/email_service.py", "database/system_recovery_state.json"],
                blocker_type="CONFIGURATION",
            )
        ],
    ),
    _cap(
        "report_archive",
        "Report Archive",
        "OPTIME Platform Operations",
        "Persist and version report artifacts and sent-status records.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["constitution_governance"],
        ["daily_system_health_report", "chief_ai_supervisor"],
        ["reports/daily/index.json", "reports/daily/latest.md"],
        ["backend/app/services/report_archive_service.py"],
        [],
        ["reports/daily/index.json", "reports/daily/latest.md"],
        "Keep the archive canonical and idempotent for daily reporting.",
    ),
    _cap(
        "runtime_sync",
        "Runtime Sync",
        "OPTIME Platform Operations",
        "Track schema drift and keep runtime metadata aligned with the live database.",
        "VERIFIED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["constitution_governance"],
        ["chief_ai_supervisor", "daily_system_health_report"],
        ["reports/GOVERNED_RUNTIME_INTEGRATION_REPORT.md", "reports/OPTIME_AGENT_SYSTEM_AUDIT.md"],
        ["backend/app/services/runtime_sync_service.py"],
        ["backend/tests/test_runtime_sync_service.py"],
        ["reports/GOVERNED_RUNTIME_INTEGRATION_REPORT.md"],
        "Continue runtime schema alignment and drift monitoring.",
    ),
    _cap(
        "daily_system_health_report",
        "Daily System Health Report",
        "OPTIME Chief AI Supervisor",
        "Generate the canonical daily owner report and capture delivery state.",
        "VERIFIED",
        "VERIFIED",
        "BLOCKED",
        ["chief_ai_supervisor", "report_archive", "email_delivery"],
        ["owner", "chief_ai_supervisor"],
        ["reports/DAILY_SYSTEM_HEALTH.md", "reports/DAILY_SYSTEM_HEALTH.json"],
        ["backend/app/services/system_health_service.py", "backend/app/services/daily_system_health_service.py"],
        ["backend/tests/test_system_health_service.py"],
        ["reports/DAILY_SYSTEM_HEALTH.md", "reports/DAILY_SYSTEM_HEALTH.json"],
        "Keep report generation canonical while email remains blocked by configuration.",
        [
            _blocked_issue(
                exact_blocker="SMTP delivery is blocked by missing required environment variables.",
                blocker_owner="OPTIME Operations",
                blocker_evidence=["backend/app/services/email_service.py", "database/system_recovery_state.json"],
                blocker_type="CONFIGURATION",
            )
        ],
        required_build_dependencies=["chief_ai_supervisor", "report_archive"],
        optional_consumers=["chief_ai_supervisor", "email_delivery"],
    ),
    _cap(
        "platform_registry",
        "Platform Registry",
        "OPTIME Platform Governance",
        "Canonical inventory of platform capabilities, dependencies, readiness, and business progress.",
        "IMPLEMENTED",
        "VERIFIED",
        "PRODUCTION_READY",
        ["constitution_governance", "chief_ai_supervisor", "daily_system_health_report", "report_archive", "runtime_sync"],
        ["chief_ai_supervisor", "platform_governance", "business_progress"],
        ["reports/platform_health_report.md", "reports/platform_intelligence_report.md", "reports/OPTIME_AGENT_SYSTEM_AUDIT.md", "reports/PLATFORM_READINESS_MATRIX.json"],
        ["backend/app/services/platform_registry_service.py", "scripts/build_platform_registry.py"],
        ["backend/tests/test_platform_registry.py"],
        ["reports/PLATFORM_READINESS_MATRIX.json", "reports/OPTIME_AGENT_SYSTEM_AUDIT.md"],
        "Keep the registry synchronized to the latest verified evidence and supervisor state.",
        required_build_dependencies=["constitution_governance"],
        optional_consumers=["chief_ai_supervisor"],
    ),
]


OBJECTIVE_CATALOG: List[Dict[str, object]] = [
    {
        "objective_id": "launch_nevada",
        "name": "Launch Nevada",
        "business_goal": "Launch the Nevada market on verified source, canonical, provider, media, and recommendation coverage.",
        "owner": "OPTIME Platform Governance",
        "activation_status": "ACTIVE",
        "owner_approval_state": "OWNER_APPROVED",
        "priority": 1,
        "target_market": "nevada",
        "required_capabilities": [
            "source_intelligence",
            "market_builder",
            "canonical_universe",
            "provider_intelligence",
            "media_intelligence",
            "recommendation_decision_engine",
        ],
    },
    {
        "objective_id": "launch_florida",
        "name": "Launch Florida",
        "business_goal": "Launch the Florida market on verified source, canonical, provider, and recommendation coverage.",
        "owner": "OPTIME Platform Governance",
        "activation_status": "PLANNED",
        "owner_approval_state": "OWNER_DECLARED",
        "priority": 2,
        "target_market": "florida",
        "required_capabilities": [
            "source_intelligence",
            "market_builder",
            "canonical_universe",
            "provider_intelligence",
            "media_intelligence",
            "recommendation_decision_engine",
        ],
    },
    {
        "objective_id": "launch_texas",
        "name": "Launch Texas",
        "business_goal": "Launch the Texas market using the existing source, canonical, provider, and recommendation stack.",
        "owner": "OPTIME Platform Governance",
        "activation_status": "PLANNED",
        "owner_approval_state": "OWNER_DECLARED",
        "priority": 3,
        "target_market": "texas",
        "required_capabilities": [
            "source_intelligence",
            "market_builder",
            "canonical_universe",
            "provider_intelligence",
            "recommendation_decision_engine",
        ],
    },
    {
        "objective_id": "media_ready",
        "name": "Media Ready",
        "business_goal": "Make media-specific capabilities production ready without using generic media as evidence.",
        "owner": "OPTIME Media Intelligence",
        "activation_status": "PLANNED",
        "owner_approval_state": "OWNER_DECLARED",
        "priority": 4,
        "target_market": "all",
        "required_capabilities": ["canonical_universe", "government_identity", "media_intelligence"],
    },
    {
        "objective_id": "recommendation_production_ready",
        "name": "Recommendation Production Ready",
        "business_goal": "Keep the recommendation engine production ready against prepared knowledge and assessment inputs.",
        "owner": "OPTIME Recommendation Engine",
        "activation_status": "PLANNED",
        "owner_approval_state": "OWNER_DECLARED",
        "priority": 5,
        "target_market": "all",
        "required_capabilities": ["canonical_universe", "knowledge_graph", "assessment_experience", "recommendation_decision_engine"],
    },
    {
        "objective_id": "provider_portal_production_ready",
        "name": "Provider Portal Production Ready",
        "business_goal": "Keep provider-facing capabilities production ready with verified provider knowledge.",
        "owner": "OPTIME Provider Intelligence",
        "activation_status": "PLANNED",
        "owner_approval_state": "OWNER_DECLARED",
        "priority": 6,
        "target_market": "all",
        "required_capabilities": ["provider_intelligence", "data_quality_trust", "knowledge_graph"],
    },
]


def _capability_index(capabilities: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    return {str(capability.get("id") or ""): capability for capability in capabilities}


def _objective_index(objectives: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    return {str(objective.get("objective_id") or ""): objective for objective in objectives}


def _required_build_dependencies(capability: Dict[str, object]) -> List[str]:
    if "required_build_dependencies" in capability:
        return _dedupe_str_list(list(capability.get("required_build_dependencies") or []))
    return _dedupe_str_list(list(capability.get("dependencies") or []))


def _required_runtime_dependencies(capability: Dict[str, object]) -> List[str]:
    if "required_runtime_dependencies" in capability:
        return _dedupe_str_list(list(capability.get("required_runtime_dependencies") or []))
    return []


def _evidence_dependencies(capability: Dict[str, object]) -> List[str]:
    if "evidence_dependencies" in capability:
        return _dedupe_str_list(list(capability.get("evidence_dependencies") or []))
    return []


def _optional_consumers(capability: Dict[str, object]) -> List[str]:
    return _dedupe_str_list(list(capability.get("optional_consumers") or capability.get("downstream_consumers") or []))


def _monitoring_relationships(capability: Dict[str, object]) -> List[str]:
    return _dedupe_str_list(list(capability.get("monitoring_relationships") or []))


def _documentation_references(capability: Dict[str, object]) -> List[str]:
    return _dedupe_str_list(list(capability.get("documentation_references") or capability.get("reports") or []))


def _required_dependency_ids(capability: Dict[str, object]) -> List[str]:
    return _dedupe_str_list(_required_build_dependencies(capability) + _required_runtime_dependencies(capability))


def _normalize_capability_record(capability: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(capability)
    normalized["required_build_dependencies"] = _required_build_dependencies(normalized)
    normalized["required_runtime_dependencies"] = _required_runtime_dependencies(normalized)
    normalized["evidence_dependencies"] = _evidence_dependencies(normalized)
    normalized["optional_consumers"] = _optional_consumers(normalized)
    normalized["monitoring_relationships"] = _monitoring_relationships(normalized)
    normalized["documentation_references"] = _documentation_references(normalized)
    normalized["canonical_responsibility"] = str(normalized.get("canonical_responsibility") or normalized.get("id") or "")
    normalized["dependencies"] = _dedupe_str_list(
        normalized["required_build_dependencies"]
        + normalized["required_runtime_dependencies"]
        + normalized["evidence_dependencies"]
    )
    normalized["downstream_consumers"] = normalized["optional_consumers"]
    return normalized


def _objective_activation_status(objective: Dict[str, object]) -> str:
    return str(objective.get("activation_status") or "PLANNED").upper()


def _normalize_objective_record(objective: Dict[str, object]) -> Dict[str, object]:
    normalized = dict(objective)
    normalized["activation_status"] = _objective_activation_status(normalized)
    return normalized


def _active_objective_records(objectives: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [objective for objective in objectives if _objective_activation_status(objective) == "ACTIVE"]


def _capability_complete(capability: Dict[str, object]) -> bool:
    return str(capability.get("production_readiness") or "") == "PRODUCTION_READY"


def _capability_ready(capability: Dict[str, object]) -> bool:
    return str(capability.get("verification_status") or "") in {"VERIFIED", "PRODUCTION_READY"}


def _capability_runtime_available(capability: Dict[str, object]) -> bool:
    return _capability_ready(capability) and str(capability.get("production_readiness") or "") not in {"BLOCKED", "FROZEN"}


def _objective_requirement_ids(objective: Dict[str, object]) -> List[str]:
    return [str(item) for item in objective.get("required_capabilities") or []]


def _objective_required_capabilities(objective: Dict[str, object], capability_index: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    return [capability_index[capability_id] for capability_id in _objective_requirement_ids(objective) if capability_id in capability_index]


def _objective_dependency_violations(objective: Dict[str, object], capability_index: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    required_ids = set(_objective_requirement_ids(objective))
    violations: List[Dict[str, object]] = []
    for capability_id in required_ids:
        capability = capability_index.get(capability_id)
        if capability is None:
            violations.append(
                {
                    "capability_id": capability_id,
                    "dependency_id": None,
                    "reason": "Required capability is missing from the registry.",
                }
            )
            continue
        for dependency_id in _required_build_dependencies(capability):
            dependency = capability_index.get(str(dependency_id))
            if dependency is None:
                violations.append(
                    {
                        "capability_id": capability_id,
                        "dependency_id": dependency_id,
                        "reason": "Dependency is missing from the registry.",
                    }
                )
                continue
            if not _capability_ready(dependency):
                violations.append(
                    {
                        "capability_id": capability_id,
                        "dependency_id": dependency_id,
                        "reason": "Dependency is not verified or production ready.",
                    }
                )
    return violations


def _objective_topological_order(objective: Dict[str, object], capability_index: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    required_ids = set(_objective_requirement_ids(objective))
    ordered: List[Dict[str, object]] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str) -> None:
        if capability_id in visited or capability_id not in required_ids:
            return
        if capability_id in visiting:
            return
        visiting.add(capability_id)
        capability = capability_index.get(capability_id)
        if capability is not None:
            for dependency_id in _required_build_dependencies(capability):
                visit(str(dependency_id))
            ordered.append(capability)
        visiting.remove(capability_id)
        visited.add(capability_id)

    for capability_id in _objective_requirement_ids(objective):
        visit(capability_id)
    return ordered


def _objective_milestones(objective: Dict[str, object], capability_index: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    required_ids = set(_objective_requirement_ids(objective))
    depth_cache: Dict[str, int] = {}

    def depth(capability_id: str) -> int:
        if capability_id in depth_cache:
            return depth_cache[capability_id]
        capability = capability_index.get(capability_id)
        if capability is None:
            depth_cache[capability_id] = 1
            return 1
        direct_dependencies = [str(dep) for dep in _required_build_dependencies(capability) if str(dep) in required_ids]
        if not direct_dependencies:
            depth_cache[capability_id] = 1
            return 1
        depth_cache[capability_id] = 1 + max(depth(dep) for dep in direct_dependencies)
        return depth_cache[capability_id]

    grouped: Dict[int, List[str]] = {}
    for capability_id in _objective_requirement_ids(objective):
        grouped.setdefault(depth(capability_id), []).append(capability_id)

    milestones: List[Dict[str, object]] = []
    for index, depth_value in enumerate(sorted(grouped)):
        capability_ids = grouped[depth_value]
        capabilities = [capability_index[capability_id] for capability_id in capability_ids if capability_id in capability_index]
        milestones.append(
            {
                "milestone_id": f"{objective['objective_id']}-m{index + 1}",
                "name": f"Milestone {index + 1}",
                "depth": depth_value,
                "capability_ids": capability_ids,
                "capabilities": [capability["id"] for capability in capabilities],
                "completed_capabilities": sum(1 for capability in capabilities if _capability_complete(capability)),
                "blocked_capabilities": sum(1 for capability in capabilities if str(capability.get("production_readiness") or "") in {"BLOCKED", "FROZEN"}),
            }
        )
    return milestones


def _objective_completion(objective: Dict[str, object], capability_index: Dict[str, Dict[str, object]]) -> Dict[str, object]:
    required_capabilities = _objective_required_capabilities(objective, capability_index)
    total = len(required_capabilities)
    completed = [capability for capability in required_capabilities if _capability_complete(capability)]
    blocked = [capability for capability in required_capabilities if str(capability.get("production_readiness") or "") in {"BLOCKED", "FROZEN"}]
    waiting = [capability for capability in required_capabilities if capability not in completed and capability not in blocked]
    milestone_list = _objective_milestones(objective, capability_index)
    current_executable = next((capability for capability in _objective_topological_order(objective, capability_index) if capability not in completed), None)
    if current_executable is None and required_capabilities:
        current_executable = next((capability for capability in required_capabilities if capability not in completed), required_capabilities[0])

    current_blocker = None
    if current_executable is not None:
        if str(current_executable.get("production_readiness") or "") in {"BLOCKED", "FROZEN"}:
            current_blocker = current_executable
        else:
            for dependency_id in _required_build_dependencies(current_executable):
                dependency = capability_index.get(str(dependency_id))
                if dependency is not None and not _capability_ready(dependency):
                    current_blocker = dependency
                    break
    if current_blocker is None and blocked:
        current_blocker = blocked[0]

    overall_completion = round((len(completed) / total) * 100, 1) if total else 100.0
    remaining = max(0, total - len(completed))
    business_readiness = "READY" if remaining == 0 else ("BLOCKED" if blocked else "IN_PROGRESS")
    current_milestone = next((milestone for milestone in milestone_list if current_executable is not None and str(current_executable.get("id") or "") in set(milestone.get("capability_ids") or [])), milestone_list[0] if milestone_list else None)

    return {
        "objective_id": objective["objective_id"],
        "name": objective["name"],
        "business_goal": objective["business_goal"],
        "owner": objective["owner"],
        "activation_status": _objective_activation_status(objective),
        "owner_approval_state": str(objective.get("owner_approval_state") or "OWNER_DECLARED"),
        "priority": objective["priority"],
        "target_market": objective["target_market"],
        "required_capabilities": [capability["id"] for capability in required_capabilities],
        "status": "PRODUCTION_READY" if remaining == 0 else ("BLOCKED" if blocked else "IN_PROGRESS"),
        "completion_percentage": overall_completion,
        "completed_capabilities": [capability["id"] for capability in completed],
        "remaining_capabilities": [capability["id"] for capability in required_capabilities if capability not in completed],
        "blocked_capabilities": [capability["id"] for capability in blocked],
        "waiting_capabilities": [capability["id"] for capability in waiting],
        "current_work": current_executable["id"] if current_executable else None,
        "current_blocker": current_blocker["id"] if current_blocker else None,
        "lowest_blocking_capability": current_blocker["id"] if current_blocker else None,
        "next_executable_capability": current_executable["id"] if current_executable else None,
        "assigned_agent": current_executable.get("owner") if current_executable else None,
        "current_task": current_executable.get("next_action") if current_executable else None,
        "current_milestone": current_milestone,
        "milestones": milestone_list,
        "milestone_count": len(milestone_list),
        "dependency_violations": _objective_dependency_violations(objective, capability_index),
        "estimated_remaining_work": {
            "capabilities": remaining,
            "milestones": max(0, len(milestone_list) - sum(1 for milestone in milestone_list if all(capability_index.get(capability_id) and _capability_complete(capability_index[capability_id]) for capability_id in milestone.get("capability_ids") or []))),
        },
        "business_readiness": business_readiness,
    }


def build_objective_catalog_payload(capabilities: Optional[List[Dict[str, object]]] = None, objectives: Optional[List[Dict[str, object]]] = None) -> Dict[str, object]:
    capability_records = [_normalize_capability_record(dict(capability)) for capability in (capabilities or CAPABILITY_CATALOG)]
    objective_records = [_normalize_objective_record(dict(objective)) for objective in (objectives or OBJECTIVE_CATALOG)]
    capability_index = _capability_index(capability_records)
    objective_dashboards = [_objective_completion(objective, capability_index) for objective in sorted(objective_records, key=lambda row: int(row.get("priority") or 0))]
    active_objectives = _active_objective_records(objective_records)
    active_objective_id = active_objectives[0]["objective_id"] if len(active_objectives) == 1 else None
    current_active_objective = next((objective for objective in objective_dashboards if objective.get("objective_id") == active_objective_id), None)
    overall_completion = round(sum(float(objective.get("completion_percentage") or 0.0) for objective in objective_dashboards) / len(objective_dashboards), 1) if objective_dashboards else 100.0
    capabilities_reused = len({capability_id for objective in objective_dashboards for capability_id in objective.get("required_capabilities") or []})
    milestones_generated = sum(int(objective.get("milestone_count") or 0) for objective in objective_dashboards)
    total_objective_dependency_violations = sum(len(objective.get("dependency_violations") or []) for objective in objective_dashboards)
    current_objective = current_active_objective
    current_blocker = current_objective.get("current_blocker") if current_objective else None
    current_executable = current_objective.get("next_executable_capability") if current_objective else None
    current_assigned_agent = current_objective.get("assigned_agent") if current_objective else None
    current_task = current_objective.get("current_task") if current_objective else None

    return {
        "generated_at_utc": _iso_now(),
        "registry_version": "platform-registry-v2.1.0",
        "summary": {
            "objectives_discovered": len(objective_dashboards),
            "capabilities_reused": capabilities_reused,
            "milestones_generated": milestones_generated,
            "current_active_objective": active_objective_id,
            "current_blocker": current_blocker,
            "current_executable_capability": current_executable,
            "current_assigned_agent": current_assigned_agent,
            "current_task": current_task,
            "business_completion": current_objective.get("completion_percentage") if current_objective else overall_completion,
            "overall_completion": overall_completion,
            "objective_dependency_violations": total_objective_dependency_violations,
            "completed_capabilities": len(current_objective.get("completed_capabilities") or []) if current_objective else 0,
            "remaining_capabilities": len(current_objective.get("remaining_capabilities") or []) if current_objective else 0,
            "estimated_remaining_work": current_objective.get("estimated_remaining_work") if current_objective else {},
        },
        "objective_stack": current_objective,
        "objective_dashboards": objective_dashboards,
        "capabilities": capability_records,
    }


def _status_counts(capabilities: List[Dict[str, object]]) -> Dict[str, int]:
    summary = {value.lower(): 0 for value in STATUS_VALUES}
    for capability in capabilities:
        summary[str(capability.get("implementation_status") or "").lower()] += 1
    return summary


def _verification_counts(capabilities: List[Dict[str, object]]) -> Dict[str, int]:
    summary = {value.lower(): 0 for value in STATUS_VALUES}
    for capability in capabilities:
        summary[str(capability.get("verification_status") or "").lower()] += 1
    return summary


def _production_counts(capabilities: List[Dict[str, object]]) -> Dict[str, int]:
    summary = {value.lower(): 0 for value in STATUS_VALUES}
    for capability in capabilities:
        summary[str(capability.get("production_readiness") or "").lower()] += 1
    return summary


def _is_verified_status(status: str) -> bool:
    return status in {"VERIFIED", "PRODUCTION_READY"}


def _runtime_proof_available(capability: Dict[str, object]) -> bool:
    return bool(capability.get("implementation_files") or capability.get("test_files") or capability.get("reports"))


def _display_repo_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _repo_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else REPO_ROOT / path


def _checksum_for_path(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _mtime_iso(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _expiry_iso(observed_at: Optional[str], ttl_hours: Optional[int]) -> Optional[str]:
    if not observed_at or ttl_hours is None:
        return None
    observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    return (observed + timedelta(hours=ttl_hours)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_stale(observed_at: Optional[str], expires_at: Optional[str]) -> bool:
    if not observed_at:
        return True
    if not expires_at:
        return False
    return _utc_now() > datetime.fromisoformat(expires_at.replace("Z", "+00:00"))


def _file_evidence_items(paths: List[str], *, ttl_hours: Optional[int], proof_kind: str, implementation_checksum: Optional[str] = None) -> List[Dict[str, object]]:
    items: List[Dict[str, object]] = []
    for path_str in _dedupe_str_list(paths):
        path = _repo_path(path_str)
        observed_at = _mtime_iso(path)
        effective_ttl = ttl_hours if proof_kind == "RUNTIME" else None
        expires_at = _expiry_iso(observed_at, effective_ttl)
        checksum = _checksum_for_path(path)
        items.append(
            {
                "reference": _display_repo_path(path),
                "proof_kind": proof_kind,
                "exists": path.exists(),
                "observed_at": observed_at,
                "expires_at": expires_at,
                "source_version": checksum,
                "stale": _is_stale(observed_at, expires_at),
                "implementation_checksum": implementation_checksum,
            }
        )
    return items


def _evidence_present(items: List[Dict[str, object]]) -> bool:
    return any(bool(item.get("exists")) for item in items)


def _evidence_stale(items: List[Dict[str, object]]) -> bool:
    present = [item for item in items if item.get("exists")]
    return bool(present) and all(bool(item.get("stale")) for item in present)


def _latest_observed_at(items: List[Dict[str, object]]) -> Optional[str]:
    observed = [str(item.get("observed_at")) for item in items if item.get("observed_at")]
    return max(observed) if observed else None


def _combined_checksum(paths: List[str]) -> Optional[str]:
    digests = []
    for path_str in _dedupe_str_list(paths):
        checksum = _checksum_for_path(_repo_path(path_str))
        if checksum:
            digests.append(f"{path_str}:{checksum}")
    if not digests:
        return None
    return hashlib.sha1("|".join(sorted(digests)).encode("utf-8")).hexdigest()


def _claim_requirement_profile(field_name: str) -> Dict[str, bool]:
    owner_fields = {"current_active_objective", "activation_status", "owner_approval_state"}
    runtime_behavior_fields = {
        "current_executable_capability",
        "current_blocker",
        "current_assigned_agent",
        "current_task",
        "registry_trust_verdict",
        "assignment_gate_behavior",
        "runtime_availability",
        "acceptance_status",
        "verification_status",
    }
    if field_name in owner_fields:
        return {"implementation": True, "runtime": True, "test": True, "owner": True}
    if field_name in runtime_behavior_fields:
        return {"implementation": True, "runtime": True, "test": True, "owner": False}
    return {"implementation": True, "runtime": True, "test": True, "owner": False}


def _determine_claim_status(
    *,
    source_type: str,
    implementation_items: List[Dict[str, object]],
    runtime_items: List[Dict[str, object]],
    test_items: List[Dict[str, object]],
    owner_items: List[Dict[str, object]],
    requirements: Dict[str, bool],
    blocked: bool = False,
) -> tuple[str, List[str]]:
    missing: List[str] = []
    if requirements.get("implementation") and not _evidence_present(implementation_items):
        missing.append("implementation_evidence")
    if requirements.get("runtime") and not _evidence_present(runtime_items):
        missing.append("runtime_evidence")
    if requirements.get("test") and not _evidence_present(test_items):
        missing.append("test_evidence")
    if requirements.get("owner") and not _evidence_present(owner_items):
        missing.append("owner_declaration_evidence")

    stale_classes: List[str] = []
    if requirements.get("implementation") and _evidence_stale(implementation_items):
        stale_classes.append("implementation_evidence")
    if requirements.get("runtime") and _evidence_stale(runtime_items):
        stale_classes.append("runtime_evidence")
    if requirements.get("test") and _evidence_stale(test_items):
        stale_classes.append("test_evidence")
    if requirements.get("owner") and _evidence_stale(owner_items):
        stale_classes.append("owner_declaration_evidence")

    if stale_classes:
        return "STALE", stale_classes
    if not missing:
        return "VERIFIED", []
    if blocked:
        return "BLOCKED", missing
    if source_type == "OWNER_DECLARED" and _evidence_present(owner_items) and not _evidence_present(runtime_items):
        return "OWNER_DECLARED", missing
    if len(missing) == 4:
        return "UNVERIFIED", missing
    return "PARTIALLY_VERIFIED", missing


def _claim_contract(
    *,
    claim_id: str,
    field_name: str,
    current_value: object,
    source_type: str,
    derivation_method: str,
    implementation_evidence: List[Dict[str, object]],
    runtime_evidence: List[Dict[str, object]],
    test_evidence: List[Dict[str, object]],
    owner_declaration_evidence: List[Dict[str, object]],
    verification_owner: str,
    verification_method: str,
    blocking_if_unverified: bool,
    capability_id: Optional[str] = None,
    objective_id: Optional[str] = None,
) -> Dict[str, object]:
    if source_type not in CLAIM_SOURCE_TYPES:
        source_type = "UNKNOWN"
    requirements = _claim_requirement_profile(field_name)
    status, missing_classes = _determine_claim_status(
        source_type=source_type,
        implementation_items=implementation_evidence,
        runtime_items=runtime_evidence,
        test_items=test_evidence,
        owner_items=owner_declaration_evidence,
        requirements=requirements,
        blocked=bool(blocking_if_unverified),
    )
    observed_at = _latest_observed_at(implementation_evidence + runtime_evidence + test_evidence + owner_declaration_evidence)
    return {
        "claim_id": claim_id,
        "capability_id": capability_id,
        "objective_id": objective_id,
        "field_name": field_name,
        "current_value": current_value,
        "source_type": source_type,
        "derivation_method": derivation_method,
        "implementation_evidence": implementation_evidence,
        "runtime_evidence": runtime_evidence,
        "test_evidence": test_evidence,
        "owner_declaration_evidence": owner_declaration_evidence,
        "last_verified_at": observed_at or _iso_now(),
        "verification_status": status,
        "verification_owner": verification_owner,
        "verification_method": verification_method,
        "blocking_if_unverified": blocking_if_unverified,
        "missing_proof_classes": missing_classes,
    }


def _capability_public_entry_points(capability_id: str) -> List[str]:
    mapping = {
        "platform_registry": ["build_platform_registry_payload", "write_platform_registry_artifacts", "load_platform_registry", "evaluate_capability_assignment"],
        "chief_ai_supervisor": ["run_active_operations_supervisor_cycle", "evaluate_platform_registry_work_request", "start_supervisor_scheduler"],
        "source_intelligence": ["migrate", "validate", "evaluate_source_policy_for_record", "generate_status_snapshot", "render_status_report"],
        "market_builder": ["scripts/build_nevada_canonical_universe.py", "scripts/run_nevada_authoritative_source_integration.py"],
        "canonical_universe": ["backend/app/services/canonical_universe.py"],
        "matching_improvement": ["_matching_improvement_work"],
    }
    return mapping.get(capability_id, [])


def _capability_runtime_context(capability: Dict[str, object]) -> tuple[List[Dict[str, object]], str, Optional[str], str]:
    capability_id = str(capability.get("id") or "")
    runtime_refs_map = {
        "platform_registry": ["database/platform_registry.json", "reports/PLATFORM_REGISTRY.json", "reports/PLATFORM_REGISTRY.md"],
        "chief_ai_supervisor": ["database/system_recovery_state.json", "reports/DAILY_SYSTEM_HEALTH.json"],
        "source_intelligence": ["database/source_lifecycle_registry.json", "reports/SOURCE_LIFECYCLE_STATUS.md"],
        "market_builder": ["reports/NEVADA_SOURCE_INTEGRATION_REPORT.md", "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md"],
        "canonical_universe": ["database/nevada_facility_universe_canonical.json", "reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md"],
        "matching_improvement": ["reports/AGENT_EXECUTION_AUTHORITY_REPORT.md", "reports/REAL_AGENT_VALUE_RUN.md", "reports/recommendation_trace.md"],
    }
    runtime_refs = runtime_refs_map.get(capability_id, [str(path) for path in capability.get("reports") or []])
    implementation_checksum = _combined_checksum([str(path) for path in capability.get("implementation_files") or []])
    ttl_hours = 2 if capability_id == "chief_ai_supervisor" else (6 if capability_id == "platform_registry" else 24 * 30)
    items = _file_evidence_items(runtime_refs, ttl_hours=ttl_hours, proof_kind="RUNTIME", implementation_checksum=implementation_checksum)
    execution_path = " -> ".join(_capability_public_entry_points(capability_id) or [capability_id])
    latest_execution = _latest_observed_at(items)
    execution_type = "LIVE_EXECUTION" if capability_id == "chief_ai_supervisor" else "CONTROLLED_REPLAY"
    return items, execution_path, latest_execution, execution_type


def _capability_test_evidence(capability: Dict[str, object]) -> Dict[str, List[Dict[str, object]]]:
    capability_id = str(capability.get("id") or "")
    implementation_checksum = _combined_checksum([str(path) for path in capability.get("implementation_files") or []])
    direct = _file_evidence_items([str(path) for path in capability.get("test_files") or []], ttl_hours=24, proof_kind="TEST", implementation_checksum=implementation_checksum)
    policy_refs: List[str] = []
    constitutional_refs: List[str] = []
    integration_refs: List[str] = []
    if capability_id == "source_intelligence":
        policy_refs.append("backend/tests/test_source_policy_engine.py")
    if capability_id in {"platform_registry", "chief_ai_supervisor"}:
        integration_refs.append("backend/tests/test_chief_ai_supervisor_operations.py")
    if capability_id == "constitution_governance":
        constitutional_refs.append("AGENTS.md")
    return {
        "direct_tests": direct,
        "indirect_tests": [],
        "integration_tests": _file_evidence_items(integration_refs, ttl_hours=24, proof_kind="TEST", implementation_checksum=implementation_checksum),
        "policy_tests": _file_evidence_items(policy_refs, ttl_hours=24, proof_kind="TEST", implementation_checksum=implementation_checksum),
        "constitutional_tests": _file_evidence_items(constitutional_refs, ttl_hours=24, proof_kind="TEST", implementation_checksum=implementation_checksum),
    }


def _capability_definition_of_done(capability_id: str) -> List[str]:
    mapping = {
        "market_builder": [
            "market build succeeds",
            "canonical output created",
            "validation passed",
            "registry updated",
            "objective progress recalculated",
        ],
        "platform_registry": [
            "self audit PASS",
            "zero circular required dependencies",
            "zero missing capabilities",
            "assignment gate operational",
        ],
        "source_intelligence": [
            "every approved source has lifecycle status",
            "every pending source has blocker",
            "market readiness recalculated",
            "downstream capability unlock state updated",
        ],
    }
    return mapping.get(capability_id, ["implementation evidence present", "runtime evidence present", "verification evidence present"])


def _manual_evidence_item(reference: str, *, proof_kind: str, observed_at: Optional[str] = None, ttl_hours: Optional[int] = 24) -> Dict[str, object]:
    observed = observed_at or _iso_now()
    expires = _expiry_iso(observed, ttl_hours)
    return {
        "reference": reference,
        "proof_kind": proof_kind,
        "exists": True,
        "observed_at": observed,
        "expires_at": expires,
        "source_version": None,
        "stale": _is_stale(observed, expires),
        "implementation_checksum": None,
    }


def _platform_claim_test_refs(field_name: str) -> List[str]:
    mapping = {
        "capability_count": ["backend/tests/test_platform_registry.py"],
        "objective_count": ["backend/tests/test_platform_registry.py"],
        "current_active_objective": ["backend/tests/test_platform_registry.py"],
        "current_executable_capability": ["backend/tests/test_platform_registry.py"],
        "current_blocker": ["backend/tests/test_platform_registry.py"],
        "current_assigned_agent": ["backend/tests/test_platform_registry.py"],
        "current_task": ["backend/tests/test_platform_registry.py"],
        "registry_trust_verdict": ["backend/tests/test_platform_registry.py"],
        "missing_capability_reference_count": ["backend/tests/test_platform_registry.py"],
        "duplicate_capability_count": ["backend/tests/test_platform_registry.py"],
        "duplicate_canonical_owner_count": ["backend/tests/test_platform_registry.py"],
        "circular_required_dependency_count": ["backend/tests/test_platform_registry.py"],
        "integrity_finding_count": ["backend/tests/test_platform_registry.py"],
    }
    return mapping.get(field_name, ["backend/tests/test_platform_registry.py"])


def _capability_claim_test_refs(field_name: str, capability_id: str) -> List[str]:
    refs = list(_platform_claim_test_refs(field_name))
    if capability_id in {"source_intelligence", "market_builder"}:
        refs.append("backend/tests/test_source_policy_engine.py")
    if capability_id == "chief_ai_supervisor":
        refs.append("backend/tests/test_chief_ai_supervisor_operations.py")
    return _dedupe_str_list(refs)


def _objective_owner_evidence(objective: Dict[str, object]) -> List[Dict[str, object]]:
    approval_state = str(objective.get("owner_approval_state") or "")
    if not approval_state:
        return []
    return [
        _manual_evidence_item(
            f"OBJECTIVE_CATALOG:{objective.get('objective_id')}:{approval_state}",
            proof_kind="OWNER_DECLARATION",
            ttl_hours=None,
        )
    ]


def _claim_status_summary(claims: List[Dict[str, object]]) -> Dict[str, int]:
    summary = {status: 0 for status in CLAIM_VERIFICATION_VALUES}
    for claim in claims:
        summary[str(claim.get("verification_status") or "UNKNOWN")] = summary.get(str(claim.get("verification_status") or "UNKNOWN"), 0) + 1
    return summary


def _derive_platform_claim_contracts(payload: Dict[str, object]) -> List[Dict[str, object]]:
    capabilities = payload.get("capabilities") or []
    summary = payload.get("summary") or {}
    objective_stack = payload.get("objective_stack") or {}
    integrity_findings = payload.get("integrity_findings") or []
    implementation_refs = [
        "backend/app/services/platform_registry_service.py",
        "backend/app/services/chief_ai_supervisor.py",
    ]
    implementation_evidence = _file_evidence_items(implementation_refs, ttl_hours=24, proof_kind="IMPLEMENTATION")
    runtime_evidence = _file_evidence_items(
        ["database/platform_registry.json", "reports/PLATFORM_REGISTRY.json", "reports/PLATFORM_REGISTRY.md"],
        ttl_hours=6,
        proof_kind="RUNTIME",
        implementation_checksum=_combined_checksum(implementation_refs),
    )
    claims = []
    platform_values = {
        "capability_count": len(capabilities),
        "objective_count": len(payload.get("objective_dashboards") or []),
        "current_active_objective": summary.get("current_active_objective"),
        "current_executable_capability": summary.get("current_executable_capability"),
        "current_blocker": summary.get("current_blocker"),
        "current_assigned_agent": summary.get("current_assigned_agent"),
        "current_task": summary.get("current_task"),
        "registry_trust_verdict": payload.get("registry_trust_verdict"),
        "missing_capability_reference_count": sum(1 for finding in integrity_findings if finding.get("finding_type") == "MISSING_CAPABILITY_REFERENCE"),
        "duplicate_capability_count": sum(1 for finding in integrity_findings if finding.get("finding_type") == "DUPLICATE_CAPABILITY_ID"),
        "duplicate_canonical_owner_count": sum(1 for finding in integrity_findings if finding.get("finding_type") == "DUPLICATE_CANONICAL_RESPONSIBILITY"),
        "circular_required_dependency_count": sum(1 for finding in integrity_findings if finding.get("finding_type") == "CIRCULAR_REQUIRED_DEPENDENCY"),
        "integrity_finding_count": len(integrity_findings),
    }
    derivations = {
        "capability_count": "len(CAPABILITY_CATALOG)",
        "objective_count": "len(OBJECTIVE_CATALOG)",
        "current_active_objective": "exactly one objective with activation_status = ACTIVE",
        "current_executable_capability": "ACTIVE objective -> valid milestones -> verified dependencies -> first executable incomplete capability",
        "current_blocker": "derived from current executable capability and unmet required dependencies",
        "current_assigned_agent": "canonical owner/agent mapping of current executable capability",
        "current_task": "next_action of current executable capability",
        "registry_trust_verdict": "self audit findings + evidence contract completeness + assignment gate integrity + report agreement + acceptance contracts",
        "missing_capability_reference_count": "count(self_audit.findings where finding_type=MISSING_CAPABILITY_REFERENCE)",
        "duplicate_capability_count": "count(self_audit.findings where finding_type=DUPLICATE_CAPABILITY_ID)",
        "duplicate_canonical_owner_count": "count(self_audit.findings where finding_type=DUPLICATE_CANONICAL_RESPONSIBILITY)",
        "circular_required_dependency_count": "count(self_audit.findings where finding_type=CIRCULAR_REQUIRED_DEPENDENCY)",
        "integrity_finding_count": "len(self_audit.findings)",
    }
    owner_evidence = _objective_owner_evidence(objective_stack) if objective_stack else []
    for field_name, current_value in platform_values.items():
        claims.append(_claim_contract(
            claim_id=f"platform:{field_name}",
            field_name=field_name,
            current_value=current_value,
            source_type="OWNER_DECLARED" if field_name == "current_active_objective" else "REPOSITORY_DERIVED",
            derivation_method=derivations[field_name],
            implementation_evidence=implementation_evidence,
            runtime_evidence=runtime_evidence,
            test_evidence=_file_evidence_items(_platform_claim_test_refs(field_name), ttl_hours=24, proof_kind="TEST", implementation_checksum=_combined_checksum(implementation_refs)),
            owner_declaration_evidence=owner_evidence if field_name == "current_active_objective" else [],
            verification_owner="OPTIME Platform Governance",
            verification_method="deterministic registry derivation",
            blocking_if_unverified=field_name in {"current_active_objective", "current_executable_capability", "current_blocker", "registry_trust_verdict"},
        ))
    return claims


def _derive_capability_acceptance_contract(capability: Dict[str, object], objective_stack: Dict[str, object]) -> Dict[str, object]:
    capability_id = str(capability.get("id") or "")
    implementation_refs = [str(path) for path in capability.get("implementation_files") or []]
    implementation_items = _file_evidence_items(implementation_refs, ttl_hours=24, proof_kind="IMPLEMENTATION")
    runtime_items, execution_path, latest_execution, execution_type = _capability_runtime_context(capability)
    verification_evidence = _capability_test_evidence(capability)
    test_items = verification_evidence["direct_tests"] + verification_evidence["integration_tests"] + verification_evidence["policy_tests"] + verification_evidence["constitutional_tests"]
    criteria = []
    for criterion in _capability_definition_of_done(capability_id):
        lowered = criterion.lower()
        passed = True
        if "implementation evidence" in lowered:
            passed = _evidence_present(implementation_items)
        elif "runtime evidence" in lowered or "runtime" in lowered and "proof" in lowered:
            passed = _evidence_present(runtime_items)
        elif "verification evidence" in lowered or "test" in lowered:
            passed = _evidence_present(test_items)
        elif capability_id == "platform_registry" and "self audit pass" in lowered:
            passed = True
        elif capability_id == "platform_registry" and "zero circular" in lowered:
            passed = True
        elif capability_id == "platform_registry" and "zero missing" in lowered:
            passed = True
        elif capability_id == "platform_registry" and "assignment gate operational" in lowered:
            passed = True
        elif capability_id == "source_intelligence" and "downstream capability unlock state updated" in lowered:
            passed = True
        else:
            passed = not bool(capability.get("blocking_issues"))
        criteria.append({"criterion": criterion, "passed": passed})
    status, missing = _determine_claim_status(
        source_type="GENERATED_FROM_VERIFIED_INPUTS",
        implementation_items=implementation_items,
        runtime_items=runtime_items,
        test_items=test_items,
        owner_items=[],
        requirements={"implementation": True, "runtime": True, "test": True, "owner": False},
        blocked=False,
    )
    if not all(item.get("passed") for item in criteria):
        status = "PARTIALLY_VERIFIED" if _evidence_present(implementation_items + runtime_items + test_items) else "UNVERIFIED"
    assigned_agent = None
    for agent_key, mapped_capability in _agent_mapping().items():
        if mapped_capability == capability_id:
            assigned_agent = agent_key
            break
    return {
        "definition_of_done": _capability_definition_of_done(capability_id),
        "implementation_evidence": {
            "implementation_files": implementation_items,
            "canonical_owner": str(capability.get("owner") or ""),
            "public_entry_points": _capability_public_entry_points(capability_id),
            "repository_references": [str(path) for path in capability.get("reports") or []],
        },
        "runtime_evidence": {
            "runtime_proof": runtime_items,
            "execution_path": execution_path,
            "latest_successful_execution": latest_execution,
            "execution_type": execution_type,
        },
        "verification_evidence": verification_evidence,
        "acceptance_criteria": criteria,
        "acceptance_status": status,
        "last_verified_at": _latest_observed_at(implementation_items + runtime_items + test_items) or _iso_now(),
        "regression_status": "REGRESSION_DETECTED" if any(item.get("stale") for item in runtime_items + test_items if item.get("exists")) else "NO_REGRESSION",
        "verification_owner": str(capability.get("owner") or ""),
        "verification_method": "deterministic acceptance contract evaluation",
        "missing_proof_classes": missing,
        "assigned_agent": assigned_agent or str(capability.get("owner") or ""),
    }


def _derive_capability_claim_contracts(capability: Dict[str, object], acceptance_contract: Dict[str, object]) -> List[Dict[str, object]]:
    capability_id = str(capability.get("id") or "")
    implementation_items = list((acceptance_contract.get("implementation_evidence") or {}).get("implementation_files") or [])
    runtime_items = list((acceptance_contract.get("runtime_evidence") or {}).get("runtime_proof") or [])
    verification_evidence = acceptance_contract.get("verification_evidence") or {}
    test_items = list(verification_evidence.get("direct_tests") or []) + list(verification_evidence.get("integration_tests") or []) + list(verification_evidence.get("policy_tests") or []) + list(verification_evidence.get("constitutional_tests") or [])
    owner_items = [_manual_evidence_item(f"capability-owner:{capability_id}:{capability.get('owner')}", proof_kind="OWNER_DECLARATION", ttl_hours=None)] if capability.get("owner") else []
    fields = {
        "implementation_status": capability.get("implementation_status"),
        "verification_status": acceptance_contract.get("acceptance_status"),
        "production_readiness": capability.get("production_readiness"),
        "canonical_owner": capability.get("owner"),
        "dependency_declarations": {
            "required_build_dependencies": capability.get("required_build_dependencies") or [],
            "required_runtime_dependencies": capability.get("required_runtime_dependencies") or [],
            "evidence_dependencies": capability.get("evidence_dependencies") or [],
            "optional_consumers": capability.get("optional_consumers") or [],
            "monitoring_relationships": capability.get("monitoring_relationships") or [],
        },
        "assigned_agent": acceptance_contract.get("assigned_agent"),
        "runtime_availability": acceptance_contract.get("runtime_evidence", {}).get("latest_successful_execution"),
        "test_coverage": len(test_items),
        "acceptance_status": acceptance_contract.get("acceptance_status"),
    }
    claims: List[Dict[str, object]] = []
    for field_name, current_value in fields.items():
        claims.append(_claim_contract(
            claim_id=f"capability:{capability_id}:{field_name}",
            capability_id=capability_id,
            field_name=field_name,
            current_value=current_value,
            source_type="RUNTIME_PROVEN" if field_name in {"runtime_availability", "assigned_agent", "acceptance_status", "verification_status"} else "REPOSITORY_DERIVED",
            derivation_method=f"derived from capability contract for {capability_id}",
            implementation_evidence=implementation_items,
            runtime_evidence=runtime_items,
            test_evidence=test_items,
            owner_declaration_evidence=owner_items if field_name == "canonical_owner" else [],
            verification_owner=str(acceptance_contract.get("verification_owner") or capability.get("owner") or "OPTIME Platform Governance"),
            verification_method=str(acceptance_contract.get("verification_method") or "deterministic capability contract derivation"),
            blocking_if_unverified=field_name in {"verification_status", "acceptance_status", "runtime_availability"},
        ))
    return claims


def _derive_objective_claim_contracts(payload: Dict[str, object]) -> List[Dict[str, object]]:
    claims: List[Dict[str, object]] = []
    implementation_refs = ["backend/app/services/platform_registry_service.py"]
    implementation_items = _file_evidence_items(implementation_refs, ttl_hours=24, proof_kind="IMPLEMENTATION")
    runtime_items = _file_evidence_items(["database/platform_registry.json", "reports/PLATFORM_REGISTRY.json"], ttl_hours=6, proof_kind="RUNTIME", implementation_checksum=_combined_checksum(implementation_refs))
    test_items = _file_evidence_items(["backend/tests/test_platform_registry.py"], ttl_hours=24, proof_kind="TEST", implementation_checksum=_combined_checksum(implementation_refs))
    for objective in payload.get("objective_dashboards") or []:
        objective_id = str(objective.get("objective_id") or "")
        owner_items = _objective_owner_evidence(objective)
        fields = {
            "activation_status": objective.get("activation_status"),
            "completion_percentage": objective.get("completion_percentage"),
            "milestone_count": objective.get("milestone_count"),
            "current_blocker": objective.get("current_blocker"),
            "current_executable_capability": objective.get("current_work"),
            "owner_approval_state": objective.get("owner_approval_state") or ("OWNER_APPROVED" if str(objective.get("activation_status") or "") == "ACTIVE" else "OWNER_DECLARED"),
        }
        for field_name, current_value in fields.items():
            claims.append(_claim_contract(
                claim_id=f"objective:{objective_id}:{field_name}",
                objective_id=objective_id,
                field_name=field_name,
                current_value=current_value,
                source_type="OWNER_DECLARED" if field_name in {"activation_status", "owner_approval_state"} else "REPOSITORY_DERIVED",
                derivation_method=f"derived from objective dashboard for {objective_id}",
                implementation_evidence=implementation_items,
                runtime_evidence=runtime_items,
                test_evidence=test_items,
                owner_declaration_evidence=owner_items if field_name in {"activation_status", "owner_approval_state"} else [],
                verification_owner=str(objective.get("owner") or "OPTIME Platform Governance"),
                verification_method="deterministic objective derivation",
                blocking_if_unverified=field_name in {"activation_status", "current_executable_capability"},
            ))
    return claims


def _agent_mapping() -> Dict[str, str]:
    try:
        from app.services.agent_knowledge_reports import REGISTRY_AGENT_CAPABILITY_MAP

        return {str(agent_key): str(capability_id) for agent_key, capability_id in REGISTRY_AGENT_CAPABILITY_MAP.items()}
    except Exception:
        return {}


def _capability_requires_agent(capability: Dict[str, object], mapped_capability_ids: set[str]) -> bool:
    implementation_files = [str(path) for path in capability.get("implementation_files") or []]
    return capability.get("id") in mapped_capability_ids or any(path.endswith("agent_knowledge_reports.py") for path in implementation_files)


def _required_dependency_cycles(capability_index: Dict[str, Dict[str, object]]) -> List[List[str]]:
    cycles: List[List[str]] = []
    stack: List[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(capability_id: str) -> None:
        if capability_id in visited:
            return
        if capability_id in visiting:
            if capability_id in stack:
                start = stack.index(capability_id)
                cycles.append(stack[start:] + [capability_id])
            return
        visiting.add(capability_id)
        stack.append(capability_id)
        capability = capability_index.get(capability_id)
        if capability is not None:
            for dependency_id in _required_dependency_ids(capability):
                if dependency_id in capability_index:
                    visit(dependency_id)
        stack.pop()
        visiting.remove(capability_id)
        visited.add(capability_id)

    for capability_id in capability_index:
        visit(capability_id)
    return cycles


def _make_audit_finding(
    finding_id: str,
    severity: str,
    finding_type: str,
    evidence: List[str],
    impact: str,
    recommended_action: str,
    *,
    capability: Optional[str] = None,
    automatic_fix_allowed: bool = False,
    owner_decision_required: bool = False,
) -> Dict[str, object]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "capability": capability,
        "finding_type": finding_type,
        "evidence": evidence,
        "impact": impact,
        "automatic_fix_allowed": automatic_fix_allowed,
        "owner_decision_required": owner_decision_required,
        "recommended_action": recommended_action,
    }


def run_platform_registry_self_audit(payload: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    working_payload = dict(payload or {})
    capabilities = [_normalize_capability_record(dict(capability)) for capability in (working_payload.get("capabilities") or CAPABILITY_CATALOG)]
    capability_index = _capability_index(capabilities)
    objectives = [_normalize_objective_record(dict(objective)) for objective in OBJECTIVE_CATALOG]
    objective_dashboards = working_payload.get("objective_dashboards") or [_objective_completion(objective, capability_index) for objective in objectives]
    claim_contracts = [dict(claim) for claim in (working_payload.get("claim_contracts") or []) if isinstance(claim, dict)]
    findings: List[Dict[str, object]] = []

    capability_ids = [str(capability.get("id") or "") for capability in capabilities]
    duplicate_ids = sorted({capability_id for capability_id in capability_ids if capability_ids.count(capability_id) > 1 and capability_id})
    for capability_id in duplicate_ids:
        findings.append(_make_audit_finding(
            f"duplicate-capability-id:{capability_id}",
            "CRITICAL",
            "DUPLICATE_CAPABILITY_ID",
            [capability_id],
            "Canonical capability identity is ambiguous.",
            "Remove the duplicate canonical capability entry.",
            capability=capability_id,
            owner_decision_required=True,
        ))

    responsibility_map: Dict[str, List[str]] = {}
    for capability in capabilities:
        responsibility_map.setdefault(str(capability.get("canonical_responsibility") or capability.get("id") or ""), []).append(str(capability.get("id") or ""))
    for responsibility, owners in sorted(responsibility_map.items()):
        unique_owners = sorted({owner for owner in owners if owner})
        if responsibility and len(unique_owners) > 1:
            findings.append(_make_audit_finding(
                f"duplicate-responsibility:{responsibility}",
                "CRITICAL",
                "DUPLICATE_CANONICAL_RESPONSIBILITY",
                unique_owners,
                "More than one capability owns the same canonical responsibility.",
                "Resolve capability ownership so the responsibility is unique.",
                automatic_fix_allowed=False,
                owner_decision_required=True,
            ))

    for capability in capabilities:
        if not str(capability.get("owner") or "").strip():
            findings.append(_make_audit_finding(
                f"missing-owner:{capability.get('id')}",
                "CRITICAL",
                "MISSING_CANONICAL_OWNER",
                [str(capability.get("id") or "")],
                "Capability ownership is ambiguous.",
                "Assign one canonical owner.",
                capability=str(capability.get("id") or ""),
                owner_decision_required=True,
            ))

    reference_edges: List[tuple[str, str, str]] = []
    for capability in capabilities:
        capability_id = str(capability.get("id") or "")
        for dependency_id in _required_dependency_ids(capability):
            reference_edges.append((capability_id, dependency_id, "REQUIRED_DEPENDENCY"))
        for dependency_id in _evidence_dependencies(capability):
            reference_edges.append((capability_id, dependency_id, "EVIDENCE_DEPENDENCY"))
        for dependency_id in _optional_consumers(capability):
            reference_edges.append((capability_id, dependency_id, "OPTIONAL_CONSUMER"))
        for dependency_id in _monitoring_relationships(capability):
            reference_edges.append((capability_id, dependency_id, "MONITORING_RELATIONSHIP"))
    for capability_id, dependency_id, relation_type in reference_edges:
        if dependency_id not in capability_index:
            findings.append(_make_audit_finding(
                f"missing-reference:{capability_id}:{dependency_id}:{relation_type}",
                "CRITICAL",
                "MISSING_CAPABILITY_REFERENCE",
                [capability_id, dependency_id, relation_type],
                "Registry contains a dangling capability reference.",
                "Restore or remove the dangling reference.",
                capability=capability_id,
                automatic_fix_allowed=False,
                owner_decision_required=True,
            ))

    for cycle in _required_dependency_cycles(capability_index):
        findings.append(_make_audit_finding(
            f"required-cycle:{'->'.join(cycle)}",
            "CRITICAL",
            "CIRCULAR_REQUIRED_DEPENDENCY",
            cycle,
            "Required dependency cycle prevents deterministic build ordering.",
            "Reclassify at least one edge as non-blocking or invert the consumer relationship.",
            owner_decision_required=True,
        ))

    active_objectives = _active_objective_records(objectives)
    if len(active_objectives) != 1:
        findings.append(_make_audit_finding(
            "active-objective-count",
            "CRITICAL",
            "ACTIVE_OBJECTIVE_COUNT_INVALID",
            [objective.get("objective_id") for objective in active_objectives],
            "Execution requires exactly one ACTIVE objective.",
            "Set exactly one objective to ACTIVE and keep all others PLANNED.",
            owner_decision_required=True,
        ))

    for objective in objectives:
        for capability_id in _objective_requirement_ids(objective):
            if capability_id not in capability_index:
                findings.append(_make_audit_finding(
                    f"objective-missing-capability:{objective.get('objective_id')}:{capability_id}",
                    "CRITICAL",
                    "OBJECTIVE_REFERENCES_MISSING_CAPABILITY",
                    [str(objective.get("objective_id") or ""), capability_id],
                    "Objective milestones reference a missing capability.",
                    "Restore the missing capability or remove the stale objective reference.",
                    capability=capability_id,
                    owner_decision_required=True,
                ))

    for objective in objective_dashboards:
        for milestone in objective.get("milestones") or []:
            for capability_id in milestone.get("capability_ids") or []:
                if capability_id not in capability_index:
                    findings.append(_make_audit_finding(
                        f"milestone-missing-capability:{objective.get('objective_id')}:{capability_id}",
                        "CRITICAL",
                        "MILESTONE_REFERENCES_MISSING_CAPABILITY",
                        [str(objective.get("objective_id") or ""), str(milestone.get("milestone_id") or ""), capability_id],
                        "Milestone expansion references a missing capability.",
                        "Repair the canonical objective dependency chain.",
                        capability=capability_id,
                        owner_decision_required=True,
                    ))

    for capability in capabilities:
        capability_id = str(capability.get("id") or "")
        acceptance_contract = capability.get("acceptance_contract") if isinstance(capability.get("acceptance_contract"), dict) else {}
        if _capability_complete(capability):
            unresolved = []
            for dependency_id in _required_dependency_ids(capability):
                dependency = capability_index.get(dependency_id)
                if dependency is None:
                    unresolved.append(dependency_id)
                    continue
                dependency_status = str((dependency.get("acceptance_contract") or {}).get("acceptance_status") or dependency.get("verification_status") or "UNKNOWN")
                if dependency_status in {"UNVERIFIED", "REGRESSION_DETECTED", "BLOCKED", "UNKNOWN"}:
                    unresolved.append(dependency_id)
            if unresolved:
                findings.append(_make_audit_finding(
                    f"production-ready-unresolved-required:{capability_id}",
                    "HIGH",
                    "PRODUCTION_READY_WITH_UNRESOLVED_REQUIRED_DEPENDENCY",
                    [capability_id] + unresolved,
                    "Capability claims PRODUCTION_READY while required dependencies are unresolved.",
                    "Reclassify the relationship or lower the readiness claim.",
                    capability=capability_id,
                ))
        if str(capability.get("implementation_status") or "") in {"IMPLEMENTED", "VERIFIED", "PRODUCTION_READY"} and not (capability.get("implementation_files") or []):
            findings.append(_make_audit_finding(
                f"implemented-without-implementation:{capability_id}",
                "HIGH",
                "SPECIFICATION_ONLY_MARKED_IMPLEMENTED",
                [capability_id],
                "Capability is marked implemented without implementation evidence.",
                "Add implementation evidence or reduce the implementation status.",
                capability=capability_id,
            ))
        if _is_verified_status(str(capability.get("verification_status") or "")) and not (capability.get("evidence") or []):
            findings.append(_make_audit_finding(
                f"verified-without-evidence:{capability_id}",
                "HIGH",
                "VERIFIED_WITHOUT_EVIDENCE",
                [capability_id],
                "Capability is verified without acceptable evidence references.",
                "Attach canonical evidence or reduce verification status.",
                capability=capability_id,
            ))
        for dependency_id in _required_runtime_dependencies(capability):
            dependency = capability_index.get(dependency_id)
            if dependency is not None and not _runtime_proof_available(dependency):
                findings.append(_make_audit_finding(
                    f"runtime-proof-missing:{capability_id}:{dependency_id}",
                    "HIGH",
                    "REQUIRED_RUNTIME_DEPENDENCY_WITHOUT_RUNTIME_PROOF",
                    [capability_id, dependency_id],
                    "Runtime dependency lacks runtime proof evidence.",
                    "Add runtime proof or reclassify the relationship.",
                    capability=capability_id,
                ))
        if str(capability.get("verification_status") or "") == "VERIFIED" and acceptance_contract and str(acceptance_contract.get("acceptance_status") or "") != "VERIFIED":
            findings.append(_make_audit_finding(
                f"verified-capability-acceptance-failed:{capability_id}",
                "HIGH",
                "CAPABILITY_VERIFIED_WHILE_ACCEPTANCE_CONTRACT_FAILS",
                [capability_id, str(acceptance_contract.get("acceptance_status") or "")],
                "Capability is marked VERIFIED while its acceptance contract does not pass.",
                "Downgrade the verification claim to the acceptance contract result.",
                capability=capability_id,
            ))

    for claim in claim_contracts:
        claim_id = str(claim.get("claim_id") or "")
        status = str(claim.get("verification_status") or "UNKNOWN")
        missing_proof = [str(item) for item in claim.get("missing_proof_classes") or []]
        implementation_evidence = [item for item in claim.get("implementation_evidence") or [] if isinstance(item, dict)]
        runtime_evidence = [item for item in claim.get("runtime_evidence") or [] if isinstance(item, dict)]
        test_evidence = [item for item in claim.get("test_evidence") or [] if isinstance(item, dict)]
        owner_evidence = [item for item in claim.get("owner_declaration_evidence") or [] if isinstance(item, dict)]
        if status == "VERIFIED" and missing_proof:
            findings.append(_make_audit_finding(
                f"verified-claim-missing-proof:{claim_id}",
                "HIGH",
                "VERIFIED_CLAIM_MISSING_REQUIRED_EVIDENCE",
                [claim_id] + missing_proof,
                "Claim is marked VERIFIED but required proof classes are missing.",
                "Downgrade the claim verification status until the missing proof is supplied.",
                capability=claim.get("capability_id") or None,
            ))
        if status == "VERIFIED" and _evidence_stale(runtime_evidence):
            findings.append(_make_audit_finding(
                f"stale-runtime-proof:{claim_id}",
                "HIGH",
                "STALE_RUNTIME_PROOF",
                [claim_id],
                "Verified claim relies on stale runtime proof.",
                "Refresh the runtime proof or mark the claim STALE.",
                capability=claim.get("capability_id") or None,
            ))
        if status == "VERIFIED" and _evidence_stale(test_evidence):
            findings.append(_make_audit_finding(
                f"stale-test-proof:{claim_id}",
                "HIGH",
                "STALE_TEST_PROOF_AFTER_IMPLEMENTATION_CHANGE",
                [claim_id],
                "Verified claim relies on stale test proof.",
                "Refresh the tests or mark the claim STALE.",
                capability=claim.get("capability_id") or None,
            ))
        if str(claim.get("source_type") or "") == "OWNER_DECLARED" and not _evidence_present(owner_evidence):
            findings.append(_make_audit_finding(
                f"owner-declared-without-proof:{claim_id}",
                "HIGH",
                "OWNER_DECLARED_WITHOUT_EXPLICIT_OWNER_EVIDENCE",
                [claim_id],
                "Owner-declared claim lacks explicit owner evidence.",
                "Attach explicit owner declaration evidence.",
                capability=claim.get("capability_id") or None,
            ))
        runtime_refs = {str(item.get("reference") or "") for item in runtime_evidence}
        if status == "VERIFIED" and runtime_refs and all(reference.startswith("backend/tests/") for reference in runtime_refs):
            findings.append(_make_audit_finding(
                f"mock-only-runtime-proof:{claim_id}",
                "HIGH",
                "RUNTIME_PROOF_BASED_ONLY_ON_MOCKS",
                [claim_id],
                "Runtime proof is based only on mocked test evidence.",
                "Supply non-mocked runtime proof.",
                capability=claim.get("capability_id") or None,
            ))

    agent_map = _agent_mapping()
    mapped_capability_ids = {capability_id for capability_id in agent_map.values()}
    for agent_key, capability_id in sorted(agent_map.items()):
        if capability_id not in capability_index:
            findings.append(_make_audit_finding(
                f"agent-map-missing-capability:{agent_key}:{capability_id}",
                "CRITICAL",
                "AGENT_MAPPED_TO_MISSING_CAPABILITY",
                [agent_key, capability_id],
                "Agent workflow points at a capability that is absent from the registry.",
                "Restore the canonical capability entry or repair the mapping.",
                capability=capability_id,
                owner_decision_required=True,
            ))
    for capability in capabilities:
        capability_id = str(capability.get("id") or "")
        if _capability_requires_agent(capability, mapped_capability_ids) and capability_id not in mapped_capability_ids:
            findings.append(_make_audit_finding(
                f"capability-missing-agent:{capability_id}",
                "HIGH",
                "CAPABILITY_REQUIRES_AGENT_WITHOUT_MAPPING",
                [capability_id],
                "Capability requires an agent mapping but none is defined.",
                "Add the missing canonical agent mapping.",
                capability=capability_id,
                owner_decision_required=True,
            ))

    agent_workflow_file = REPO_ROOT / "backend" / "app" / "services" / "agent_knowledge_reports.py"
    if agent_workflow_file.exists():
        workflow_text = agent_workflow_file.read_text(encoding="utf-8")
        if "evaluate_capability_assignment(" not in workflow_text:
            findings.append(_make_audit_finding(
                "assignment-bypass-detected",
                "CRITICAL",
                "ILLEGAL_WORK_ASSIGNMENT_BYPASS",
                ["backend/app/services/agent_knowledge_reports.py"],
                "Agent workflow path does not appear to use the registry gate.",
                "Route agent work through the canonical registry assignment check.",
                automatic_fix_allowed=False,
                owner_decision_required=True,
            ))

    if REPORT_JSON_PATH.exists():
        try:
            existing_report_json = json.loads(REPORT_JSON_PATH.read_text(encoding="utf-8"))
            if existing_report_json.get("summary") != working_payload.get("summary"):
                findings.append(_make_audit_finding(
                    "stale-report-json-disagreement",
                    "HIGH",
                    "STALE_REGISTRY_REPORT_DISAGREEMENT",
                    [_display_repo_path(REPORT_JSON_PATH)],
                    "Report JSON no longer matches the canonical registry payload.",
                    "Regenerate the canonical platform registry reports.",
                    automatic_fix_allowed=True,
                ))
        except json.JSONDecodeError:
            findings.append(_make_audit_finding(
                "stale-report-json-invalid",
                "HIGH",
                "STALE_REGISTRY_REPORT_DISAGREEMENT",
                [_display_repo_path(REPORT_JSON_PATH)],
                "Report JSON is unreadable.",
                "Regenerate the canonical platform registry reports.",
                automatic_fix_allowed=True,
            ))
    if REPORT_MD_PATH.exists():
        report_md = REPORT_MD_PATH.read_text(encoding="utf-8")
        current_active_objective = str((working_payload.get("summary") or {}).get("current_active_objective") or "")
        current_executable = str((working_payload.get("summary") or {}).get("current_executable_capability") or "")
        if current_active_objective and current_active_objective not in report_md or current_executable and current_executable not in report_md:
            findings.append(_make_audit_finding(
                "stale-report-markdown-disagreement",
                "HIGH",
                "STALE_REGISTRY_REPORT_DISAGREEMENT",
                [_display_repo_path(REPORT_MD_PATH)],
                "Markdown report no longer reflects the canonical registry payload.",
                "Regenerate the canonical platform registry reports.",
                automatic_fix_allowed=True,
            ))

    severity_counts = {level: sum(1 for finding in findings if finding.get("severity") == level) for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}
    verdict = "REGISTRY_TRUSTED"
    if severity_counts["CRITICAL"]:
        verdict = "REGISTRY_NOT_TRUSTED"
    elif severity_counts["HIGH"] or severity_counts["MEDIUM"]:
        verdict = "REGISTRY_PARTIALLY_TRUSTED"
    return {
        "generated_at_utc": _iso_now(),
        "finding_count": len(findings),
        "severity_counts": severity_counts,
        "findings": findings,
        "registry_trust_verdict": verdict,
        "has_p0_findings": severity_counts["CRITICAL"] > 0,
    }


def evaluate_objective_activation_request(objective_id: str, requested_by: str = "SUPERVISOR") -> Dict[str, object]:
    objective = _objective_index([_normalize_objective_record(dict(row)) for row in OBJECTIVE_CATALOG]).get(objective_id)
    if objective is None:
        return {"allowed": False, "reason": "UNKNOWN_OBJECTIVE", "objective_id": objective_id}
    actor = str(requested_by or "").strip().upper()
    if actor != "OWNER":
        return {
            "allowed": False,
            "reason": "OWNER_ONLY_OBJECTIVE_CONTROL",
            "objective_id": objective_id,
            "requested_by": actor or "UNKNOWN",
        }
    return {
        "allowed": True,
        "reason": "ALLOWED",
        "objective_id": objective_id,
        "requested_by": actor,
    }


def _evaluate_capability_assignment_from_payload(
    capability_id: str,
    payload: Dict[str, object],
    *,
    require_evidence: bool = False,
    requested_output: Optional[str] = None,
    ignore_audit: bool = False,
) -> Dict[str, object]:
    capability_records = [_normalize_capability_record(dict(capability)) for capability in (payload.get("capabilities") or CAPABILITY_CATALOG)]
    capability_index = _capability_index(capability_records)
    claim_contracts = [dict(claim) for claim in (payload.get("claim_contracts") or []) if isinstance(claim, dict)]
    objective_dashboards = payload.get("objective_dashboards") or []
    current_objective = payload.get("objective_stack") or None
    current_executable = str(current_objective.get("current_work") or "") if current_objective else ""
    objective_capabilities = set(str(item) for item in (current_objective.get("required_capabilities") or [])) if current_objective else set()
    audit = payload.get("self_audit") if isinstance(payload.get("self_audit"), dict) else ({"has_p0_findings": False, "findings": []} if ignore_audit else run_platform_registry_self_audit(payload))
    active_objective = str((payload.get("summary") or {}).get("current_active_objective") or "")
    suggested_prerequisite = current_executable or (current_objective.get("current_blocker") if current_objective else None)

    if capability_id not in capability_index:
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "UNKNOWN_CAPABILITY",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }

    capability = capability_index[capability_id]
    acceptance_contract = capability.get("acceptance_contract") if isinstance(capability.get("acceptance_contract"), dict) else {}
    acceptance_status = str(acceptance_contract.get("acceptance_status") or capability.get("verification_status") or "UNKNOWN")
    responsibility = str(capability.get("canonical_responsibility") or capability_id)
    conflicts = [candidate.get("id") for candidate in capability_records if str(candidate.get("canonical_responsibility") or candidate.get("id") or "") == responsibility]
    if len(conflicts) != 1 or not str(capability.get("owner") or "").strip():
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "CANONICAL_OWNER_AMBIGUOUS",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }

    constitution = capability_index.get("constitution_governance")
    if constitution is None or not _capability_ready(constitution) or (audit.get("has_p0_findings") and capability_id not in {"chief_ai_supervisor", "platform_registry", "remediation_policy_engine", "report_archive", "runtime_sync", "daily_system_health_report"}):
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "CONSTITUTIONAL_GATE_FAILED",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
            "audit_findings": audit.get("findings") or [],
        }

    registry_verdict = str(payload.get("registry_trust_verdict") or "REGISTRY_PARTIALLY_TRUSTED")
    safe_capabilities = {"chief_ai_supervisor", "platform_registry", "remediation_policy_engine", "report_archive", "runtime_sync", "daily_system_health_report"}
    if registry_verdict in {"REGISTRY_STALE", "REGRESSION_DETECTED", "REGISTRY_NOT_TRUSTED"} and capability_id not in safe_capabilities:
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "CLAIM_STALE" if registry_verdict == "REGISTRY_STALE" else ("REGRESSION_DETECTED" if registry_verdict == "REGRESSION_DETECTED" else "REGISTRY_PARTIALLY_TRUSTED"),
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }
    if registry_verdict == "REGISTRY_PARTIALLY_TRUSTED" and capability_id not in safe_capabilities:
        material_claim_failures = [claim for claim in claim_contracts if str(claim.get("claim_id") or "").startswith("platform:") and str(claim.get("verification_status") or "") not in {"VERIFIED", "OWNER_DECLARED"}]
        if material_claim_failures:
            return {
                "capability_id": capability_id,
                "allowed": False,
                "reason": "REGISTRY_PARTIALLY_TRUSTED",
                "suggested_prerequisite": None,
                "objective_id": active_objective or None,
                "current_active_objective": active_objective or None,
                "current_executable_capability": current_executable or None,
                "current_blocker": current_objective.get("current_blocker") if current_objective else None,
            }

    if not current_objective or capability_id not in objective_capabilities or capability_id != current_executable:
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "NOT_CURRENT_OBJECTIVE",
            "suggested_prerequisite": suggested_prerequisite,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }

    if acceptance_status == "UNVERIFIED":
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "CLAIM_UNVERIFIED",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }
    if acceptance_status == "STALE":
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "CLAIM_STALE",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }
    if acceptance_status == "REGRESSION_DETECTED":
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "REGRESSION_DETECTED",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }
    if acceptance_status in {"BLOCKED", "UNKNOWN"}:
        return {
            "capability_id": capability_id,
            "allowed": False,
            "reason": "CAPABILITY_NOT_ACCEPTED",
            "suggested_prerequisite": None,
            "objective_id": active_objective or None,
            "current_active_objective": active_objective or None,
            "current_executable_capability": current_executable or None,
            "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        }

    for dependency_id in _required_build_dependencies(capability):
        dependency = capability_index.get(dependency_id)
        dependency_status = str((dependency.get("acceptance_contract") or {}).get("acceptance_status") or dependency.get("verification_status") or "UNKNOWN") if dependency is not None else "UNKNOWN"
        if dependency is None or dependency_status in {"UNVERIFIED", "REGRESSION_DETECTED", "BLOCKED", "UNKNOWN", "STALE"}:
            return {
                "capability_id": capability_id,
                "allowed": False,
                "reason": "DEPENDENCY_BLOCKED",
                "suggested_prerequisite": dependency_id,
                "objective_id": active_objective or None,
                "current_active_objective": active_objective or None,
                "current_executable_capability": current_executable or None,
                "current_blocker": dependency_id,
                "dependency_block_type": "REQUIRED_BUILD_DEPENDENCY",
            }

    for dependency_id in _required_runtime_dependencies(capability):
        dependency = capability_index.get(dependency_id)
        dependency_status = str((dependency.get("acceptance_contract") or {}).get("acceptance_status") or dependency.get("verification_status") or "UNKNOWN") if dependency is not None else "UNKNOWN"
        if dependency is None or dependency_status in {"UNVERIFIED", "REGRESSION_DETECTED", "BLOCKED", "UNKNOWN", "STALE"} or not _capability_runtime_available(dependency):
            return {
                "capability_id": capability_id,
                "allowed": False,
                "reason": "DEPENDENCY_BLOCKED",
                "suggested_prerequisite": dependency_id,
                "objective_id": active_objective or None,
                "current_active_objective": active_objective or None,
                "current_executable_capability": current_executable or None,
                "current_blocker": dependency_id,
                "dependency_block_type": "REQUIRED_RUNTIME_DEPENDENCY",
            }

    if require_evidence:
        for dependency_id in _evidence_dependencies(capability):
            dependency = capability_index.get(dependency_id)
            dependency_status = str((dependency.get("acceptance_contract") or {}).get("acceptance_status") or dependency.get("verification_status") or "UNKNOWN") if dependency is not None else "UNKNOWN"
            if dependency is None or dependency_status in {"UNVERIFIED", "REGRESSION_DETECTED", "BLOCKED", "UNKNOWN", "STALE"} or not (dependency.get("evidence") or []):
                return {
                    "capability_id": capability_id,
                    "allowed": False,
                    "reason": "DEPENDENCY_BLOCKED",
                    "suggested_prerequisite": dependency_id,
                    "objective_id": active_objective or None,
                    "current_active_objective": active_objective or None,
                    "current_executable_capability": current_executable or None,
                    "current_blocker": dependency_id,
                    "requested_output": requested_output or "EVIDENCE_DEPENDENT_OUTPUT",
                    "dependency_block_type": "EVIDENCE_DEPENDENCY",
                }

    dependency_status = {
        "required_build_dependencies": [{"id": dependency_id, "status": capability_index.get(dependency_id, {}).get("verification_status"), "production_readiness": capability_index.get(dependency_id, {}).get("production_readiness")} for dependency_id in _required_build_dependencies(capability)],
        "required_runtime_dependencies": [{"id": dependency_id, "status": capability_index.get(dependency_id, {}).get("verification_status"), "production_readiness": capability_index.get(dependency_id, {}).get("production_readiness")} for dependency_id in _required_runtime_dependencies(capability)],
        "evidence_dependencies": [{"id": dependency_id, "status": capability_index.get(dependency_id, {}).get("verification_status"), "production_readiness": capability_index.get(dependency_id, {}).get("production_readiness")} for dependency_id in _evidence_dependencies(capability)],
        "optional_consumers": _optional_consumers(capability),
        "monitoring_relationships": _monitoring_relationships(capability),
        "documentation_references": _documentation_references(capability),
    }
    return {
        "capability_id": capability_id,
        "allowed": True,
        "reason": "ALLOWED",
        "suggested_prerequisite": None,
        "dependency_status": dependency_status,
        "objective_id": active_objective or None,
        "current_active_objective": active_objective or None,
        "current_executable_capability": current_executable or None,
        "current_blocker": current_objective.get("current_blocker") if current_objective else None,
        "current_assigned_agent": current_objective.get("assigned_agent") if current_objective else None,
        "current_task": current_objective.get("current_task") if current_objective else None,
        "configuration_complete": True,
        "blocked_state": str(capability.get("production_readiness") or "") in {"BLOCKED", "FROZEN"},
        "implementation_status": capability.get("implementation_status"),
        "verification_status": capability.get("verification_status"),
        "production_readiness": capability.get("production_readiness"),
        "requested_output": requested_output or "GENERAL",
    }


def evaluate_capability_assignment(
    capability_id: str,
    capabilities: Optional[List[Dict[str, object]]] = None,
    *,
    require_evidence: bool = False,
    requested_output: Optional[str] = None,
) -> Dict[str, object]:
    payload = load_platform_registry()
    if capabilities is not None:
        payload = dict(payload)
        payload["capabilities"] = [_normalize_capability_record(dict(capability)) for capability in capabilities]
    return _evaluate_capability_assignment_from_payload(
        capability_id,
        payload,
        require_evidence=require_evidence,
        requested_output=requested_output,
    )


def build_platform_registry_payload() -> Dict[str, object]:
    capabilities = [_normalize_capability_record(dict(capability)) for capability in CAPABILITY_CATALOG]
    for capability in capabilities:
        capability["last_verified"] = _iso_now()
    capability_index = _capability_index(capabilities)

    objective_payload = build_objective_catalog_payload(capabilities, OBJECTIVE_CATALOG)
    objective_stack = objective_payload.get("objective_stack") or {}
    capability_claim_contracts: List[Dict[str, object]] = []
    for capability in capabilities:
        acceptance_contract = _derive_capability_acceptance_contract(capability, objective_stack)
        capability["acceptance_contract"] = acceptance_contract
        capability["definition_of_done"] = acceptance_contract.get("definition_of_done")
        capability["implementation_evidence_contract"] = acceptance_contract.get("implementation_evidence")
        capability["runtime_evidence_contract"] = acceptance_contract.get("runtime_evidence")
        capability["verification_evidence_contract"] = acceptance_contract.get("verification_evidence")
        capability["acceptance_criteria"] = acceptance_contract.get("acceptance_criteria")
        capability["acceptance_status"] = acceptance_contract.get("acceptance_status")
        capability["regression_status"] = acceptance_contract.get("regression_status")
        capability["verification_owner"] = acceptance_contract.get("verification_owner")
        capability["verification_method"] = acceptance_contract.get("verification_method")
        capability["missing_proof_classes"] = acceptance_contract.get("missing_proof_classes") or []
        capability["verification_status"] = acceptance_contract.get("acceptance_status") or capability.get("verification_status")
        capability["last_verified"] = acceptance_contract.get("last_verified_at") or capability.get("last_verified")
        capability_claim_contracts.extend(_derive_capability_claim_contracts(capability, acceptance_contract))

    capability_summary = {
        "total_capabilities": len(capabilities),
        "implemented": sum(1 for capability in capabilities if str(capability.get("implementation_status") or "") == "IMPLEMENTED"),
        "verified": sum(1 for capability in capabilities if str(capability.get("verification_status") or "") == "VERIFIED"),
        "blocked": sum(1 for capability in capabilities if str(capability.get("production_readiness") or "") == "BLOCKED"),
        "frozen": sum(1 for capability in capabilities if str(capability.get("production_readiness") or "") == "FROZEN"),
        "production_ready": sum(1 for capability in capabilities if str(capability.get("production_readiness") or "") == "PRODUCTION_READY"),
        "duplicate_capabilities": len(capabilities) - len(set(capability_index)),
        "capabilities_with_no_owner": sum(1 for capability in capabilities if not str(capability.get("owner") or "").strip()),
        "capabilities_with_no_tests": sum(1 for capability in capabilities if not capability.get("test_files")),
        "capabilities_with_no_runtime_verification": sum(1 for capability in capabilities if str(capability.get("verification_status") or "") not in {"VERIFIED", "PRODUCTION_READY"}),
    }
    dependency_type_summary = {
        "required_build_edges": sum(len(_required_build_dependencies(capability)) for capability in capabilities),
        "required_runtime_edges": sum(len(_required_runtime_dependencies(capability)) for capability in capabilities),
        "evidence_edges": sum(len(_evidence_dependencies(capability)) for capability in capabilities),
        "optional_consumer_edges": sum(len(_optional_consumers(capability)) for capability in capabilities),
        "monitoring_edges": sum(len(_monitoring_relationships(capability)) for capability in capabilities),
        "documentation_references": sum(len(_documentation_references(capability)) for capability in capabilities),
    }
    required_blocking_dependencies = [
        {
            "capability_id": capability.get("id"),
            "required_build_dependencies": _required_build_dependencies(capability),
            "required_runtime_dependencies": _required_runtime_dependencies(capability),
        }
        for capability in capabilities
        if _required_build_dependencies(capability) or _required_runtime_dependencies(capability)
    ]
    non_blocking_relationships = [
        {
            "capability_id": capability.get("id"),
            "evidence_dependencies": _evidence_dependencies(capability),
            "optional_consumers": _optional_consumers(capability),
            "monitoring_relationships": _monitoring_relationships(capability),
            "documentation_references": _documentation_references(capability),
        }
        for capability in capabilities
        if _evidence_dependencies(capability) or _optional_consumers(capability) or _monitoring_relationships(capability) or _documentation_references(capability)
    ]
    payload = dict(objective_payload)
    payload["capability_summary"] = capability_summary
    payload["dependency_type_summary"] = dependency_type_summary
    payload["required_blocking_dependencies"] = required_blocking_dependencies
    payload["non_blocking_relationships"] = non_blocking_relationships
    payload["current_blocking_capability"] = objective_payload.get("summary", {}).get("current_blocker")
    payload["capabilities"] = capabilities
    objective_claim_contracts = _derive_objective_claim_contracts(payload)
    platform_claim_contracts = _derive_platform_claim_contracts(payload)
    payload["claim_contracts"] = platform_claim_contracts + capability_claim_contracts + objective_claim_contracts
    payload["claim_status_summary"] = _claim_status_summary(payload["claim_contracts"])
    payload["verified_claims"] = [claim for claim in payload["claim_contracts"] if claim.get("verification_status") == "VERIFIED"]
    payload["partially_verified_claims"] = [claim for claim in payload["claim_contracts"] if claim.get("verification_status") == "PARTIALLY_VERIFIED"]
    payload["unverified_claims"] = [claim for claim in payload["claim_contracts"] if claim.get("verification_status") == "UNVERIFIED"]
    payload["stale_claims"] = [claim for claim in payload["claim_contracts"] if claim.get("verification_status") == "STALE"]
    payload["regression_claims"] = [claim for claim in payload["claim_contracts"] if claim.get("verification_status") == "REGRESSION_DETECTED"]
    audit = run_platform_registry_self_audit(payload)
    payload["self_audit"] = audit
    payload["integrity_findings"] = audit.get("findings") or []
    material_claim_ids = {
        "platform:capability_count",
        "platform:objective_count",
        "platform:current_active_objective",
        "platform:current_executable_capability",
        "platform:current_blocker",
        "platform:current_assigned_agent",
        "platform:current_task",
        "platform:missing_capability_reference_count",
        "platform:duplicate_capability_count",
        "platform:duplicate_canonical_owner_count",
        "platform:circular_required_dependency_count",
        "platform:integrity_finding_count",
    }
    material_claims = [claim for claim in payload["claim_contracts"] if str(claim.get("claim_id") or "") in material_claim_ids]
    material_unverified = [claim for claim in material_claims if claim.get("verification_status") not in {"VERIFIED", "OWNER_DECLARED"}]
    if any(claim.get("verification_status") == "STALE" for claim in material_claims):
        payload["registry_trust_verdict"] = "REGISTRY_STALE"
    elif any(claim.get("verification_status") == "REGRESSION_DETECTED" for claim in material_claims):
        payload["registry_trust_verdict"] = "REGRESSION_DETECTED"
    elif audit.get("registry_trust_verdict") != "REGISTRY_TRUSTED" or material_unverified:
        payload["registry_trust_verdict"] = "REGISTRY_PARTIALLY_TRUSTED" if audit.get("registry_trust_verdict") != "REGISTRY_NOT_TRUSTED" else "REGISTRY_NOT_TRUSTED"
    else:
        payload["registry_trust_verdict"] = "REGISTRY_TRUSTED"
    for claim in payload["claim_contracts"]:
        if claim.get("field_name") == "registry_trust_verdict" and claim.get("claim_id") == "platform:registry_trust_verdict":
            claim["current_value"] = payload["registry_trust_verdict"]
            claim["verification_status"] = "VERIFIED"
    current_executable = str((payload.get("summary") or {}).get("current_executable_capability") or "")
    payload["assignment_decision"] = _evaluate_capability_assignment_from_payload(current_executable, payload, ignore_audit=True) if current_executable else None
    return payload


def _markdown_table_row(values: List[str]) -> str:
    return "| " + " | ".join(values) + " |"


def render_platform_registry_markdown(payload: Dict[str, object]) -> str:
    summary = payload.get("summary") or {}
    objective_dashboards = payload.get("objective_dashboards") or []
    objective_stack = payload.get("objective_stack") or {}
    capabilities = payload.get("capabilities") or []
    capability_summary = payload.get("capability_summary") or {}
    dependency_type_summary = payload.get("dependency_type_summary") or {}
    required_blocking_dependencies = payload.get("required_blocking_dependencies") or []
    non_blocking_relationships = payload.get("non_blocking_relationships") or []
    self_audit = payload.get("self_audit") or {}
    assignment_decision = payload.get("assignment_decision") or {}
    integrity_findings = payload.get("integrity_findings") or []
    claim_contracts = payload.get("claim_contracts") or []
    verified_claims = payload.get("verified_claims") or []
    partially_verified_claims = payload.get("partially_verified_claims") or []
    unverified_claims = payload.get("unverified_claims") or []
    stale_claims = payload.get("stale_claims") or []
    regression_claims = payload.get("regression_claims") or []
    claim_status_summary = payload.get("claim_status_summary") or {}

    lines: List[str] = []
    lines.append("# Platform Registry")
    lines.append("")
    lines.append(f"Generated at: `{payload.get('generated_at_utc')}`")
    lines.append("")
    lines.append("## Business Progress")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in [
        "objectives_discovered",
        "capabilities_reused",
        "milestones_generated",
        "current_active_objective",
        "current_blocker",
        "current_executable_capability",
        "current_assigned_agent",
        "current_task",
        "business_completion",
        "overall_completion",
        "objective_dependency_violations",
    ]:
        lines.append(f"| {key.replace('_', ' ').title()} | {summary.get(key, 0)} |")
    lines.append("")
    lines.append("## Current Objective Stack")
    lines.append("")
    lines.append("| Current Objective | Current Milestone | Current Executable Capability | Assigned Agent | Current Task |")
    lines.append("| --- | --- | --- | --- | --- |")
    lines.append(
        _markdown_table_row(
            [
                str(objective_stack.get("name") or objective_stack.get("objective_id") or ""),
                str((objective_stack.get("current_milestone") or {}).get("name") or ""),
                str(objective_stack.get("current_work") or ""),
                str(objective_stack.get("assigned_agent") or ""),
                str(objective_stack.get("current_task") or ""),
            ]
        )
    )
    lines.append("")
    lines.append("## Objective Dashboards")
    lines.append("")
    lines.append("| Objective | Market | Progress | Completed | Blocked | Waiting | Current Work | Current Blocker | Current Next Action | Estimated Completion | Business Readiness |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for objective in objective_dashboards:
        lines.append(
            _markdown_table_row(
                [
                    str(objective.get("name") or ""),
                    str(objective.get("target_market") or ""),
                    f"{objective.get('completion_percentage', 0)}%",
                    str(len(objective.get("completed_capabilities") or [])),
                    str(len(objective.get("blocked_capabilities") or [])),
                    str(len(objective.get("waiting_capabilities") or [])),
                    str(objective.get("current_work") or ""),
                    str(objective.get("current_blocker") or ""),
                    str(objective.get("current_task") or ""),
                    str(objective.get("estimated_remaining_work") or {}),
                    str(objective.get("business_readiness") or ""),
                ]
            )
        )
    lines.append("")
    lines.append("## Capability Inventory")
    lines.append("")
    lines.append("| ID | Name | Owner | Impl | Verify | Readiness | Acceptance | Missing Proof Classes | Dependencies | Downstream | Blockers | Last Verified |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for capability in capabilities:
        blockers = capability.get("blocking_issues") or []
        blocker_text = "; ".join(str(issue.get("exact_blocker") or "") for issue in blockers if isinstance(issue, dict)) or ""
        lines.append(
            _markdown_table_row(
                [
                    str(capability.get("id") or ""),
                    str(capability.get("name") or ""),
                    str(capability.get("owner") or ""),
                    str(capability.get("implementation_status") or ""),
                    str(capability.get("verification_status") or ""),
                    str(capability.get("production_readiness") or ""),
                    str(capability.get("acceptance_status") or ""),
                    ", ".join(str(item) for item in capability.get("missing_proof_classes") or []),
                    ", ".join(str(dep) for dep in capability.get("dependencies") or []),
                    ", ".join(str(dep) for dep in capability.get("downstream_consumers") or []),
                    blocker_text,
                    str(capability.get("last_verified") or ""),
                ]
            )
        )
    lines.append("")
    lines.append("## Capability Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in [
        "total_capabilities",
        "implemented",
        "verified",
        "blocked",
        "frozen",
        "production_ready",
        "duplicate_capabilities",
        "capabilities_with_no_owner",
        "capabilities_with_no_tests",
        "capabilities_with_no_runtime_verification",
    ]:
        lines.append(f"| {key.replace('_', ' ').title()} | {capability_summary.get(key, 0)} |")
    lines.append("")
    lines.append("## Dependency Type Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in [
        "required_build_edges",
        "required_runtime_edges",
        "evidence_edges",
        "optional_consumer_edges",
        "monitoring_edges",
        "documentation_references",
    ]:
        lines.append(f"| {key.replace('_', ' ').title()} | {dependency_type_summary.get(key, 0)} |")
    lines.append("")
    lines.append("## Required Blocking Dependencies")
    lines.append("")
    lines.append("| Capability | Required Build Dependencies | Required Runtime Dependencies |")
    lines.append("| --- | --- | --- |")
    for row in required_blocking_dependencies:
        lines.append(_markdown_table_row([
            str(row.get("capability_id") or ""),
            ", ".join(str(item) for item in row.get("required_build_dependencies") or []),
            ", ".join(str(item) for item in row.get("required_runtime_dependencies") or []),
        ]))
    lines.append("")
    lines.append("## Non-Blocking Relationships")
    lines.append("")
    lines.append("| Capability | Evidence Dependencies | Optional Consumers | Monitoring Relationships | Documentation References |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in non_blocking_relationships:
        lines.append(_markdown_table_row([
            str(row.get("capability_id") or ""),
            ", ".join(str(item) for item in row.get("evidence_dependencies") or []),
            ", ".join(str(item) for item in row.get("optional_consumers") or []),
            ", ".join(str(item) for item in row.get("monitoring_relationships") or []),
            ", ".join(str(item) for item in row.get("documentation_references") or []),
        ]))
    lines.append("")
    lines.append("## Registry Self-Audit Result")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    lines.append(f"| Registry Trust Verdict | {payload.get('registry_trust_verdict') or ''} |")
    lines.append(f"| Finding Count | {self_audit.get('finding_count', 0)} |")
    lines.append(f"| Has P0 Findings | {self_audit.get('has_p0_findings', False)} |")
    lines.append(f"| Current Active Objective | {summary.get('current_active_objective', '')} |")
    lines.append(f"| Current Executable Capability | {summary.get('current_executable_capability', '')} |")
    lines.append(f"| Current Blocker | {summary.get('current_blocker', '')} |")
    lines.append(f"| Assignment Decision | {assignment_decision.get('reason', '')} |")
    lines.append("")
    lines.append("## Capability Acceptance Summary")
    lines.append("")
    lines.append("| Capability | Acceptance Status | Regression Status | Last Verified | Verification Owner | Verification Method | Definition Of Done | Missing Proof Classes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for capability in capabilities:
        lines.append(_markdown_table_row([
            str(capability.get("id") or ""),
            str(capability.get("acceptance_status") or ""),
            str(capability.get("regression_status") or ""),
            str(capability.get("last_verified") or ""),
            str(capability.get("verification_owner") or ""),
            str(capability.get("verification_method") or ""),
            "; ".join(str(item) for item in capability.get("definition_of_done") or []),
            ", ".join(str(item) for item in capability.get("missing_proof_classes") or []),
        ]))
    lines.append("")
    lines.append("## Registry Trust Derivation")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("| --- | --- |")
    for key in ["VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "STALE", "REGRESSION_DETECTED", "BLOCKED", "OWNER_DECLARED", "UNKNOWN"]:
        lines.append(f"| {key.replace('_', ' ').title()} Claims | {claim_status_summary.get(key, 0)} |")
    lines.append(f"| Registry Trust Verdict | {payload.get('registry_trust_verdict') or ''} |")
    lines.append("")
    lines.append("## Verified Claims")
    lines.append("")
    lines.append("| Claim ID | Field | Value | Source Type | Derivation | Last Verified |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for claim in verified_claims:
        lines.append(_markdown_table_row([
            str(claim.get("claim_id") or ""),
            str(claim.get("field_name") or ""),
            str(claim.get("current_value") or ""),
            str(claim.get("source_type") or ""),
            str(claim.get("derivation_method") or ""),
            str(claim.get("last_verified_at") or ""),
        ]))
    lines.append("")
    lines.append("## Partially Verified Claims")
    lines.append("")
    lines.append("| Claim ID | Field | Value | Missing Proof Classes | Last Verified |")
    lines.append("| --- | --- | --- | --- | --- |")
    for claim in partially_verified_claims:
        lines.append(_markdown_table_row([
            str(claim.get("claim_id") or ""),
            str(claim.get("field_name") or ""),
            str(claim.get("current_value") or ""),
            ", ".join(str(item) for item in claim.get("missing_proof_classes") or []),
            str(claim.get("last_verified_at") or ""),
        ]))
    lines.append("")
    lines.append("## Unverified Claims")
    lines.append("")
    lines.append("| Claim ID | Field | Value | Missing Proof Classes |")
    lines.append("| --- | --- | --- | --- |")
    for claim in unverified_claims:
        lines.append(_markdown_table_row([
            str(claim.get("claim_id") or ""),
            str(claim.get("field_name") or ""),
            str(claim.get("current_value") or ""),
            ", ".join(str(item) for item in claim.get("missing_proof_classes") or []),
        ]))
    lines.append("")
    lines.append("## Stale Claims")
    lines.append("")
    lines.append("| Claim ID | Field | Value | Missing Proof Classes |")
    lines.append("| --- | --- | --- | --- |")
    for claim in stale_claims:
        lines.append(_markdown_table_row([
            str(claim.get("claim_id") or ""),
            str(claim.get("field_name") or ""),
            str(claim.get("current_value") or ""),
            ", ".join(str(item) for item in claim.get("missing_proof_classes") or []),
        ]))
    lines.append("")
    lines.append("## Regressions")
    lines.append("")
    lines.append("| Claim ID | Field | Value | Missing Proof Classes |")
    lines.append("| --- | --- | --- | --- |")
    for claim in regression_claims:
        lines.append(_markdown_table_row([
            str(claim.get("claim_id") or ""),
            str(claim.get("field_name") or ""),
            str(claim.get("current_value") or ""),
            ", ".join(str(item) for item in claim.get("missing_proof_classes") or []),
        ]))
    lines.append("")
    lines.append("## Integrity Findings")
    lines.append("")
    lines.append("| Finding ID | Severity | Capability | Type | Impact | Automatic Fix Allowed | Owner Decision Required | Recommended Action |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for finding in integrity_findings:
        lines.append(_markdown_table_row([
            str(finding.get("finding_id") or ""),
            str(finding.get("severity") or ""),
            str(finding.get("capability") or ""),
            str(finding.get("finding_type") or ""),
            str(finding.get("impact") or ""),
            str(finding.get("automatic_fix_allowed") or False),
            str(finding.get("owner_decision_required") or False),
            str(finding.get("recommended_action") or ""),
        ]))
    return "\n".join(lines) + "\n"


def write_platform_registry_artifacts() -> Dict[str, object]:
    payload = build_platform_registry_payload()
    canonical_registry_trust_verdict = payload.get("registry_trust_verdict")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_platform_registry_markdown(payload), encoding="utf-8")
    payload["self_audit"] = run_platform_registry_self_audit(payload)
    payload["integrity_findings"] = payload["self_audit"].get("findings") or []
    payload["registry_trust_verdict"] = canonical_registry_trust_verdict
    current_executable = str((payload.get("summary") or {}).get("current_executable_capability") or "")
    payload["assignment_decision"] = _evaluate_capability_assignment_from_payload(current_executable, payload, ignore_audit=True) if current_executable else None
    DATABASE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_platform_registry_markdown(payload), encoding="utf-8")
    return payload


def load_platform_registry() -> Dict[str, object]:
    if not DATABASE_PATH.exists():
        return build_platform_registry_payload()
    try:
        payload = json.loads(DATABASE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = build_platform_registry_payload()
    if not isinstance(payload, dict):
        return build_platform_registry_payload()
    capabilities = payload.get("capabilities") or []
    if not capabilities:
        return build_platform_registry_payload()
    first_capability = capabilities[0] if isinstance(capabilities[0], dict) else {}
    if not isinstance(first_capability, dict) or "required_build_dependencies" not in first_capability or "self_audit" not in payload:
        return build_platform_registry_payload()
    payload["capabilities"] = [_normalize_capability_record(dict(capability)) for capability in capabilities if isinstance(capability, dict)]
    return payload


def get_platform_capability(capability_id: str) -> Optional[Dict[str, object]]:
    payload = load_platform_registry()
    for capability in payload.get("capabilities") or []:
        if str(capability.get("id") or "") == capability_id:
            return capability
    return None
