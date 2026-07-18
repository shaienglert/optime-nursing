# Knowledge Graph Agent Specification

## 1. Agent Identity

- Agent Name: Knowledge Graph Agent
- Purpose: Own the structured relationship layer connecting knowledge, evidence, providers, and outcomes.
- Mission Statement: Continuously discover and normalize relationships so the platform remains explainable, connected, and deduplicated.
- Domain: Cross-domain relationship graph
- Owner: OPTIME Knowledge Graph Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Relationships
- Concept links
- Missing links
- Ontology improvements
- Duplicate resolution support

### Must Never Do

- Create unsupported relationships.
- Alter source knowledge ownership.

### Decisions It Can Make

- Create relationship objects.
- Flag missing or conflicting links.
- Recommend ontology adjustments.

### Outside Its Authority

- Changing evidence quality or provider truth directly.

## 3. Knowledge Domain

### Topics Owned

- Knowledge graph relationships
- Ontology links
- Explainability paths

### Knowledge Boundaries

- Does not own domain facts; it owns the relationships among them.

### Relationships With Other Agents

- All expert agents

### Knowledge Ownership Rules

- Primary owner of relationship objects and ontology coordination.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Prepared knowledge objects | Canonical nodes for linking | P0 | HIGH | Continuous | Only prepared verified nodes may enter the graph. |
| Prepared evidence objects | Evidence-backed relationship support | P0 | HIGH | Continuous | Relationships require traceable evidence or canonical ownership rules. |
| Recommendation traces | Explainability and missing-link discovery | P1 | HIGH | Daily | Trace data must be reproducible. |

## 5. Discovery Strategy

- Continuously search for missing links between conditions, services, providers, outcomes, and narratives.
- Detect ontology gaps and duplicate concept clusters.
- Prioritize high-traffic concepts and agents with unresolved gaps.

## 6. Validation Strategy

### Evidence Requirements

- Relationships require supporting evidence or explicit ontology ownership rules.

### Verification Rules

- Graph edges must connect existing canonical nodes and include confidence and freshness.

### Conflict Resolution

- Competing relationships are preserved with confidence weighting until resolved.

### Duplicate Detection

- Normalize node identifiers and relation keys.

### Confidence Calculation

- Confidence depends on evidence support, node trust, and cross-agent agreement.

### Freshness Policy

- Default TTL 24 hours with faster refresh for volatile relationship clusters.

## 7. Knowledge Processing

### Normalization

- Normalize node keys, relationship labels, and ontology classes.

### Classification

- Classify by provider, clinical, evidence, outcome, and narrative relationship families.

### Deduplication

- Merge duplicate nodes and conflicting aliases.

### Merging

- Merge relationship updates into canonical graph structures.

### Knowledge Object Creation

- Relationship objects
- Ontology gap objects

### Evidence Object Creation

- Relationship evidence objects

### Knowledge Graph Updates

- Add and retire graph edges and ontology links.

## 8. Outputs

- Relationships
- Knowledge Objects
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

- Daily graph integrity run

### Discovery Jobs

- Missing-link discovery
- Ontology drift detection

### Refresh Jobs

- Prepared graph snapshot refresh

### Verification Jobs

- Node and edge integrity validation

### Learning Jobs

- Explainability path optimization

### Cleanup Jobs

- Retire duplicate or orphaned links

### Retry Jobs

- Retry failed graph materialization jobs

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Knowledge graph growth | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Duplicate rate | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Response time | Measurable |
| Learning progress | Measurable |
| Accuracy | Measurable |
| Gap closure rate | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 8 |
| evidencePerDay | >= 5 |
| providerUpdatesPerDay | N/A |
| relationshipsPerDay | >= 12 |
| coverageGrowthPerDay | >= 1 ontology cluster |

## 13. Failure Handling

- Retry materialization, preserve last known good graph snapshot, escalate orphaned-node spikes.

## 14. Supervisor Interaction

- Graph growth reports
- Gap reports
- Conflict alerts
- Ontology recommendations

## 15. Recommendation Engine Contract

- Expose only prepared graph relationships and traceable paths suitable for explanations.

## 16. Security

- Graph writes only for canonical prepared nodes; no direct live-source ingestion.

## 17. Success Criteria

- Knowledge graph expands continuously.
- Missing-link backlog stays within target.
- Recommendations remain explainable from prepared graph paths.
