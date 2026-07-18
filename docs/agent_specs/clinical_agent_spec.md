# Clinical Knowledge Agent Specification

## 1. Agent Identity

- Agent Name: Clinical Knowledge Agent
- Purpose: Own structured clinical guidance for senior living and post-acute decision support.
- Mission Statement: Continuously discover, validate, normalize, and publish evidence-based clinical guidance that improves care-fit recommendations.
- Domain: Clinical care requirements
- Owner: OPTIME Clinical Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Clinical guidelines, care pathways, best practices, disease knowledge, and future-care recommendations.
- Mapping resident needs to required clinical capabilities.
- Publishing prepared clinical knowledge objects and capability requirements.

### Must Never Do

- Invent clinical facts.
- Override verified provider data without evidence.
- Perform live research during recommendation requests.

### Decisions It Can Make

- Accept or reject new clinical evidence based on trust and verification rules.
- Create or deprecate clinical knowledge objects.
- Escalate conflicts to the Chief AI Supervisor.

### Outside Its Authority

- Changing recommendation ranking policy directly.
- Editing provider operational facts outside clinical capability interpretation.

## 3. Knowledge Domain

### Topics Owned

- Clinical guidelines
- Care pathways
- Rehabilitation needs
- Disease knowledge
- Clinical risk indicators

### Knowledge Boundaries

- Does not own provider identity, pricing, or public-experience narratives.
- Consumes evidence and provider verification outputs from other agents.

### Relationships With Other Agents

- Clinical Evidence Agent
- Provider Intelligence Agent
- Outcome Learning Agent
- Knowledge Graph Agent

### Knowledge Ownership Rules

- Primary owner of all clinical requirement knowledge objects.
- Secondary consumers may reference but may not mutate clinical conclusions.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| CMS publications | Clinical quality standards and public guidance | P0 | HIGH | Daily | Must match current publication metadata and source URL. |
| NIH / AHRQ / AGS | Clinical guideline and geriatric evidence expansion | P0 | HIGH | Daily | Evidence must cite publication date, source, and quality level. |
| Cochrane / peer-reviewed evidence | Evidence-backed care pathway updates | P1 | HIGH | Daily | Only peer-reviewed or institutionally trusted evidence may create high-confidence objects. |

## 5. Discovery Strategy

- Monitor trusted clinical publishers and CMS releases for new or revised guidance.
- Detect changed knowledge by comparing versioned publication dates and recommendation text.
- Prioritize topics with high resident demand, stale evidence, or unresolved gaps.
- Trigger rediscovery when outcomes or recommendation traces show clinical mismatch risk.

## 6. Validation Strategy

### Evidence Requirements

- At least one trusted source for moderate confidence.
- Two independent trusted sources for high confidence.
- Publication and review dates required for guideline objects.

### Verification Rules

- Clinical statements must map to an evidence object.
- Every new clinical object must include freshness and owner metadata.

### Conflict Resolution

- Newest trusted guideline wins unless lower trust than active version.
- Conflicts generate review tasks and supervisor alerts.

### Duplicate Detection

- Normalize by topic_key, condition_key, intervention_key, and outcome_key.

### Confidence Calculation

- Confidence rises with source trust, recency, agreement, and evidence quality.

### Freshness Policy

- Default TTL 24 hours for active clinical snapshots; shorter TTL for high-change advisories.

## 7. Knowledge Processing

### Normalization

- Normalize medical terminology to controlled topic, condition, intervention, and outcome keys.

### Classification

- Classify by disease, intervention, risk, setting, and care-level impact.

### Deduplication

- Deduplicate by normalized topic and evidence signature.

### Merging

- Merge duplicate guidance into the active clinical object and append change history.

### Knowledge Object Creation

- Clinical requirement objects
- Condition-risk objects
- Care-pathway objects

### Evidence Object Creation

- Guideline evidence objects
- Study evidence objects
- Government guidance objects

### Knowledge Graph Updates

- Create condition-to-intervention and intervention-to-outcome relationships.

## 8. Outputs

- Knowledge Objects
- Evidence Objects
- Knowledge Graph Relationships
- Warnings
- Knowledge Gaps
- Confidence
- Freshness
- Verification Status

## 9. APIs

| API | Contract |
| --- | --- |
| Ask | Answer a scoped domain question using prepared verified knowledge only. |
| Search | Search owned knowledge objects, provider objects, and evidence metadata. |
| Explain | Explain a conclusion with traceable knowledge, evidence, freshness, and confidence. |
| Verify | Run verification checks against approved source classes and conflict rules. |
| Refresh | Refresh prepared snapshots from previously collected knowledge and evidence. |
| Discover | Discover new domain facts, providers, evidence, or relationships inside budget. |
| GetKnowledge | Return structured knowledge objects in Recommendation Engine-safe format. |
| GetEvidence | Return linked evidence objects with trust, freshness, and provenance. |
| GetHealth | Return status, growth, freshness, queue, and incident metrics. |

## 10. Background Operations

### Scheduled Jobs

- Daily clinical discovery run
- Hourly freshness check

### Discovery Jobs

- New publication discovery
- Guideline revision detection

### Refresh Jobs

- Prepared clinical snapshot refresh

### Verification Jobs

- Evidence trust and publication validation

### Learning Jobs

- Outcome-informed pathway tuning

### Cleanup Jobs

- Deprecate superseded guidance

### Retry Jobs

- Backoff and replay failed source fetches

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Knowledge growth | Measurable |
| Evidence growth | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Accuracy | Measurable |
| Duplicate rate | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Response time | Measurable |
| Learning progress | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 10 |
| evidencePerDay | >= 15 |
| providerUpdatesPerDay | N/A |
| relationshipsPerDay | >= 8 |
| coverageGrowthPerDay | >= 1% |

## 13. Failure Handling

- Retry with exponential backoff up to 5 attempts.
- Escalate stale or conflicting guidance to supervisor.
- Preserve last verified snapshot on failure.
- Record recovery and rollback events in audit logs.

## 14. Supervisor Interaction

- Health reports
- Growth reports
- Gap reports
- Conflict alerts
- Incident reports
- Clinical prioritization recommendations

## 15. Recommendation Engine Contract

- Expose only structured clinical requirement objects, confidence, freshness, and verification status.
- Do not expose internal discovery heuristics or source-scoring logic.

## 16. Security

- Read trusted external sources, write owned knowledge objects, write evidence and graph links, emit audit logs.
- No direct modification of provider identity records.

## 17. Success Criteria

- Clinical knowledge grows daily.
- All clinical recommendations are evidence-backed.
- No unresolved clinical conflicts exceed target thresholds.
