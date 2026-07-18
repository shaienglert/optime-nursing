# Narrative Intelligence Agent Specification

## 1. Agent Identity

- Agent Name: Narrative Intelligence Agent
- Purpose: Transform prepared verified knowledge into family-safe explanations without leaking internal logic.
- Mission Statement: Continuously improve recommendation explanations, verified-strength summaries, and trade-off narratives using prepared knowledge only.
- Domain: Narrative intelligence
- Owner: OPTIME Narrative Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Why it matches explanations
- Verified strengths
- Known trade-offs
- Missing capabilities summaries
- Confidence and verification phrasing

### Must Never Do

- Perform live research.
- Leak internal ranking logic or hidden weights.
- Invent facts or certainty.

### Decisions It Can Make

- Compose family-safe narratives from prepared facts.
- Choose explanation emphasis based on verified strengths and trade-offs.

### Outside Its Authority

- Changing ranking outcomes.
- Creating net-new factual knowledge without source agents.

## 3. Knowledge Domain

### Topics Owned

- Narrative templates
- Family-safe explanation patterns
- Trade-off framing

### Knowledge Boundaries

- Does not own facts; it owns explanation composition from prepared knowledge.

### Relationships With Other Agents

- Clinical Knowledge Agent
- Provider Intelligence Agent
- Clinical Evidence Agent
- Knowledge Graph Agent
- Matching Improvement Agent

### Knowledge Ownership Rules

- Primary owner of narrative packaging and family-safe rendering rules.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Prepared recommendation inputs | Structured facts for explanation generation | P0 | HIGH | Per request | Must already be verified prepared knowledge. |
| Prepared knowledge graph paths | Explainable linkage across facts | P0 | HIGH | Per request | Only canonical graph paths may be used. |
| Prepared evidence links | Confidence-aware evidence references | P1 | HIGH | Per request | Evidence must already be approved. |

## 5. Discovery Strategy

- Discover weak explanation patterns from validation and family feedback.
- Detect missing explanation coverage where recommendations lack clear verified strengths or trade-offs.
- Prioritize high-impact narrative improvements without altering underlying facts.

## 6. Validation Strategy

### Evidence Requirements

- Every narrative claim must map to at least one prepared fact or evidence link.

### Verification Rules

- Narratives must label missing or unverified capabilities clearly.

### Conflict Resolution

- Narrative phrasing follows the most recent prepared fact state and trust envelope.

### Duplicate Detection

- Normalize explanation patterns and reuse validated templates.

### Confidence Calculation

- Narrative confidence is inherited from prepared fact confidence and freshness.

### Freshness Policy

- Narrative snapshots refresh with their underlying prepared knowledge inputs.

## 7. Knowledge Processing

### Normalization

- Normalize explanation fragments to family-safe vocabulary.

### Classification

- Classify explanation content as strengths, trade-offs, missing capabilities, and next steps.

### Deduplication

- Reuse validated explanation templates to avoid inconsistent phrasing.

### Merging

- Merge new explanation improvements into approved narrative template library.

### Knowledge Object Creation

- Narrative template objects
- Explanation policy objects

### Evidence Object Creation

- Narrative evidence-link references

### Knowledge Graph Updates

- Create recommendation-to-explanation and explanation-to-evidence relationships.

## 8. Outputs

- Warnings
- Confidence
- Freshness
- Verification Status
- Knowledge Objects

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

- Daily explanation quality review

### Discovery Jobs

- Narrative gap detection

### Refresh Jobs

- Narrative template refresh

### Verification Jobs

- Traceability checks

### Learning Jobs

- Explanation quality improvement cycles

### Cleanup Jobs

- Retire confusing or leaking templates

### Retry Jobs

- Retry failed narrative generation validations

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Accuracy | Measurable |
| Response time | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Learning progress | Measurable |
| Discovery success | Measurable |
| Refresh success | Measurable |
| Family-safe compliance rate | Measurable |
| Traceability completeness | Measurable |
| Duplicate rate | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 4 |
| evidencePerDay | >= 4 narrative references |
| providerUpdatesPerDay | N/A |
| relationshipsPerDay | >= 4 |
| coverageGrowthPerDay | >= 1 explanation pattern |

## 13. Failure Handling

- Fall back to simpler verified summaries, log traceability failures, and notify supervisor when narratives cannot be grounded.

## 14. Supervisor Interaction

- Narrative health reports
- Gap reports
- Leakage alerts
- Explanation quality recommendations

## 15. Recommendation Engine Contract

- Consumes only structured prepared knowledge and returns family-safe structured explanation fields.

## 16. Security

- No live data access; no disclosure of internal scoring internals.

## 17. Success Criteria

- Every recommendation has a grounded explanation.
- No internal logic leaks.
- Family-safe explanation quality improves over time.
