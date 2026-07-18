# Database Review

## Scope

Review of existing SQLAlchemy tables in facility, questionnaire, and clinical evidence domains with focus on indexing, relationships, normalization, and scaling.

## Current Table Landscape

Core groups present:

- Facility master and CMS-derived quality/staffing/inspection tables.
- Matching and intelligence support tables.
- Provider identity, audit, verification, and memory tables.
- Clinical evidence and graph support tables.

## Part 6: Findings

### Missing Indexes

1. Add composite index on facilities(state, overall_optime_score) to support ranked listing by state.
2. Add index on resident_outcomes(recorded_at, facility_id) for outcome trend queries.
3. Add index on adaptive_question_responses(resident_key, created_at) for session replay.
4. Add index on clinical_evidence(condition_key, intervention_key) for evidence lookups.
5. Add index on recommendation_evidence_links(facility_id, recommendation_run_id).
6. Add index on facility_intelligence_profiles(last_updated) for staleness scans.

### Relationship and Integrity Gaps

1. Several tables use string keys (topic_key, condition_key, intervention_key) where foreign keys would improve integrity.
2. Clinical evidence references are not fully connected with FK constraints to condition/intervention/outcome entities.
3. recommendation_evidence_links table exists but runtime population is not clearly persisted in backend APIs.
4. Some domain entities (provider inbox work items, simulation run ledger) are absent.

### Normalization Issues

1. facility_intelligence_profiles stores many list/object values as JSON text columns, limiting relational querying.
2. Signal provenance and source coverage would scale better in child tables instead of serialized blobs.
3. Update frequency and summary metadata are mixed with analytical values in one wide table.

### Duplicate or Overlapping Structures

1. Capability state appears in both facility_capabilities and facility_verification_memory with partial overlap.
2. Verification response artifacts and memory records may diverge without explicit reconciliation process.

### Future Scaling Concerns

1. SQLite-centric patterns may bottleneck high-write workflows (verification, outcome events, inbox tasks).
2. Heavy markdown-report-driven analytics bypasses database observability and reusable query APIs.
3. Lack of partitioning strategy for event-like tables (audit logs, outcomes, intelligence signals) risks long-term performance degradation.

## Recommended Table Additions

1. provider_inbox_items
2. provider_lead_events
3. matching_policy_versions
4. matching_run_replays
5. simulation_runs
6. report_registry
7. osint_collection_runs
8. evidence_refresh_tasks
9. journey_events
10. api_rate_limit_events

## Recommended Migrations Roadmap

High priority:

- Add missing indexes on high-volume and ranking query paths.
- Add matching policy version and run replay tables.
- Add provider inbox and SLA tables.

Medium priority:

- Normalize intelligence profile JSON blobs into child tables.
- Add simulation and report registries.

Low priority:

- Introduce archive/partition strategy for long-history events.
- Evaluate graph-native storage once relationship volume justifies migration.

## Database Readiness Assessment

- Data model richness: Strong.
- Integrity enforcement: Medium.
- Queryability at scale: Medium-Low without normalization/index improvements.
- Enterprise readiness: Medium after migration hardening.
