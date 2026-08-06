# Platform Registry

Generated at: `2026-08-06T05:40:39Z`

## Business Progress

| Metric | Value |
| --- | --- |
| Objectives Discovered | 6 |
| Capabilities Reused | 10 |
| Milestones Generated | 20 |
| Current Active Objective | launch_nevada |
| Current Blocker | source_intelligence |
| Current Executable Capability | source_intelligence |
| Current Assigned Agent | OPTIME Source Intelligence |
| Current Task | Complete the remaining approved source integrations and unblock market build coverage. |
| Business Completion | 16.7 |
| Overall Completion | 33.9 |
| Objective Dependency Violations | 5 |

## Current Objective Stack

| Current Objective | Current Milestone | Current Executable Capability | Assigned Agent | Current Task |
| --- | --- | --- | --- | --- |
| Launch Nevada | Milestone 1 | source_intelligence | OPTIME Source Intelligence | Complete the remaining approved source integrations and unblock market build coverage. |

## Objective Dashboards

| Objective | Market | Progress | Completed | Blocked | Waiting | Current Work | Current Blocker | Current Next Action | Estimated Completion | Business Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Launch Nevada | nevada | 16.7% | 1 | 5 | 0 | source_intelligence | source_intelligence | Complete the remaining approved source integrations and unblock market build coverage. | {'capabilities': 5, 'milestones': 4} | BLOCKED |
| Launch Florida | florida | 16.7% | 1 | 5 | 0 | source_intelligence | source_intelligence | Complete the remaining approved source integrations and unblock market build coverage. | {'capabilities': 5, 'milestones': 4} | BLOCKED |
| Launch Texas | texas | 20.0% | 1 | 4 | 0 | source_intelligence | source_intelligence | Complete the remaining approved source integrations and unblock market build coverage. | {'capabilities': 4, 'milestones': 4} | BLOCKED |
| Media Ready | all | 0.0% | 0 | 3 | 0 | canonical_universe | canonical_universe | Finish the remaining market-builder dependency chain and close the Nevada HCQC gap. | {'capabilities': 3, 'milestones': 3} | BLOCKED |
| Recommendation Production Ready | all | 50.0% | 2 | 2 | 0 | canonical_universe | canonical_universe | Finish the remaining market-builder dependency chain and close the Nevada HCQC gap. | {'capabilities': 2, 'milestones': 2} | BLOCKED |
| Provider Portal Production Ready | all | 100.0% | 3 | 0 | 0 | provider_intelligence |  | Continue controlled discovery and publish only verified provider updates. | {'capabilities': 0, 'milestones': 0} | READY |

## Capability Inventory

| ID | Name | Owner | Impl | Verify | Readiness | Acceptance | Missing Proof Classes | Dependencies | Downstream | Blockers | Last Verified |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| constitution_governance | Constitution & Governance | OPTIME Governance | VERIFIED | VERIFIED | PRODUCTION_READY | VERIFIED |  |  | source_intelligence, market_builder, canonical_universe, government_identity, media_intelligence, knowledge_graph, data_quality_trust, provider_intelligence, clinical_knowledge, clinical_evidence, narrative_intelligence, nutrition_intelligence, outcome_learning, resident_needs_intelligence, senior_living_research, family_experience_intelligence, assessment_experience, recommendation_decision_engine, chief_ai_supervisor, remediation_policy_engine, daily_system_health_report, email_delivery, report_archive, runtime_sync, platform_registry |  | 2026-08-02T10:11:53Z |
| source_intelligence | Source Intelligence | OPTIME Source Intelligence | IN_PROGRESS | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | test_evidence | constitution_governance | market_builder, canonical_universe, data_quality_trust, chief_ai_supervisor | Approved sources are not fully integrated and Florida state sources remain partially blocked. | 2026-08-06T05:37:03Z |
| market_builder | Market Builder | OPTIME Market Intelligence | NOT_STARTED | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | runtime_evidence | constitution_governance, source_intelligence | canonical_universe | No generic builder entry point exists; validation remains state-specific. | 2026-08-05T12:11:52Z |
| canonical_universe | Canonical Universe | OPTIME Canonical Universe | IMPLEMENTED | VERIFIED | BLOCKED | VERIFIED |  | market_builder, source_intelligence | government_identity, media_intelligence, assessment_experience, recommendation_decision_engine, chief_ai_supervisor | Layer 2 Market Builder remains state-specific and Nevada HCQC remains unintegrated. | 2026-08-05T12:11:52Z |
| government_identity | Government Identity | OPTIME Identity Governance | IMPLEMENTED | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | runtime_evidence | canonical_universe | media_intelligence, recommendation_decision_engine, assessment_experience | Government identity resolution still depends on incomplete canonical universe coverage. | 2026-08-05T12:11:51Z |
| media_intelligence | Media Intelligence | OPTIME Media Intelligence | IN_PROGRESS | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | runtime_evidence | canonical_universe, government_identity | recommendation_decision_engine, assessment_experience | Rights validation is not integrated for the media pilot and generic media remains non-facility-specific. | 2026-08-05T12:11:51Z |
| knowledge_graph | Knowledge Graph | OPTIME Knowledge Graph Intelligence | IMPLEMENTED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | source_intelligence, canonical_universe | provider_intelligence, clinical_knowledge, assessment_experience, recommendation_decision_engine, chief_ai_supervisor |  | 2026-08-06T05:29:18Z |
| data_quality_trust | Data Quality & Trust | OPTIME Data Quality | IMPLEMENTED | VERIFIED | PRODUCTION_READY | VERIFIED |  |  | chief_ai_supervisor, recommendation_decision_engine |  | 2026-08-06T05:29:18Z |
| matching_improvement | Matching Improvement | OPTIME Matching Improvement | VERIFIED | VERIFIED | PRODUCTION_READY | VERIFIED |  | knowledge_graph, data_quality_trust | narrative_intelligence, outcome_learning |  | 2026-08-06T05:29:18Z |
| provider_intelligence | Provider Intelligence | OPTIME Provider Intelligence | VERIFIED | VERIFIED | PRODUCTION_READY | VERIFIED |  | data_quality_trust, knowledge_graph | canonical_universe, recommendation_decision_engine, assessment_experience, activities_intelligence, nutrition_intelligence, clinical_knowledge, resident_needs_intelligence, senior_living_research, narrative_intelligence |  | 2026-08-06T05:29:18Z |
| activities_intelligence | Activities Intelligence | OPTIME Lifestyle Intelligence | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | provider_intelligence, outcome_learning, knowledge_graph | recommendation_decision_engine, assessment_experience, narrative_intelligence |  | 2026-08-06T05:29:18Z |
| clinical_knowledge | Clinical Knowledge | OPTIME Clinical Intelligence | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | provider_intelligence, knowledge_graph, clinical_evidence, outcome_learning | assessment_experience, recommendation_decision_engine, family_experience_intelligence |  | 2026-08-06T05:29:18Z |
| clinical_evidence | Clinical Evidence | OPTIME Evidence Intelligence | IN_PROGRESS | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | implementation_evidence, test_evidence | knowledge_graph | clinical_knowledge, recommendation_decision_engine, narrative_intelligence | Automated external evidence monitoring is not configured. | 2026-07-18T05:44:31Z |
| narrative_intelligence | Narrative Intelligence | OPTIME Narrative Intelligence | IN_PROGRESS | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | implementation_evidence, test_evidence | provider_intelligence, knowledge_graph, clinical_knowledge, clinical_evidence, matching_improvement | family_experience_intelligence, recommendation_decision_engine | Upstream evidence and knowledge coverage remain insufficient for fully trusted narratives. | 2026-07-18T16:46:28Z |
| nutrition_intelligence | Nutrition Intelligence | OPTIME Nutrition Intelligence | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | provider_intelligence, knowledge_graph, clinical_knowledge | recommendation_decision_engine, assessment_experience |  | 2026-08-06T05:29:18Z |
| outcome_learning | Outcome Learning | OPTIME Outcome Intelligence | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | knowledge_graph, matching_improvement, clinical_knowledge | recommendation_decision_engine, chief_ai_supervisor |  | 2026-08-06T05:29:18Z |
| resident_needs_intelligence | Resident Needs Intelligence | OPTIME Resident Needs Intelligence | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | provider_intelligence, knowledge_graph | assessment_experience, recommendation_decision_engine |  | 2026-08-06T05:29:18Z |
| senior_living_research | Senior Living Research | OPTIME Senior Living Research | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | provider_intelligence, knowledge_graph | chief_ai_supervisor, knowledge_graph |  | 2026-08-06T05:29:18Z |
| family_experience_intelligence | Family Experience Intelligence | OPTIME Family Experience Intelligence | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | knowledge_graph, narrative_intelligence | assessment_experience, recommendation_decision_engine |  | 2026-08-06T05:29:18Z |
| assessment_experience | Assessment Experience | OPTIME Assessment Experience | VERIFIED | UNVERIFIED | PRODUCTION_READY | UNVERIFIED | implementation_evidence, runtime_evidence, test_evidence | knowledge_graph, resident_needs_intelligence, family_experience_intelligence | recommendation_decision_engine, canonical_universe |  | 2026-08-06T05:40:41Z |
| recommendation_decision_engine | Recommendation Decision Engine | OPTIME Recommendation Engine | IMPLEMENTED | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | runtime_evidence | canonical_universe, knowledge_graph, assessment_experience | family_experience_intelligence, chief_ai_supervisor | Upstream canonical universe and assessment readiness remain incomplete for full production confidence. | 2026-08-05T10:04:15Z |
| chief_ai_supervisor | Chief AI Supervisor | OPTIME Platform Governance | VERIFIED | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | runtime_evidence | constitution_governance, platform_registry, report_archive, runtime_sync, remediation_policy_engine | daily_system_health_report, platform_registry, remediation_policy_engine | Owner email delivery remains blocked by missing SMTP configuration. | 2026-08-06T05:37:03Z |
| remediation_policy_engine | Remediation Policy Engine | OPTIME Platform Governance | VERIFIED | VERIFIED | PRODUCTION_READY | VERIFIED |  | constitution_governance | chief_ai_supervisor, daily_system_health_report |  | 2026-08-05T12:11:51Z |
| email_delivery | Email Delivery | OPTIME Operations | IMPLEMENTED | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | test_evidence | report_archive, constitution_governance | daily_system_health_report, chief_ai_supervisor | OPTIME_SMTP_HOST and OPTIME_SMTP_FROM are missing from environment configuration. | 2026-07-19T14:08:21Z |
| report_archive | Report Archive | OPTIME Platform Operations | VERIFIED | PARTIALLY_VERIFIED | PRODUCTION_READY | PARTIALLY_VERIFIED | test_evidence | constitution_governance | daily_system_health_report, chief_ai_supervisor |  | 2026-08-05T10:04:16Z |
| runtime_sync | Runtime Sync | OPTIME Platform Operations | VERIFIED | VERIFIED | PRODUCTION_READY | VERIFIED |  | constitution_governance | chief_ai_supervisor, daily_system_health_report |  | 2026-08-05T12:11:51Z |
| daily_system_health_report | Daily System Health Report | OPTIME Chief AI Supervisor | VERIFIED | PARTIALLY_VERIFIED | BLOCKED | PARTIALLY_VERIFIED | runtime_evidence | chief_ai_supervisor, report_archive | chief_ai_supervisor, email_delivery | SMTP delivery is blocked by missing required environment variables. | 2026-08-05T12:11:51Z |
| platform_registry | Platform Registry | OPTIME Platform Governance | IMPLEMENTED | VERIFIED | PRODUCTION_READY | VERIFIED |  | constitution_governance | chief_ai_supervisor |  | 2026-08-06T05:37:12Z |

## Capability Summary

| Metric | Value |
| --- | --- |
| Total Capabilities | 28 |
| Implemented | 7 |
| Verified | 8 |
| Blocked | 11 |
| Frozen | 0 |
| Production Ready | 17 |
| Duplicate Capabilities | 0 |
| Capabilities With No Owner | 0 |
| Capabilities With No Tests | 13 |
| Capabilities With No Runtime Verification | 20 |

## Dependency Type Summary

| Metric | Value |
| --- | --- |
| Required Build Edges | 43 |
| Required Runtime Edges | 4 |
| Evidence Edges | 11 |
| Optional Consumer Edges | 97 |
| Monitoring Edges | 6 |
| Documentation References | 66 |

## Required Blocking Dependencies

| Capability | Required Build Dependencies | Required Runtime Dependencies |
| --- | --- | --- |
| source_intelligence | constitution_governance |  |
| market_builder | constitution_governance, source_intelligence |  |
| canonical_universe | market_builder, source_intelligence |  |
| government_identity | canonical_universe |  |
| media_intelligence | canonical_universe, government_identity |  |
| matching_improvement | knowledge_graph, data_quality_trust |  |
| provider_intelligence | data_quality_trust, knowledge_graph |  |
| activities_intelligence | provider_intelligence, outcome_learning, knowledge_graph |  |
| clinical_knowledge | provider_intelligence, knowledge_graph |  |
| clinical_evidence | knowledge_graph |  |
| narrative_intelligence | provider_intelligence, knowledge_graph |  |
| nutrition_intelligence | provider_intelligence, knowledge_graph |  |
| outcome_learning | knowledge_graph, matching_improvement |  |
| resident_needs_intelligence | provider_intelligence, knowledge_graph |  |
| senior_living_research | provider_intelligence, knowledge_graph |  |
| family_experience_intelligence | knowledge_graph |  |
| assessment_experience | knowledge_graph, resident_needs_intelligence |  |
| recommendation_decision_engine | canonical_universe, knowledge_graph, assessment_experience |  |
| chief_ai_supervisor | constitution_governance | platform_registry, report_archive, runtime_sync, remediation_policy_engine |
| remediation_policy_engine | constitution_governance |  |
| email_delivery | report_archive, constitution_governance |  |
| report_archive | constitution_governance |  |
| runtime_sync | constitution_governance |  |
| daily_system_health_report | chief_ai_supervisor, report_archive |  |
| platform_registry | constitution_governance |  |

## Non-Blocking Relationships

| Capability | Evidence Dependencies | Optional Consumers | Monitoring Relationships | Documentation References |
| --- | --- | --- | --- | --- |
| constitution_governance |  | source_intelligence, market_builder, canonical_universe, government_identity, media_intelligence, knowledge_graph, data_quality_trust, provider_intelligence, clinical_knowledge, clinical_evidence, narrative_intelligence, nutrition_intelligence, outcome_learning, resident_needs_intelligence, senior_living_research, family_experience_intelligence, assessment_experience, recommendation_decision_engine, chief_ai_supervisor, remediation_policy_engine, daily_system_health_report, email_delivery, report_archive, runtime_sync, platform_registry |  | AGENTS.md, docs/OPTIME_PRINCIPLES.md, docs/OPTIME_PRINCIPLES_REGISTRY.md, reports/OPTIME_AGENT_SYSTEM_AUDIT.md, reports/OPTIME_DECISION_INTELLIGENCE_ARCHITECTURE.md |
| source_intelligence |  | market_builder, canonical_universe, data_quality_trust, chief_ai_supervisor |  | reports/SOURCE_LIFECYCLE_STATUS.md, reports/SOURCE_POLICY_MIGRATION_REPORT.md, reports/FLORIDA_SOURCE_CONNECTIVITY_AUDIT.md |
| market_builder |  | canonical_universe |  | reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md, reports/NEVADA_SOURCE_INTEGRATION_REPORT.md |
| canonical_universe |  | government_identity, media_intelligence, assessment_experience, recommendation_decision_engine, chief_ai_supervisor |  | reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md, reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md, reports/FLORIDA_CANONICAL_UNIVERSE_AUDIT.md |
| government_identity |  | media_intelligence, recommendation_decision_engine, assessment_experience |  | reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md, reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.json |
| media_intelligence |  | recommendation_decision_engine, assessment_experience |  | reports/MEDIA_LIVE_PILOT_FAILURE_ANALYSIS.md, reports/GOVERNMENT_IDENTITY_MEDIA_COVERAGE.md |
| knowledge_graph | source_intelligence, canonical_universe | provider_intelligence, clinical_knowledge, assessment_experience, recommendation_decision_engine, chief_ai_supervisor |  | reports/knowledge_graph_design.md, reports/knowledge_repository_schema.md |
| data_quality_trust |  | chief_ai_supervisor, recommendation_decision_engine | source_intelligence | reports/platform_health_report.md, reports/knowledge_quality_framework.md |
| matching_improvement |  | narrative_intelligence, outcome_learning |  | reports/agent_registry.md, reports/agent_value_matrix.md, reports/benchmark_gap_analysis.md |
| provider_intelligence |  | canonical_universe, recommendation_decision_engine, assessment_experience, activities_intelligence, nutrition_intelligence, clinical_knowledge, resident_needs_intelligence, senior_living_research, narrative_intelligence |  | reports/platform_intelligence_report.md, reports/agent_registry.md |
| activities_intelligence |  | recommendation_decision_engine, assessment_experience, narrative_intelligence |  | reports/agent_registry.md, reports/agent_task_queue.md |
| clinical_knowledge | clinical_evidence, outcome_learning | assessment_experience, recommendation_decision_engine, family_experience_intelligence |  | reports/clinical_knowledge_platform.md, reports/clinical_evidence_validation.md |
| clinical_evidence |  | clinical_knowledge, recommendation_decision_engine, narrative_intelligence |  | reports/clinical_evidence_validation.md, reports/knowledge_validation_framework.md |
| narrative_intelligence | clinical_knowledge, clinical_evidence, matching_improvement | family_experience_intelligence, recommendation_decision_engine |  | reports/OPTIME_IMMERSIVE_EDITORIAL_EXPERIENCE_STRATEGY.md, reports/agent_registry.md |
| nutrition_intelligence | clinical_knowledge | recommendation_decision_engine, assessment_experience |  | reports/agent_registry.md, reports/knowledge_workforce_architecture.md |
| outcome_learning | clinical_knowledge | recommendation_decision_engine, chief_ai_supervisor |  | reports/agent_registry.md, reports/knowledge_growth_matrix.md |
| resident_needs_intelligence |  | assessment_experience, recommendation_decision_engine |  | reports/agent_registry.md, reports/knowledge_workforce_architecture.md |
| senior_living_research |  | chief_ai_supervisor, knowledge_graph |  | reports/agent_registry.md, reports/agent_daily_missions.md |
| family_experience_intelligence | narrative_intelligence | assessment_experience, recommendation_decision_engine |  | reports/family_experience_report.md, reports/family_journey_review.md |
| assessment_experience | family_experience_intelligence | recommendation_decision_engine, canonical_universe |  | reports/assessment-ux-review, reports/ADAPTIVE_INTERVIEW_CURRENT_CODE_EXTRACT.md |
| recommendation_decision_engine |  | family_experience_intelligence, chief_ai_supervisor |  | reports/OPTIME_END_TO_END_DECISION_SIMULATION.md, reports/OPTIME_END_TO_END_FAMILY_EXPLANATION.md, reports/OPTIME_END_TO_END_SENSITIVITY_ANALYSIS.md |
| chief_ai_supervisor |  | daily_system_health_report, platform_registry, remediation_policy_engine | source_intelligence, market_builder, canonical_universe, data_quality_trust, email_delivery | reports/platform_health_report.md, reports/platform_intelligence_report.md, reports/DAILY_SYSTEM_HEALTH.md |
| remediation_policy_engine |  | chief_ai_supervisor, daily_system_health_report |  | reports/platform_health_report.md, reports/OPTIME_AGENT_SYSTEM_AUDIT.md |
| email_delivery |  | daily_system_health_report, chief_ai_supervisor |  | reports/DAILY_SYSTEM_HEALTH.md, reports/platform_health_report.md |
| report_archive |  | daily_system_health_report, chief_ai_supervisor |  | reports/daily/index.json, reports/daily/latest.md |
| runtime_sync |  | chief_ai_supervisor, daily_system_health_report |  | reports/GOVERNED_RUNTIME_INTEGRATION_REPORT.md, reports/OPTIME_AGENT_SYSTEM_AUDIT.md |
| daily_system_health_report |  | chief_ai_supervisor, email_delivery |  | reports/DAILY_SYSTEM_HEALTH.md, reports/DAILY_SYSTEM_HEALTH.json |
| platform_registry |  | chief_ai_supervisor |  | reports/platform_health_report.md, reports/platform_intelligence_report.md, reports/OPTIME_AGENT_SYSTEM_AUDIT.md, reports/PLATFORM_READINESS_MATRIX.json |

## Registry Self-Audit Result

| Metric | Value |
| --- | --- |
| Registry Trust Verdict | REGISTRY_TRUSTED |
| Finding Count | 0 |
| Has P0 Findings | False |
| Current Active Objective | launch_nevada |
| Current Executable Capability | source_intelligence |
| Current Blocker | source_intelligence |
| Assignment Decision | ALLOWED |

## Capability Acceptance Summary

| Capability | Acceptance Status | Regression Status | Last Verified | Verification Owner | Verification Method | Definition Of Done | Missing Proof Classes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| constitution_governance | VERIFIED | NO_REGRESSION | 2026-08-02T10:11:53Z | OPTIME Governance | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| source_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:37:03Z | OPTIME Source Intelligence | deterministic acceptance contract evaluation | every approved source has lifecycle status; every pending source has blocker; market readiness recalculated; downstream capability unlock state updated | test_evidence |
| market_builder | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-05T12:11:52Z | OPTIME Market Intelligence | deterministic acceptance contract evaluation | market build succeeds; canonical output created; validation passed; registry updated; objective progress recalculated | runtime_evidence |
| canonical_universe | VERIFIED | NO_REGRESSION | 2026-08-05T12:11:52Z | OPTIME Canonical Universe | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| government_identity | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-05T12:11:51Z | OPTIME Identity Governance | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | runtime_evidence |
| media_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-05T12:11:51Z | OPTIME Media Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | runtime_evidence |
| knowledge_graph | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Knowledge Graph Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| data_quality_trust | VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Data Quality | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| matching_improvement | VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Matching Improvement | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| provider_intelligence | VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Provider Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| activities_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Lifestyle Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| clinical_knowledge | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Clinical Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| clinical_evidence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-07-18T05:44:31Z | OPTIME Evidence Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | implementation_evidence, test_evidence |
| narrative_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-07-18T16:46:28Z | OPTIME Narrative Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | implementation_evidence, test_evidence |
| nutrition_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Nutrition Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| outcome_learning | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Outcome Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| resident_needs_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Resident Needs Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| senior_living_research | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Senior Living Research | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| family_experience_intelligence | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:29:18Z | OPTIME Family Experience Intelligence | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| assessment_experience | UNVERIFIED | NO_REGRESSION | 2026-08-06T05:40:41Z | OPTIME Assessment Experience | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | implementation_evidence, runtime_evidence, test_evidence |
| recommendation_decision_engine | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-05T10:04:15Z | OPTIME Recommendation Engine | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | runtime_evidence |
| chief_ai_supervisor | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-06T05:37:03Z | OPTIME Platform Governance | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | runtime_evidence |
| remediation_policy_engine | VERIFIED | NO_REGRESSION | 2026-08-05T12:11:51Z | OPTIME Platform Governance | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| email_delivery | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-07-19T14:08:21Z | OPTIME Operations | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| report_archive | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-05T10:04:16Z | OPTIME Platform Operations | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | test_evidence |
| runtime_sync | VERIFIED | NO_REGRESSION | 2026-08-05T12:11:51Z | OPTIME Platform Operations | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present |  |
| daily_system_health_report | PARTIALLY_VERIFIED | NO_REGRESSION | 2026-08-05T12:11:51Z | OPTIME Chief AI Supervisor | deterministic acceptance contract evaluation | implementation evidence present; runtime evidence present; verification evidence present | runtime_evidence |
| platform_registry | VERIFIED | NO_REGRESSION | 2026-08-06T05:37:12Z | OPTIME Platform Governance | deterministic acceptance contract evaluation | self audit PASS; zero circular required dependencies; zero missing capabilities; assignment gate operational |  |

## Registry Trust Derivation

| Metric | Value |
| --- | --- |
| Verified Claims | 121 |
| Partially Verified Claims | 120 |
| Unverified Claims | 0 |
| Stale Claims | 0 |
| Regression Detected Claims | 0 |
| Blocked Claims | 60 |
| Owner Declared Claims | 0 |
| Unknown Claims | 0 |
| Registry Trust Verdict | REGISTRY_TRUSTED |

## Verified Claims

| Claim ID | Field | Value | Source Type | Derivation | Last Verified |
| --- | --- | --- | --- | --- | --- |
| platform:capability_count | capability_count | 28 | REPOSITORY_DERIVED | len(CAPABILITY_CATALOG) | 2026-08-06T05:37:12Z |
| platform:objective_count | objective_count | 6 | REPOSITORY_DERIVED | len(OBJECTIVE_CATALOG) | 2026-08-06T05:37:12Z |
| platform:current_active_objective | current_active_objective | launch_nevada | OWNER_DECLARED | exactly one objective with activation_status = ACTIVE | 2026-08-06T05:40:41Z |
| platform:current_executable_capability | current_executable_capability | source_intelligence | REPOSITORY_DERIVED | ACTIVE objective -> valid milestones -> verified dependencies -> first executable incomplete capability | 2026-08-06T05:37:12Z |
| platform:current_blocker | current_blocker | source_intelligence | REPOSITORY_DERIVED | derived from current executable capability and unmet required dependencies | 2026-08-06T05:37:12Z |
| platform:current_assigned_agent | current_assigned_agent | OPTIME Source Intelligence | REPOSITORY_DERIVED | canonical owner/agent mapping of current executable capability | 2026-08-06T05:37:12Z |
| platform:current_task | current_task | Complete the remaining approved source integrations and unblock market build coverage. | REPOSITORY_DERIVED | next_action of current executable capability | 2026-08-06T05:37:12Z |
| platform:registry_trust_verdict | registry_trust_verdict | REGISTRY_TRUSTED | REPOSITORY_DERIVED | self audit findings + evidence contract completeness + assignment gate integrity + report agreement + acceptance contracts | 2026-08-06T05:37:12Z |
| platform:missing_capability_reference_count | missing_capability_reference_count |  | REPOSITORY_DERIVED | count(self_audit.findings where finding_type=MISSING_CAPABILITY_REFERENCE) | 2026-08-06T05:37:12Z |
| platform:duplicate_capability_count | duplicate_capability_count |  | REPOSITORY_DERIVED | count(self_audit.findings where finding_type=DUPLICATE_CAPABILITY_ID) | 2026-08-06T05:37:12Z |
| platform:duplicate_canonical_owner_count | duplicate_canonical_owner_count |  | REPOSITORY_DERIVED | count(self_audit.findings where finding_type=DUPLICATE_CANONICAL_RESPONSIBILITY) | 2026-08-06T05:37:12Z |
| platform:circular_required_dependency_count | circular_required_dependency_count |  | REPOSITORY_DERIVED | count(self_audit.findings where finding_type=CIRCULAR_REQUIRED_DEPENDENCY) | 2026-08-06T05:37:12Z |
| platform:integrity_finding_count | integrity_finding_count |  | REPOSITORY_DERIVED | len(self_audit.findings) | 2026-08-06T05:37:12Z |
| capability:constitution_governance:implementation_status | implementation_status | VERIFIED | REPOSITORY_DERIVED | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:canonical_owner | canonical_owner | OPTIME Governance | REPOSITORY_DERIVED | derived from capability contract for constitution_governance | 2026-08-06T05:40:41Z |
| capability:constitution_governance:dependency_declarations | dependency_declarations | {'required_build_dependencies': [], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['source_intelligence', 'market_builder', 'canonical_universe', 'government_identity', 'media_intelligence', 'knowledge_graph', 'data_quality_trust', 'provider_intelligence', 'clinical_knowledge', 'clinical_evidence', 'narrative_intelligence', 'nutrition_intelligence', 'outcome_learning', 'resident_needs_intelligence', 'senior_living_research', 'family_experience_intelligence', 'assessment_experience', 'recommendation_decision_engine', 'chief_ai_supervisor', 'remediation_policy_engine', 'daily_system_health_report', 'email_delivery', 'report_archive', 'runtime_sync', 'platform_registry'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:assigned_agent | assigned_agent | OPTIME Governance | RUNTIME_PROVEN | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:runtime_availability | runtime_availability | 2026-07-20T13:42:18Z | RUNTIME_PROVEN | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:test_coverage | test_coverage | 1 | REPOSITORY_DERIVED | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:constitution_governance:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for constitution_governance | 2026-08-02T10:11:53Z |
| capability:canonical_universe:implementation_status | implementation_status | IMPLEMENTED | REPOSITORY_DERIVED | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:production_readiness | production_readiness | BLOCKED | REPOSITORY_DERIVED | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:canonical_owner | canonical_owner | OPTIME Canonical Universe | REPOSITORY_DERIVED | derived from capability contract for canonical_universe | 2026-08-06T05:40:41Z |
| capability:canonical_universe:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['market_builder', 'source_intelligence'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['government_identity', 'media_intelligence', 'assessment_experience', 'recommendation_decision_engine', 'chief_ai_supervisor'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:assigned_agent | assigned_agent | OPTIME Canonical Universe | RUNTIME_PROVEN | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:runtime_availability | runtime_availability | 2026-08-05T12:11:51Z | RUNTIME_PROVEN | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:test_coverage | test_coverage | 1 | REPOSITORY_DERIVED | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:canonical_universe:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for canonical_universe | 2026-08-05T12:11:52Z |
| capability:data_quality_trust:implementation_status | implementation_status | IMPLEMENTED | REPOSITORY_DERIVED | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:canonical_owner | canonical_owner | OPTIME Data Quality | REPOSITORY_DERIVED | derived from capability contract for data_quality_trust | 2026-08-06T05:40:41Z |
| capability:data_quality_trust:dependency_declarations | dependency_declarations | {'required_build_dependencies': [], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['chief_ai_supervisor', 'recommendation_decision_engine'], 'monitoring_relationships': ['source_intelligence']} | REPOSITORY_DERIVED | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:assigned_agent | assigned_agent | data_quality | RUNTIME_PROVEN | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:runtime_availability | runtime_availability | 2026-07-18T04:16:33Z | RUNTIME_PROVEN | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:test_coverage | test_coverage | 1 | REPOSITORY_DERIVED | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:data_quality_trust:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for data_quality_trust | 2026-08-06T05:29:18Z |
| capability:matching_improvement:implementation_status | implementation_status | VERIFIED | REPOSITORY_DERIVED | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:canonical_owner | canonical_owner | OPTIME Matching Improvement | REPOSITORY_DERIVED | derived from capability contract for matching_improvement | 2026-08-06T05:40:41Z |
| capability:matching_improvement:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['knowledge_graph', 'data_quality_trust'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['narrative_intelligence', 'outcome_learning'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:assigned_agent | assigned_agent | matching_improvement | RUNTIME_PROVEN | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:runtime_availability | runtime_availability | 2026-07-20T22:17:42Z | RUNTIME_PROVEN | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:test_coverage | test_coverage | 2 | REPOSITORY_DERIVED | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:matching_improvement:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for matching_improvement | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:implementation_status | implementation_status | VERIFIED | REPOSITORY_DERIVED | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:canonical_owner | canonical_owner | OPTIME Provider Intelligence | REPOSITORY_DERIVED | derived from capability contract for provider_intelligence | 2026-08-06T05:40:41Z |
| capability:provider_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['data_quality_trust', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['canonical_universe', 'recommendation_decision_engine', 'assessment_experience', 'activities_intelligence', 'nutrition_intelligence', 'clinical_knowledge', 'resident_needs_intelligence', 'senior_living_research', 'narrative_intelligence'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:assigned_agent | assigned_agent | provider_intelligence | RUNTIME_PROVEN | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:runtime_availability | runtime_availability | 2026-07-18T16:46:28Z | RUNTIME_PROVEN | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:test_coverage | test_coverage | 1 | REPOSITORY_DERIVED | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:provider_intelligence:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for provider_intelligence | 2026-08-06T05:29:18Z |
| capability:remediation_policy_engine:implementation_status | implementation_status | VERIFIED | REPOSITORY_DERIVED | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:canonical_owner | canonical_owner | OPTIME Platform Governance | REPOSITORY_DERIVED | derived from capability contract for remediation_policy_engine | 2026-08-06T05:40:41Z |
| capability:remediation_policy_engine:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['chief_ai_supervisor', 'daily_system_health_report'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:assigned_agent | assigned_agent | OPTIME Platform Governance | RUNTIME_PROVEN | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:runtime_availability | runtime_availability | 2026-07-17T21:36:30Z | RUNTIME_PROVEN | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:test_coverage | test_coverage | 1 | REPOSITORY_DERIVED | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:remediation_policy_engine:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for remediation_policy_engine | 2026-08-05T12:11:51Z |
| capability:runtime_sync:implementation_status | implementation_status | VERIFIED | REPOSITORY_DERIVED | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:canonical_owner | canonical_owner | OPTIME Platform Operations | REPOSITORY_DERIVED | derived from capability contract for runtime_sync | 2026-08-06T05:40:41Z |
| capability:runtime_sync:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['chief_ai_supervisor', 'daily_system_health_report'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:assigned_agent | assigned_agent | OPTIME Platform Operations | RUNTIME_PROVEN | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:runtime_availability | runtime_availability | 2026-07-20T07:07:55Z | RUNTIME_PROVEN | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:test_coverage | test_coverage | 1 | REPOSITORY_DERIVED | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:runtime_sync:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for runtime_sync | 2026-08-05T12:11:51Z |
| capability:platform_registry:implementation_status | implementation_status | IMPLEMENTED | REPOSITORY_DERIVED | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:verification_status | verification_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:production_readiness | production_readiness | PRODUCTION_READY | REPOSITORY_DERIVED | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:canonical_owner | canonical_owner | OPTIME Platform Governance | REPOSITORY_DERIVED | derived from capability contract for platform_registry | 2026-08-06T05:40:41Z |
| capability:platform_registry:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['chief_ai_supervisor'], 'monitoring_relationships': []} | REPOSITORY_DERIVED | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:assigned_agent | assigned_agent | OPTIME Platform Governance | RUNTIME_PROVEN | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:runtime_availability | runtime_availability | 2026-08-06T05:37:12Z | RUNTIME_PROVEN | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:test_coverage | test_coverage | 2 | REPOSITORY_DERIVED | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| capability:platform_registry:acceptance_status | acceptance_status | VERIFIED | RUNTIME_PROVEN | derived from capability contract for platform_registry | 2026-08-06T05:37:12Z |
| objective:launch_nevada:activation_status | activation_status | ACTIVE | OWNER_DECLARED | derived from objective dashboard for launch_nevada | 2026-08-06T05:40:41Z |
| objective:launch_nevada:completion_percentage | completion_percentage | 16.7 | REPOSITORY_DERIVED | derived from objective dashboard for launch_nevada | 2026-08-06T05:37:12Z |
| objective:launch_nevada:milestone_count | milestone_count | 4 | REPOSITORY_DERIVED | derived from objective dashboard for launch_nevada | 2026-08-06T05:37:12Z |
| objective:launch_nevada:current_blocker | current_blocker | source_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for launch_nevada | 2026-08-06T05:37:12Z |
| objective:launch_nevada:current_executable_capability | current_executable_capability | source_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for launch_nevada | 2026-08-06T05:37:12Z |
| objective:launch_nevada:owner_approval_state | owner_approval_state | OWNER_APPROVED | OWNER_DECLARED | derived from objective dashboard for launch_nevada | 2026-08-06T05:40:41Z |
| objective:launch_florida:activation_status | activation_status | PLANNED | OWNER_DECLARED | derived from objective dashboard for launch_florida | 2026-08-06T05:40:41Z |
| objective:launch_florida:completion_percentage | completion_percentage | 16.7 | REPOSITORY_DERIVED | derived from objective dashboard for launch_florida | 2026-08-06T05:37:12Z |
| objective:launch_florida:milestone_count | milestone_count | 4 | REPOSITORY_DERIVED | derived from objective dashboard for launch_florida | 2026-08-06T05:37:12Z |
| objective:launch_florida:current_blocker | current_blocker | source_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for launch_florida | 2026-08-06T05:37:12Z |
| objective:launch_florida:current_executable_capability | current_executable_capability | source_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for launch_florida | 2026-08-06T05:37:12Z |
| objective:launch_florida:owner_approval_state | owner_approval_state | OWNER_DECLARED | OWNER_DECLARED | derived from objective dashboard for launch_florida | 2026-08-06T05:40:41Z |
| objective:launch_texas:activation_status | activation_status | PLANNED | OWNER_DECLARED | derived from objective dashboard for launch_texas | 2026-08-06T05:40:41Z |
| objective:launch_texas:completion_percentage | completion_percentage | 20.0 | REPOSITORY_DERIVED | derived from objective dashboard for launch_texas | 2026-08-06T05:37:12Z |
| objective:launch_texas:milestone_count | milestone_count | 4 | REPOSITORY_DERIVED | derived from objective dashboard for launch_texas | 2026-08-06T05:37:12Z |
| objective:launch_texas:current_blocker | current_blocker | source_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for launch_texas | 2026-08-06T05:37:12Z |
| objective:launch_texas:current_executable_capability | current_executable_capability | source_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for launch_texas | 2026-08-06T05:37:12Z |
| objective:launch_texas:owner_approval_state | owner_approval_state | OWNER_DECLARED | OWNER_DECLARED | derived from objective dashboard for launch_texas | 2026-08-06T05:40:41Z |
| objective:media_ready:activation_status | activation_status | PLANNED | OWNER_DECLARED | derived from objective dashboard for media_ready | 2026-08-06T05:40:41Z |
| objective:media_ready:completion_percentage | completion_percentage |  | REPOSITORY_DERIVED | derived from objective dashboard for media_ready | 2026-08-06T05:37:12Z |
| objective:media_ready:milestone_count | milestone_count | 3 | REPOSITORY_DERIVED | derived from objective dashboard for media_ready | 2026-08-06T05:37:12Z |
| objective:media_ready:current_blocker | current_blocker | canonical_universe | REPOSITORY_DERIVED | derived from objective dashboard for media_ready | 2026-08-06T05:37:12Z |
| objective:media_ready:current_executable_capability | current_executable_capability | canonical_universe | REPOSITORY_DERIVED | derived from objective dashboard for media_ready | 2026-08-06T05:37:12Z |
| objective:media_ready:owner_approval_state | owner_approval_state | OWNER_DECLARED | OWNER_DECLARED | derived from objective dashboard for media_ready | 2026-08-06T05:40:41Z |
| objective:recommendation_production_ready:activation_status | activation_status | PLANNED | OWNER_DECLARED | derived from objective dashboard for recommendation_production_ready | 2026-08-06T05:40:41Z |
| objective:recommendation_production_ready:completion_percentage | completion_percentage | 50.0 | REPOSITORY_DERIVED | derived from objective dashboard for recommendation_production_ready | 2026-08-06T05:37:12Z |
| objective:recommendation_production_ready:milestone_count | milestone_count | 3 | REPOSITORY_DERIVED | derived from objective dashboard for recommendation_production_ready | 2026-08-06T05:37:12Z |
| objective:recommendation_production_ready:current_blocker | current_blocker | canonical_universe | REPOSITORY_DERIVED | derived from objective dashboard for recommendation_production_ready | 2026-08-06T05:37:12Z |
| objective:recommendation_production_ready:current_executable_capability | current_executable_capability | canonical_universe | REPOSITORY_DERIVED | derived from objective dashboard for recommendation_production_ready | 2026-08-06T05:37:12Z |
| objective:recommendation_production_ready:owner_approval_state | owner_approval_state | OWNER_DECLARED | OWNER_DECLARED | derived from objective dashboard for recommendation_production_ready | 2026-08-06T05:40:41Z |
| objective:provider_portal_production_ready:activation_status | activation_status | PLANNED | OWNER_DECLARED | derived from objective dashboard for provider_portal_production_ready | 2026-08-06T05:40:41Z |
| objective:provider_portal_production_ready:completion_percentage | completion_percentage | 100.0 | REPOSITORY_DERIVED | derived from objective dashboard for provider_portal_production_ready | 2026-08-06T05:37:12Z |
| objective:provider_portal_production_ready:milestone_count | milestone_count | 2 | REPOSITORY_DERIVED | derived from objective dashboard for provider_portal_production_ready | 2026-08-06T05:37:12Z |
| objective:provider_portal_production_ready:current_blocker | current_blocker |  | REPOSITORY_DERIVED | derived from objective dashboard for provider_portal_production_ready | 2026-08-06T05:37:12Z |
| objective:provider_portal_production_ready:current_executable_capability | current_executable_capability | provider_intelligence | REPOSITORY_DERIVED | derived from objective dashboard for provider_portal_production_ready | 2026-08-06T05:37:12Z |
| objective:provider_portal_production_ready:owner_approval_state | owner_approval_state | OWNER_DECLARED | OWNER_DECLARED | derived from objective dashboard for provider_portal_production_ready | 2026-08-06T05:40:41Z |

## Partially Verified Claims

| Claim ID | Field | Value | Missing Proof Classes | Last Verified |
| --- | --- | --- | --- | --- |
| capability:source_intelligence:implementation_status | implementation_status | IN_PROGRESS | test_evidence | 2026-08-06T05:37:03Z |
| capability:source_intelligence:production_readiness | production_readiness | BLOCKED | test_evidence | 2026-08-06T05:37:03Z |
| capability:source_intelligence:canonical_owner | canonical_owner | OPTIME Source Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:source_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['market_builder', 'canonical_universe', 'data_quality_trust', 'chief_ai_supervisor'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:37:03Z |
| capability:source_intelligence:assigned_agent | assigned_agent | OPTIME Source Intelligence | test_evidence | 2026-08-06T05:37:03Z |
| capability:source_intelligence:test_coverage | test_coverage | 2 | test_evidence | 2026-08-06T05:37:03Z |
| capability:market_builder:implementation_status | implementation_status | NOT_STARTED | runtime_evidence | 2026-08-05T12:11:52Z |
| capability:market_builder:production_readiness | production_readiness | BLOCKED | runtime_evidence | 2026-08-05T12:11:52Z |
| capability:market_builder:canonical_owner | canonical_owner | OPTIME Market Intelligence | runtime_evidence | 2026-08-06T05:40:41Z |
| capability:market_builder:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance', 'source_intelligence'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['canonical_universe'], 'monitoring_relationships': []} | runtime_evidence | 2026-08-05T12:11:52Z |
| capability:market_builder:assigned_agent | assigned_agent | OPTIME Market Intelligence | runtime_evidence | 2026-08-05T12:11:52Z |
| capability:market_builder:test_coverage | test_coverage | 1 | runtime_evidence | 2026-08-05T12:11:52Z |
| capability:government_identity:implementation_status | implementation_status | IMPLEMENTED | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:government_identity:production_readiness | production_readiness | BLOCKED | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:government_identity:canonical_owner | canonical_owner | OPTIME Identity Governance | runtime_evidence | 2026-08-06T05:40:41Z |
| capability:government_identity:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['canonical_universe'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['media_intelligence', 'recommendation_decision_engine', 'assessment_experience'], 'monitoring_relationships': []} | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:government_identity:assigned_agent | assigned_agent | OPTIME Identity Governance | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:government_identity:test_coverage | test_coverage | 1 | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:media_intelligence:implementation_status | implementation_status | IN_PROGRESS | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:media_intelligence:production_readiness | production_readiness | BLOCKED | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:media_intelligence:canonical_owner | canonical_owner | OPTIME Media Intelligence | runtime_evidence | 2026-08-06T05:40:41Z |
| capability:media_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['canonical_universe', 'government_identity'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['recommendation_decision_engine', 'assessment_experience'], 'monitoring_relationships': []} | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:media_intelligence:assigned_agent | assigned_agent | OPTIME Media Intelligence | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:media_intelligence:test_coverage | test_coverage | 1 | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:knowledge_graph:implementation_status | implementation_status | IMPLEMENTED | test_evidence | 2026-08-06T05:29:18Z |
| capability:knowledge_graph:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:knowledge_graph:canonical_owner | canonical_owner | OPTIME Knowledge Graph Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:knowledge_graph:dependency_declarations | dependency_declarations | {'required_build_dependencies': [], 'required_runtime_dependencies': [], 'evidence_dependencies': ['source_intelligence', 'canonical_universe'], 'optional_consumers': ['provider_intelligence', 'clinical_knowledge', 'assessment_experience', 'recommendation_decision_engine', 'chief_ai_supervisor'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:knowledge_graph:assigned_agent | assigned_agent | knowledge_graph | test_evidence | 2026-08-06T05:29:18Z |
| capability:knowledge_graph:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:activities_intelligence:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:activities_intelligence:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:activities_intelligence:canonical_owner | canonical_owner | OPTIME Lifestyle Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:activities_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['provider_intelligence', 'outcome_learning', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['recommendation_decision_engine', 'assessment_experience', 'narrative_intelligence'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:activities_intelligence:assigned_agent | assigned_agent | activities_intelligence | test_evidence | 2026-08-06T05:29:18Z |
| capability:activities_intelligence:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:clinical_knowledge:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:clinical_knowledge:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:clinical_knowledge:canonical_owner | canonical_owner | OPTIME Clinical Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:clinical_knowledge:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['provider_intelligence', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': ['clinical_evidence', 'outcome_learning'], 'optional_consumers': ['assessment_experience', 'recommendation_decision_engine', 'family_experience_intelligence'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:clinical_knowledge:assigned_agent | assigned_agent | clinical_knowledge | test_evidence | 2026-08-06T05:29:18Z |
| capability:clinical_knowledge:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:clinical_evidence:implementation_status | implementation_status | IN_PROGRESS | implementation_evidence, test_evidence | 2026-07-18T05:44:31Z |
| capability:clinical_evidence:production_readiness | production_readiness | BLOCKED | implementation_evidence, test_evidence | 2026-07-18T05:44:31Z |
| capability:clinical_evidence:canonical_owner | canonical_owner | OPTIME Evidence Intelligence | implementation_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:clinical_evidence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['clinical_knowledge', 'recommendation_decision_engine', 'narrative_intelligence'], 'monitoring_relationships': []} | implementation_evidence, test_evidence | 2026-07-18T05:44:31Z |
| capability:clinical_evidence:assigned_agent | assigned_agent | OPTIME Evidence Intelligence | implementation_evidence, test_evidence | 2026-07-18T05:44:31Z |
| capability:clinical_evidence:test_coverage | test_coverage |  | implementation_evidence, test_evidence | 2026-07-18T05:44:31Z |
| capability:narrative_intelligence:implementation_status | implementation_status | IN_PROGRESS | implementation_evidence, test_evidence | 2026-07-18T16:46:28Z |
| capability:narrative_intelligence:production_readiness | production_readiness | BLOCKED | implementation_evidence, test_evidence | 2026-07-18T16:46:28Z |
| capability:narrative_intelligence:canonical_owner | canonical_owner | OPTIME Narrative Intelligence | implementation_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:narrative_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['provider_intelligence', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': ['clinical_knowledge', 'clinical_evidence', 'matching_improvement'], 'optional_consumers': ['family_experience_intelligence', 'recommendation_decision_engine'], 'monitoring_relationships': []} | implementation_evidence, test_evidence | 2026-07-18T16:46:28Z |
| capability:narrative_intelligence:assigned_agent | assigned_agent | OPTIME Narrative Intelligence | implementation_evidence, test_evidence | 2026-07-18T16:46:28Z |
| capability:narrative_intelligence:test_coverage | test_coverage |  | implementation_evidence, test_evidence | 2026-07-18T16:46:28Z |
| capability:nutrition_intelligence:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:nutrition_intelligence:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:nutrition_intelligence:canonical_owner | canonical_owner | OPTIME Nutrition Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:nutrition_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['provider_intelligence', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': ['clinical_knowledge'], 'optional_consumers': ['recommendation_decision_engine', 'assessment_experience'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:nutrition_intelligence:assigned_agent | assigned_agent | nutrition_intelligence | test_evidence | 2026-08-06T05:29:18Z |
| capability:nutrition_intelligence:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:outcome_learning:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:outcome_learning:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:outcome_learning:canonical_owner | canonical_owner | OPTIME Outcome Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:outcome_learning:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['knowledge_graph', 'matching_improvement'], 'required_runtime_dependencies': [], 'evidence_dependencies': ['clinical_knowledge'], 'optional_consumers': ['recommendation_decision_engine', 'chief_ai_supervisor'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:outcome_learning:assigned_agent | assigned_agent | outcome_learning | test_evidence | 2026-08-06T05:29:18Z |
| capability:outcome_learning:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:resident_needs_intelligence:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:resident_needs_intelligence:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:resident_needs_intelligence:canonical_owner | canonical_owner | OPTIME Resident Needs Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:resident_needs_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['provider_intelligence', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['assessment_experience', 'recommendation_decision_engine'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:resident_needs_intelligence:assigned_agent | assigned_agent | resident_needs | test_evidence | 2026-08-06T05:29:18Z |
| capability:resident_needs_intelligence:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:senior_living_research:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:senior_living_research:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:senior_living_research:canonical_owner | canonical_owner | OPTIME Senior Living Research | test_evidence | 2026-08-06T05:40:41Z |
| capability:senior_living_research:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['provider_intelligence', 'knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['chief_ai_supervisor', 'knowledge_graph'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:senior_living_research:assigned_agent | assigned_agent | senior_living_research | test_evidence | 2026-08-06T05:29:18Z |
| capability:senior_living_research:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:family_experience_intelligence:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-06T05:29:18Z |
| capability:family_experience_intelligence:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-06T05:29:18Z |
| capability:family_experience_intelligence:canonical_owner | canonical_owner | OPTIME Family Experience Intelligence | test_evidence | 2026-08-06T05:40:41Z |
| capability:family_experience_intelligence:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['knowledge_graph'], 'required_runtime_dependencies': [], 'evidence_dependencies': ['narrative_intelligence'], 'optional_consumers': ['assessment_experience', 'recommendation_decision_engine'], 'monitoring_relationships': []} | test_evidence | 2026-08-06T05:29:18Z |
| capability:family_experience_intelligence:assigned_agent | assigned_agent | family_experience | test_evidence | 2026-08-06T05:29:18Z |
| capability:family_experience_intelligence:test_coverage | test_coverage |  | test_evidence | 2026-08-06T05:29:18Z |
| capability:assessment_experience:implementation_status | implementation_status | VERIFIED | implementation_evidence, runtime_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:assessment_experience:production_readiness | production_readiness | PRODUCTION_READY | implementation_evidence, runtime_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:assessment_experience:canonical_owner | canonical_owner | OPTIME Assessment Experience | implementation_evidence, runtime_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:assessment_experience:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['knowledge_graph', 'resident_needs_intelligence'], 'required_runtime_dependencies': [], 'evidence_dependencies': ['family_experience_intelligence'], 'optional_consumers': ['recommendation_decision_engine', 'canonical_universe'], 'monitoring_relationships': []} | implementation_evidence, runtime_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:assessment_experience:assigned_agent | assigned_agent | OPTIME Assessment Experience | implementation_evidence, runtime_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:assessment_experience:test_coverage | test_coverage | 3 | implementation_evidence, runtime_evidence, test_evidence | 2026-08-06T05:40:41Z |
| capability:recommendation_decision_engine:implementation_status | implementation_status | IMPLEMENTED | runtime_evidence | 2026-08-05T10:04:15Z |
| capability:recommendation_decision_engine:production_readiness | production_readiness | BLOCKED | runtime_evidence | 2026-08-05T10:04:15Z |
| capability:recommendation_decision_engine:canonical_owner | canonical_owner | OPTIME Recommendation Engine | runtime_evidence | 2026-08-06T05:40:41Z |
| capability:recommendation_decision_engine:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['canonical_universe', 'knowledge_graph', 'assessment_experience'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['family_experience_intelligence', 'chief_ai_supervisor'], 'monitoring_relationships': []} | runtime_evidence | 2026-08-05T10:04:15Z |
| capability:recommendation_decision_engine:assigned_agent | assigned_agent | OPTIME Recommendation Engine | runtime_evidence | 2026-08-05T10:04:15Z |
| capability:recommendation_decision_engine:test_coverage | test_coverage | 1 | runtime_evidence | 2026-08-05T10:04:15Z |
| capability:chief_ai_supervisor:implementation_status | implementation_status | VERIFIED | runtime_evidence | 2026-08-06T05:37:03Z |
| capability:chief_ai_supervisor:production_readiness | production_readiness | BLOCKED | runtime_evidence | 2026-08-06T05:37:03Z |
| capability:chief_ai_supervisor:canonical_owner | canonical_owner | OPTIME Platform Governance | runtime_evidence | 2026-08-06T05:40:41Z |
| capability:chief_ai_supervisor:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance'], 'required_runtime_dependencies': ['platform_registry', 'report_archive', 'runtime_sync', 'remediation_policy_engine'], 'evidence_dependencies': [], 'optional_consumers': ['daily_system_health_report', 'platform_registry', 'remediation_policy_engine'], 'monitoring_relationships': ['source_intelligence', 'market_builder', 'canonical_universe', 'data_quality_trust', 'email_delivery']} | runtime_evidence | 2026-08-06T05:37:03Z |
| capability:chief_ai_supervisor:assigned_agent | assigned_agent | OPTIME Platform Governance | runtime_evidence | 2026-08-06T05:37:03Z |
| capability:chief_ai_supervisor:test_coverage | test_coverage | 3 | runtime_evidence | 2026-08-06T05:37:03Z |
| capability:email_delivery:implementation_status | implementation_status | IMPLEMENTED | test_evidence | 2026-07-19T14:08:21Z |
| capability:email_delivery:production_readiness | production_readiness | BLOCKED | test_evidence | 2026-07-19T14:08:21Z |
| capability:email_delivery:canonical_owner | canonical_owner | OPTIME Operations | test_evidence | 2026-08-06T05:40:41Z |
| capability:email_delivery:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['report_archive', 'constitution_governance'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['daily_system_health_report', 'chief_ai_supervisor'], 'monitoring_relationships': []} | test_evidence | 2026-07-19T14:08:21Z |
| capability:email_delivery:assigned_agent | assigned_agent | OPTIME Operations | test_evidence | 2026-07-19T14:08:21Z |
| capability:email_delivery:test_coverage | test_coverage |  | test_evidence | 2026-07-19T14:08:21Z |
| capability:report_archive:implementation_status | implementation_status | VERIFIED | test_evidence | 2026-08-05T10:04:16Z |
| capability:report_archive:production_readiness | production_readiness | PRODUCTION_READY | test_evidence | 2026-08-05T10:04:16Z |
| capability:report_archive:canonical_owner | canonical_owner | OPTIME Platform Operations | test_evidence | 2026-08-06T05:40:41Z |
| capability:report_archive:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['constitution_governance'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['daily_system_health_report', 'chief_ai_supervisor'], 'monitoring_relationships': []} | test_evidence | 2026-08-05T10:04:16Z |
| capability:report_archive:assigned_agent | assigned_agent | OPTIME Platform Operations | test_evidence | 2026-08-05T10:04:16Z |
| capability:report_archive:test_coverage | test_coverage |  | test_evidence | 2026-08-05T10:04:16Z |
| capability:daily_system_health_report:implementation_status | implementation_status | VERIFIED | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:daily_system_health_report:production_readiness | production_readiness | BLOCKED | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:daily_system_health_report:canonical_owner | canonical_owner | OPTIME Chief AI Supervisor | runtime_evidence | 2026-08-06T05:40:41Z |
| capability:daily_system_health_report:dependency_declarations | dependency_declarations | {'required_build_dependencies': ['chief_ai_supervisor', 'report_archive'], 'required_runtime_dependencies': [], 'evidence_dependencies': [], 'optional_consumers': ['chief_ai_supervisor', 'email_delivery'], 'monitoring_relationships': []} | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:daily_system_health_report:assigned_agent | assigned_agent | OPTIME Chief AI Supervisor | runtime_evidence | 2026-08-05T12:11:51Z |
| capability:daily_system_health_report:test_coverage | test_coverage | 1 | runtime_evidence | 2026-08-05T12:11:51Z |

## Unverified Claims

| Claim ID | Field | Value | Missing Proof Classes |
| --- | --- | --- | --- |

## Stale Claims

| Claim ID | Field | Value | Missing Proof Classes |
| --- | --- | --- | --- |

## Regressions

| Claim ID | Field | Value | Missing Proof Classes |
| --- | --- | --- | --- |

## Integrity Findings

| Finding ID | Severity | Capability | Type | Impact | Automatic Fix Allowed | Owner Decision Required | Recommended Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
