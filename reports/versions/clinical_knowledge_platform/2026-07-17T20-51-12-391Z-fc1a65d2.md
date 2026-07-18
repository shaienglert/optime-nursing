# Clinical Knowledge Platform

## Mission

Build a continuously learning clinical intelligence layer that improves recommendation quality, missing-data detection, and clinical explanations without replacing verified facility facts.

## Clinical Knowledge Agent Scope

The Clinical Knowledge Agent continuously studies:

- Geriatrics
- Skilled Nursing
- Rehabilitation
- Stroke
- Parkinson disease
- Dementia
- Falls
- Nutrition
- Depression
- Loneliness
- Mobility
- Palliative Care

## Trusted Sources

- CMS
- PubMed
- NIH
- CDC
- AGS
- Cochrane
- AHRQ
- JAMA
- NEJM

## Source Trust Policy

- Tier 1 (Verified Facts): CMS, state inspection feeds, provider-verified portal submissions.
- Tier 2 (Clinical Evidence): Peer-reviewed and guideline sources listed above.
- Tier 3 (Inferential Signals): Model-derived associations from anonymized outcomes.

Verified facts always remain authoritative. Agents can only augment confidence, context, and question generation.

## Output: Clinical Knowledge Graph

The agent emits a graph of clinical entities, requirements, interventions, and outcomes.

Example chain:

- Stroke
  - Speech therapy
  - Swallow evaluation
  - Fall prevention

Additional examples:

- Dementia
  - Memory care programming
  - Wandering safeguards
  - Structured routines
- Parkinson disease
  - PT/OT intensity
  - Mobility support
  - Medication-timing consistency

## Matching Engine Interaction

The clinical graph contributes to:

- Mandatory and critical requirement mapping
- Clinical explanation narratives
- Missing information detection (for verification checklist)
- Confidence calibration when high-impact clinical fields are UNKNOWN

The clinical graph does not directly overwrite facility capability states marked as verified.

## Facility Memory Engine Interaction

The Clinical Knowledge Agent reads memory state before producing recommendations:

- Current capability state (YES/NO/UNKNOWN)
- Verification confidence
- Conflict markers
- Data freshness and expiry

It writes:

- Suggested verification questions
- Clinical rationale for why each missing field matters
- Confidence adjustment proposals

It never mutates verified facts.

## Database Design (Clinical Layer)

### Table: clinical_knowledge_topics

- id (PK)
- topic_key (unique)
- title
- specialty_area
- guideline_summary
- evidence_strength
- updated_at

### Table: clinical_evidence_sources

- id (PK)
- topic_id (FK clinical_knowledge_topics.id)
- source_name
- source_type
- publication_date
- citation
- trust_tier
- extracted_summary
- created_at

### Table: clinical_condition_care_links

- id (PK)
- condition_key
- required_capability_key
- importance_tier
- rationale
- evidence_score
- created_at

### Table: clinical_explanation_templates

- id (PK)
- condition_key
- template_key
- explanation_text
- trigger_requirements_json
- created_at
- updated_at

### Table: clinical_missing_info_rules

- id (PK)
- condition_key
- missing_field_key
- risk_if_unknown
- verification_prompt
- priority
- created_at

## APIs

- GET /intelligence/clinical/topics
- GET /intelligence/clinical/conditions/{condition_key}/requirements
- GET /intelligence/clinical/explanations/{condition_key}
- POST /intelligence/clinical/evidence/refresh
- POST /intelligence/clinical/missing-info/analyze

## Update Frequency

- CMS/state verification overlays: daily
- Literature ingestion: weekly
- Guideline synthesis refresh: biweekly
- Explanation template tuning from outcomes: monthly

## Safety Rules

- No generated claim can be promoted to verified fact without trusted source evidence.
- Unknown remains UNKNOWN until verified.
- Clinical narratives must reference known evidence or clearly mark uncertainty.

## Validation Criteria

Clinical platform is valid only if:

- All required sources are active.
- Graph contains condition-to-capability mappings for all target areas.
- Generated explanations align with condition-specific evidence.
- No writes alter verified capability facts.
