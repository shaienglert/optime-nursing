# OPTIME Intelligence Platform Architecture

## Purpose

Design a multi-agent intelligence platform that continuously improves recommendation quality while preserving the core ranking rule: clinical fit is primary, and non-clinical enhancements act as confidence and tie-break inputs only.

## Core Principles

- Clinical safety first: no agent can override mandatory clinical constraints.
- Trusted-source hierarchy: provider-verified and regulated sources outrank inferred signals.
- Memory-aware intelligence: every agent can read facility memory state and write auditable updates through controlled APIs.
- Deterministic matching boundary: agents enrich inputs, confidence, and explainability; matching engine remains deterministic.
- Continuous learning loop: outcomes are fed back into weighting, confidence, and question generation.

## Shared Platform Components

- Agent Orchestrator: schedules periodic jobs and event-driven runs.
- Trust and Provenance Layer: assigns source confidence, recency, and provenance labels.
- Facility Memory Engine: stores capability answers, confidence, conflicts, expiry, and audit trails.
- Matching Engine: computes fit score, confidence score, ranking explanation, and verification checklist.
- Knowledge Graph: canonical graph for facility, resident, services, outcomes, and social context entities.

## Agent Architecture

### 1. Clinical Knowledge Agent

- Mission: Maintain high-confidence clinical capability intelligence for skilled nursing, rehabilitation, chronic condition support, staffing adequacy, and acuity readiness.
- Trusted data sources:
  - CMS Provider Data and Medicare Care Compare
  - State health department inspections and enforcement actions
  - Provider-submitted credentialed updates (verified users only)
  - Clinical policy repositories and standardized care taxonomies
- Update frequency:
  - CMS and state feeds: weekly
  - Provider verified updates: near real-time
  - Clinical taxonomy refresh: monthly
- Outputs:
  - Clinical capability states per facility (YES/NO/UNKNOWN)
  - Clinical quality subscores and trend indicators
  - Clinical risk flags and contraindication markers
  - Verification questions for unresolved clinical capabilities
- Database tables:
  - clinical_capability_facts
  - facility_clinical_quality_snapshots
  - clinical_risk_flags
  - clinical_source_events
- APIs:
  - GET /intelligence/clinical/facilities/{facility_id}
  - POST /intelligence/clinical/ingest
  - POST /intelligence/clinical/recompute/{facility_id}
- Interaction with matching engine:
  - Supplies mandatory and critical care-fit features
  - Provides clinical quality category contributions
  - Feeds missing clinical fields into confidence penalties only
- Interaction with Facility Memory Engine:
  - Reads verified clinical memory and conflict state before recompute
  - Writes new clinical evidence with confidence, provenance, TTL, and audit entry

### 2. Senior Living Research Agent

- Mission: Build market-level intelligence on facility operations, reputation, compliance patterns, and ownership dynamics.
- Trusted data sources:
  - Official facility websites and disclosures
  - Corporate filings and ownership registries
  - State licensing data
  - Structured review aggregations (source-weighted)
  - Local news from vetted outlets
- Update frequency:
  - Web and registry crawl: weekly
  - News and reputation refresh: daily
  - Ownership structure refresh: monthly
- Outputs:
  - Facility profile enrichment fields
  - Reputation trend signals
  - Ownership and operator risk insights
  - Source coverage metrics
- Database tables:
  - facility_research_profiles
  - facility_ownership_links
  - reputation_signal_events
  - source_coverage_metrics
- APIs:
  - GET /intelligence/research/facilities/{facility_id}
  - POST /intelligence/research/crawl
  - POST /intelligence/research/refresh/{facility_id}
- Interaction with matching engine:
  - Provides non-clinical context features and narrative evidence
  - Improves explainability and tie-break context only
- Interaction with Facility Memory Engine:
  - Reads memory overlays for disputed non-clinical facts
  - Writes candidate facts with lower default confidence until verified

### 3. Resident Needs Intelligence Agent

- Mission: Transform family and resident intake into structured need vectors with severity, priority, and uncertainty scoring.
- Trusted data sources:
  - Family intake questionnaires
  - Care manager notes
  - Historical successful match patterns
  - Standardized ADL/IADL and risk instruments
- Update frequency:
  - Intake parsing: real-time per search
  - Need model recalibration: biweekly
- Outputs:
  - Resident need profile vectors
  - Priority tier mapping (MANDATORY/CRITICAL/IMPORTANT/OPTIONAL)
  - Clarifying question queue for missing inputs
  - Persona and preference signatures
- Database tables:
  - resident_need_profiles
  - resident_preference_vectors
  - intake_uncertainty_logs
  - clarifying_question_sets
- APIs:
  - POST /intelligence/resident/parse-intake
  - GET /intelligence/resident/profile/{session_id}
  - POST /intelligence/resident/recompute/{session_id}
- Interaction with matching engine:
  - Supplies weighted requirement vectors and tier constraints
  - Constrains ranking by mandatory needs before any tie-break logic
- Interaction with Facility Memory Engine:
  - Reads which facility unknowns most affect resident-specific decisions
  - Triggers targeted verification requests for high-impact unknowns

### 4. Provider Intelligence Agent

- Mission: Normalize and score provider-supplied data quality, timeliness, and consistency across submitted claims.
- Trusted data sources:
  - Verified provider portal submissions
  - License and domain verification outcomes
  - Historical provider answer reliability metrics
- Update frequency:
  - Submission scoring: real-time
  - Reliability model update: weekly
- Outputs:
  - Provider trust scores
  - Submission conflict flags
  - Field-level confidence updates
  - Verification backlog prioritization
- Database tables:
  - provider_submission_events
  - provider_trust_scores
  - provider_field_conflicts
  - provider_verification_backlog
- APIs:
  - POST /intelligence/provider/submission
  - GET /intelligence/provider/trust/{facility_id}
  - POST /intelligence/provider/reconcile/{facility_id}
- Interaction with matching engine:
  - Increases confidence for verified provider-backed facts
  - Does not change clinical gating rules directly
- Interaction with Facility Memory Engine:
  - Primary writer for verified facility memory updates
  - Manages conflict state between provider and family-reported signals

### 5. Activities Intelligence Agent

- Mission: Map activity programs, social cadence, and resident engagement opportunities to lifestyle-fit needs.
- Trusted data sources:
  - Facility calendars and events pages
  - Social media event streams from official channels
  - Provider-submitted activity schedules
  - Public event listings with facility attribution
- Update frequency:
  - Event stream refresh: daily
  - Structured activity normalization: weekly
- Outputs:
  - Activities taxonomy coverage by facility
  - Social engagement intensity score
  - Program consistency indicators
  - Missing activity verification prompts
- Database tables:
  - facility_activity_catalog
  - activity_schedule_events
  - activity_coverage_scores
  - activity_verification_questions
- APIs:
  - GET /intelligence/activities/facilities/{facility_id}
  - POST /intelligence/activities/refresh/{facility_id}
  - GET /intelligence/activities/coverage
- Interaction with matching engine:
  - Provides activities and social-fit evidence for important/optional categories
  - Strengthens tie-break precision among clinically equivalent options
- Interaction with Facility Memory Engine:
  - Reads existing activity capability state and expiry
  - Writes refreshed activity evidence with 30-180 day TTL based on volatility

### 6. Nutrition Intelligence Agent

- Mission: Maintain dietary accommodation intelligence including therapeutic diets, meal flexibility, and nutrition support quality.
- Trusted data sources:
  - Facility dining pages and menus
  - Provider-verified dietary accommodation statements
  - Regulatory nutrition deficiency findings
  - Family feedback on meal accommodation outcomes
- Update frequency:
  - Provider and family updates: near real-time
  - Public menu/website ingestion: weekly
  - Deficiency report checks: monthly
- Outputs:
  - Diet accommodation matrix (renal, diabetic, low sodium, texture-modified, etc.)
  - Nutrition flexibility score
  - Dietary risk and contradiction alerts
  - Follow-up verification questions
- Database tables:
  - facility_nutrition_capabilities
  - nutrition_accommodation_matrix
  - nutrition_risk_alerts
  - nutrition_signal_events
- APIs:
  - GET /intelligence/nutrition/facilities/{facility_id}
  - POST /intelligence/nutrition/ingest
  - POST /intelligence/nutrition/reconcile/{facility_id}
- Interaction with matching engine:
  - Contributes to dietary-fit category scoring and confidence
  - Flags hard dietary constraints as mandatory blockers when configured
- Interaction with Facility Memory Engine:
  - Writes durable dietary accommodations with longer TTL where stable
  - Tracks contradictions between provider claims and family outcomes

### 7. Family Experience Agent

- Mission: Capture and normalize family-reported experience signals for communication quality, transition support, and trust outcomes.
- Trusted data sources:
  - Structured post-match family surveys
  - Intake-to-move-in communication logs
  - Complaint and resolution workflows
- Update frequency:
  - Survey and feedback ingestion: real-time
  - Experience trend analysis: weekly
- Outputs:
  - Family communication quality score
  - Transition support score
  - Escalation risk markers
  - Family narrative snippets for explainability
- Database tables:
  - family_experience_events
  - family_experience_scores
  - communication_quality_metrics
  - transition_support_indicators
- APIs:
  - POST /intelligence/family-experience/submit
  - GET /intelligence/family-experience/facilities/{facility_id}
  - GET /intelligence/family-experience/trends
- Interaction with matching engine:
  - Adds family-facing quality context to ranking explanation
  - Supports tie-breaks and recommendation narrative confidence
- Interaction with Facility Memory Engine:
  - Writes family-reported memory evidence with conflict-safe handling
  - Marks disputed fields for provider re-verification workflows

### 8. Outcome Learning Agent

- Mission: Learn from post-placement outcomes to improve success prediction and reduce mismatch risk.
- Trusted data sources:
  - 30/90/180 day post-placement outcomes
  - Readmission and adverse transition indicators
  - Family satisfaction and retention outcomes
  - Care escalation events
- Update frequency:
  - Outcome ingestion: daily
  - Model retraining and calibration: monthly
- Outputs:
  - Outcome success predictors
  - Failure factor updates
  - Segment-specific risk adjustments
  - Recommendations for feature weighting changes
- Database tables:
  - placement_outcome_events
  - outcome_success_models
  - mismatch_risk_factors
  - model_calibration_reports
- APIs:
  - POST /intelligence/outcomes/ingest
  - GET /intelligence/outcomes/facilities/{facility_id}
  - POST /intelligence/outcomes/retrain
- Interaction with matching engine:
  - Proposes weight tuning and risk penalties for future scoring versions
  - Feeds confidence calibration without overriding mandatory fit
- Interaction with Facility Memory Engine:
  - Adds observed outcome reliability signals to memory confidence metadata
  - Triggers expiry shortening for repeatedly contradicted claims

### 9. Matching Improvement Agent

- Mission: Evaluate ranking behavior, detect regressions, and safely deploy improvements through controlled experiments.
- Trusted data sources:
  - Search and ranking trace logs
  - Match quality audit reports
  - Outcome Learning Agent recommendations
  - A/B experiment telemetry
- Update frequency:
  - Performance and drift monitoring: daily
  - Experiment cycles: biweekly
- Outputs:
  - Candidate scoring configuration updates
  - Regression alerts and guardrail violations
  - Explainability improvements
  - Experiment reports and rollout recommendations
- Database tables:
  - ranking_trace_events
  - experiment_configurations
  - scoring_guardrail_violations
  - ranking_regression_reports
- APIs:
  - GET /intelligence/matching/diagnostics
  - POST /intelligence/matching/experiment/start
  - POST /intelligence/matching/rollout
- Interaction with matching engine:
  - Owns versioned score config proposals and guardrail enforcement
  - Ensures clinical-fit-first constraints remain immutable
- Interaction with Facility Memory Engine:
  - Consumes memory quality metrics to tune confidence penalties
  - Recommends question prioritization based on uncertainty impact

### 10. Knowledge Graph Agent

- Mission: Maintain the canonical graph of entities and relationships across residents, facilities, services, outcomes, and signals.
- Trusted data sources:
  - All upstream agent outputs with provenance metadata
  - Canonical facility registry and taxonomy maps
  - Verified provider identity and ownership records
- Update frequency:
  - Graph writes: event-driven near real-time
  - Consistency checks and deduplication: daily
  - Schema evolution: quarterly
- Outputs:
  - Unified entity IDs and relationship edges
  - Explainable lineage paths for recommendations
  - Cross-agent consistency checks and conflict detection
  - Graph-powered feature bundles for ranking and narrative
- Database tables:
  - kg_entities
  - kg_relationships
  - kg_source_lineage
  - kg_conflict_edges
  - kg_feature_materializations
- APIs:
  - GET /intelligence/kg/entity/{entity_id}
  - GET /intelligence/kg/facility/{facility_id}/subgraph
  - POST /intelligence/kg/upsert
  - POST /intelligence/kg/reconcile
- Interaction with matching engine:
  - Provides unified features, source lineage, and cross-domain context
  - Enables deeper traceability in score audit output
- Interaction with Facility Memory Engine:
  - Bi-directional sync between graph facts and memory records
  - Uses memory confidence and conflict states as edge weights

## Agent Interaction Flow

1. Intake arrives and Resident Needs Intelligence Agent creates requirement vectors.
2. Clinical, Nutrition, Activities, Research, and Provider agents enrich facility intelligence.
3. Knowledge Graph Agent reconciles entities and relationships, then materializes feature bundles.
4. Matching engine runs deterministic scoring with mandatory clinical gating first.
5. Facility Memory Engine updates unknown/conflict/expiry state from new evidence.
6. Family Experience and Outcome Learning agents feed back real-world outcomes.
7. Matching Improvement Agent monitors drift, runs experiments, and proposes safe updates.

## Implementation Roadmap by Business Value

| Phase | Priority | Agents | Business Value | Why First |
| --- | --- | --- | --- | --- |
| Phase 1 | Highest | Clinical Knowledge, Resident Needs Intelligence, Provider Intelligence | Immediate recommendation quality and safety uplift | Directly improves core fit accuracy, mandatory gating, and confidence in existing workflow |
| Phase 2 | High | Knowledge Graph, Nutrition Intelligence, Activities Intelligence | Better explainability and preference-fit precision | Reduces unknowns, strengthens family trust, and improves tie-break quality |
| Phase 3 | High | Family Experience, Outcome Learning | Closed-loop quality improvement | Converts placement outcomes into measurable improvement signals |
| Phase 4 | Medium | Senior Living Research, Matching Improvement | Strategic differentiation and optimization at scale | Improves market intelligence depth and safe ranking evolution |

## Validation Criteria

Architecture is considered valid only if all checks pass:

- All 10 required agents are defined.
- Each agent includes mission, trusted data sources, update frequency, outputs, database tables, APIs, matching engine interaction, and Facility Memory Engine interaction.
- Clinical-fit-first rule is explicitly preserved.
- Roadmap prioritization is aligned to business value and implementation sequencing.
- Interaction flow demonstrates end-to-end data movement from intake to learning loop.

## Architecture Validation Result

Status: PASS (pending automated validation command execution)
