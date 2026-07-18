# Knowledge Graph Design

## Purpose

Connect cross-agent intelligence into a single explainable structure that supports matching, confidence scoring, question generation, and continuous learning while preserving verified-fact integrity.

## Core Graph Example

- Stroke
  - requires -> Speech Therapy
  - requires -> Swallow Evaluation
  - mitigation -> Fall Prevention
- Speech Therapy
  - delivered_by -> Certified SLP
- Certified SLP
  - improves -> Communication Ability
- Communication Ability
  - influences -> Family Satisfaction

## Entity Types

- ResidentProfile
- ClinicalCondition
- CareCapability
- Facility
- ProviderSubmission
- ActivityType
- NutritionCapability
- FamilySignal
- OutcomeEvent
- EvidenceSource
- VerificationQuestion

## Relationship Types

- has_condition
- requires_capability
- offers_capability
- capability_verified_by
- capability_conflicted_by
- capability_expired_on
- improves_outcome
- linked_to_family_signal
- supported_by_evidence
- suggested_question

## Graph Integrity Rules

- Verified facility capabilities are immutable from agent inference writes.
- Each edge carries provenance, trust tier, confidence, and recency metadata.
- Conflicts create parallel conflict edges, not destructive updates.
- Unknown values remain explicit and queryable.

## Database Design

### Table: kg_entities

- id (PK)
- entity_type
- entity_key (unique)
- display_name
- attributes_json
- created_at
- updated_at

### Table: kg_relationships

- id (PK)
- from_entity_id (FK kg_entities.id)
- relation_type
- to_entity_id (FK kg_entities.id)
- weight
- confidence
- provenance
- source_event_id
- is_verified
- valid_from
- valid_to
- created_at

### Table: kg_source_lineage

- id (PK)
- relationship_id (FK kg_relationships.id)
- source_name
- source_url
- source_type
- trust_tier
- evidence_excerpt
- collected_at

### Table: kg_conflict_edges

- id (PK)
- relationship_id (FK kg_relationships.id)
- conflict_source
- conflict_statement
- conflict_severity
- resolution_status
- created_at
- resolved_at

### Table: kg_feature_materializations

- id (PK)
- facility_id
- resident_profile_hash
- feature_bundle_json
- explanation_bundle_json
- confidence_bundle_json
- generated_at

### Table: kg_agent_contributions

- id (PK)
- run_id
- agent_name
- facility_id
- contribution_type
- contribution_payload_json
- confidence_delta
- created_at

## Query Patterns

- Explain why a facility ranked high for a clinical profile.
- Find all missing high-impact capabilities for a resident-condition pair.
- Identify conflicting evidence on a capability and its source lineage.
- Retrieve agent-by-agent contribution summary for one recommendation run.

## APIs

- GET /intelligence/kg/entity/{entity_key}
- GET /intelligence/kg/facility/{facility_id}/explain
- GET /intelligence/kg/facility/{facility_id}/gaps
- GET /intelligence/kg/runs/{run_id}/contributions
- POST /intelligence/kg/upsert-entities
- POST /intelligence/kg/upsert-relationships
- POST /intelligence/kg/materialize-features

## Matching Engine Interaction

- Receives materialized feature bundles from kg_feature_materializations.
- Uses trust- and recency-weighted relationship confidence for confidence scoring.
- Uses graph lineage to produce traceable family-facing narratives.

## Facility Memory Engine Interaction

- Reads memory confidence/conflict/expiry to weight capability edges.
- Writes non-destructive conflict annotations to kg_conflict_edges.
- Syncs verified capability state to is_verified edges only.

## Privacy and Compliance

- Resident identifiers are hashed tokens in graph operations.
- Outcome nodes store anonymous event data only.
- Family feedback uses de-identified text features, not raw PII.
