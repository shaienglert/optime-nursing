# REAL AGENT VALUE RUN

## Controlled Cohort

- Cohort: Miami-Dade canonical facilities
- Facilities processed: 54
- Automatic agents executed: 11

## First Run Result

- New knowledge records: 173
- New facility intelligence profiles: 54
- New job runs persisted: 11
- Successful refresh events added: 11
- Failed refresh events added: 0

## Agent Outcomes

```json
[
  {
    "agent_key": "activities_intelligence",
    "status": "SUCCESS",
    "items_processed": 0,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": \"SOURCE_NOT_CONNECTED: facility_activity_categories has no records.\", \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 0, \"items_added\": 0, \"items_processed\": 0, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [\"SOURCE_NOT_CONNECTED: facility_activity_categories has no records.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 0, \"sources_checked\": 0, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "clinical_knowledge",
    "status": "SUCCESS",
    "items_processed": 54,
    "items_added": 53,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": null, \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 54, \"items_added\": 53, \"items_processed\": 54, \"items_updated\": 0, \"new_evidence_records\": 53, \"new_findings\": [\"Clinical baseline stored for AZURE SHORES REHAB: staffing=3, quality=4, inspection=2.\", \"Clinical baseline stored for BISCAYNE HEALTH AND REHABILITATION CENTER: staffing=4, quality=5, inspection=4.\", \"Clinical baseline stored for BROOKWOOD GARDENS REHABILITATION AND NURSING CENTE: staffing=4, quality=4, inspection=2.\", \"Clinical baseline stored for CLARIDGE HOUSE NURSING AND REHABILITATION CENTER: staffing=4, quality=4, inspection=2.\", \"Clinical baseline stored for CORAL GABLES NURSING AND REHABILITATION CENTER: staffing=5, quality=4, inspection=5.\"], \"new_verified_facts\": 53, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 3, \"sources_checked\": 3, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "data_quality",
    "status": "SUCCESS",
    "items_processed": 54,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": null, \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 54, \"items_added\": 0, \"items_processed\": 54, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 4, \"sources_checked\": 4, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "family_experience",
    "status": "SUCCESS",
    "items_processed": 0,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": \"SOURCE_NOT_CONNECTED: facility_reviews has no records.\", \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 0, \"items_added\": 0, \"items_processed\": 0, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [\"SOURCE_NOT_CONNECTED: facility_reviews has no records.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 0, \"sources_checked\": 0, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "knowledge_graph",
    "status": "SUCCESS",
    "items_processed": 54,
    "items_added": 53,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": null, \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 54, \"items_added\": 53, \"items_processed\": 54, \"items_updated\": 0, \"new_evidence_records\": 53, \"new_findings\": [\"Relationships stored for AZURE SHORES REHAB -> Miami-Dade / EXCELSIOR CARE GROUP.\", \"Relationships stored for BISCAYNE HEALTH AND REHABILITATION CENTER -> Miami-Dade / ONYX HEALTH.\", \"Relationships stored for BROOKWOOD GARDENS REHABILITATION AND NURSING CENTE -> Miami-Dade / BENJAMIN LANDA.\", \"Relationships stored for CLARIDGE HOUSE NURSING AND REHABILITATION CENTER -> Miami-Dade / VENTURA SERVICES.\", \"Relationships stored for CORAL GABLES NURSING AND REHABILITATION CENTER -> Miami-Dade / None.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 2, \"sources_checked\": 2, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "matching_improvement",
    "status": "SUCCESS",
    "items_processed": 54,
    "items_added": 14,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": null, \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 14, \"facilities_enriched\": 0, \"facilities_processed\": 54, \"items_added\": 14, \"items_processed\": 54, \"items_updated\": 0, \"new_evidence_records\": 14, \"new_findings\": [\"Decision caution stored for BROOKWOOD GARDENS REHABILITATION AND NURSING CENTE: low_inspection_rating.\", \"Decision caution stored for CLARIDGE HOUSE NURSING AND REHABILITATION CENTER: low_inspection_rating.\", \"Decision caution stored for CORAL REEF SUBACUTE CARE CENTER LLC: low_inspection_rating.\", \"Decision caution stored for GARDENS NURSING AND REHAB CENTER: low_inspection_rating.\", \"Decision caution stored for KENDALL LAKES HEALTHCARE AND REHAB CENTER: low_staffing_rating.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 3, \"sources_checked\": 3, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "nutrition_intelligence",
    "status": "SUCCESS",
    "items_processed": 0,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": \"SOURCE_NOT_CONNECTED: facility_capabilities has no nutrition-specific records.\", \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 0, \"items_added\": 0, \"items_processed\": 0, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [\"SOURCE_NOT_CONNECTED: facility_capabilities has no nutrition-specific records.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 0, \"sources_checked\": 0, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "outcome_learning",
    "status": "SUCCESS",
    "items_processed": 0,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": \"SOURCE_NOT_CONNECTED: resident_outcomes has no records.\", \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 0, \"items_added\": 0, \"items_processed\": 0, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [\"SOURCE_NOT_CONNECTED: resident_outcomes has no records.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 0, \"sources_checked\": 0, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "provider_intelligence",
    "status": "SUCCESS",
    "items_processed": 54,
    "items_added": 107,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": null, \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 54, \"facilities_processed\": 54, \"items_added\": 107, \"items_processed\": 54, \"items_updated\": 0, \"new_evidence_records\": 107, \"new_findings\": [\"New provider baseline stored for AZURE SHORES REHAB (105903).\", \"New provider baseline stored for BISCAYNE HEALTH AND REHABILITATION CENTER (105008).\", \"New provider baseline stored for BROOKWOOD GARDENS REHABILITATION AND NURSING CENTE (105550).\", \"New provider baseline stored for CLARIDGE HOUSE NURSING AND REHABILITATION CENTER (105513).\", \"New provider baseline stored for CORAL GABLES NURSING AND REHABILITATION CENTER (105005).\"], \"new_verified_facts\": 53, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 2, \"sources_checked\": 2, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "resident_needs",
    "status": "SUCCESS",
    "items_processed": 0,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": \"SOURCE_NOT_CONNECTED: adaptive_question_responses has no records.\", \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 0, \"items_added\": 0, \"items_processed\": 0, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [\"SOURCE_NOT_CONNECTED: adaptive_question_responses has no records.\"], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 0, \"sources_checked\": 0, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  },
  {
    "agent_key": "senior_living_research",
    "status": "SUCCESS",
    "items_processed": 54,
    "items_added": 0,
    "items_updated": 0,
    "errors": 0,
    "knowledge_gained_json": "{\"blocked_reason\": null, \"changed_facts\": 0, \"contradictions_found\": 0, \"decision_changes\": 0, \"facilities_enriched\": 0, \"facilities_processed\": 54, \"items_added\": 0, \"items_processed\": 54, \"items_updated\": 0, \"new_evidence_records\": 0, \"new_findings\": [], \"new_verified_facts\": 0, \"regulatory_findings\": 0, \"source_requests_failed\": 0, \"source_requests_successful\": 2, \"sources_checked\": 2, \"stale_evidence_refreshed\": 0, \"unknown_resolved\": 0}"
  }
]
```

## Examples Of Real New Value

```json
[
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105903:relationships",
    "summary": "Knowledge graph relationships verified for AZURE SHORES REHAB.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105008:relationships",
    "summary": "Knowledge graph relationships verified for BISCAYNE HEALTH AND REHABILITATION CENTER.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105550:relationships",
    "summary": "Knowledge graph relationships verified for BROOKWOOD GARDENS REHABILITATION AND NURSING CENTE.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105513:relationships",
    "summary": "Knowledge graph relationships verified for CLARIDGE HOUSE NURSING AND REHABILITATION CENTER.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105005:relationships",
    "summary": "Knowledge graph relationships verified for CORAL GABLES NURSING AND REHABILITATION CENTER.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105910:relationships",
    "summary": "Knowledge graph relationships verified for CORAL REEF SUBACUTE CARE CENTER LLC.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105508:relationships",
    "summary": "Knowledge graph relationships verified for East Ridge Rehabilitation and Nursing Center.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:106007:relationships",
    "summary": "Knowledge graph relationships verified for FLORIDEAN HEALTH & REHABILITATION CENTER.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105172:relationships",
    "summary": "Knowledge graph relationships verified for FOUNTAIN MANOR HEALTH & REHABILITATION CENTER.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  },
  {
    "agent_key": "knowledge_graph",
    "record_type": "facility_relationships",
    "entity_key": "facility:105765:relationships",
    "summary": "Knowledge graph relationships verified for GARDENS NURSING AND REHAB CENTER.",
    "source": "CANONICAL_INVENTORY_GRAPH",
    "created_at": "2026-07-20 13:54:15"
  }
]
```

## Second Run Idempotency Result

- New knowledge records on second run: 0
- New facility intelligence profiles on second run: 0
- New duplicate findings persisted: 0
- Agent job runs persisted on second run: 11

## Current Persisted State

- Facility intelligence profiles total: 54
- Knowledge records persisted from the real workflow remain in the canonical database after execution.

## Honest Blocked/No-Source Agents

- Activities Intelligence Agent: `SOURCE_NOT_CONNECTED` (`facility_activity_categories` empty)
- Nutrition Intelligence Agent: `SOURCE_NOT_CONNECTED` (`facility_capabilities` lacks nutrition records)
- Family Experience Intelligence Agent: `SOURCE_NOT_CONNECTED` (`facility_reviews` empty)
- Resident Needs Intelligence Agent: `SOURCE_NOT_CONNECTED` (`adaptive_question_responses` empty)
- Outcome Learning Agent: `SOURCE_NOT_CONNECTED` (`resident_outcomes` empty)

## What Real Work Happened

- Provider Intelligence Agent persisted source-backed provider baselines for Miami-Dade facilities.
- Clinical Knowledge Agent persisted CMS-based clinical baselines.
- Senior Living Research Agent persisted a Miami-Dade market snapshot.
- Knowledge Graph Agent persisted canonical facility relationship records.
- Matching Improvement Agent persisted source-backed decision caution records.
- Data Quality Agent recorded missing authoritative fields as durable known gaps.
- The Organic / AI Authority system performed local technical discoverability checks and persisted those results through the canonical executive report.

## Generated At

- 2026-07-20T13:56:57.461318+00:00
