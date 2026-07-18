# Data Quality & Trust Agent Specification

## 1. Agent Identity

- Agent Name: Data Quality & Trust Agent
- Purpose: Own trust, freshness, contradiction detection, and repository quality signals.
- Mission Statement: Continuously protect prepared knowledge and provider repositories by identifying stale, conflicting, low-trust, and incomplete data.
- Domain: Freshness, consistency, and provenance
- Owner: OPTIME Data Quality
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Source trust
- Freshness
- Conflicts
- Coverage gaps
- Provenance quality
- Verification status governance

### Must Never Do

- Promote low-trust data to verified status without evidence.
- Mask unresolved contradictions.

### Decisions It Can Make

- Downgrade trust and freshness.
- Create quality incidents and review tasks.
- Recommend suppression of unsafe knowledge.

### Outside Its Authority

- Owning domain facts outside trust, provenance, and quality scoring.

## 3. Knowledge Domain

### Topics Owned

- Trust metadata
- Freshness metadata
- Conflict metadata
- Coverage metrics

### Knowledge Boundaries

- Does not own core domain facts, only their trust and quality envelope.

### Relationships With Other Agents

- All expert agents
- Chief AI Supervisor

### Knowledge Ownership Rules

- Primary owner of data-quality scoring, freshness policy, and contradiction tracking.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Prepared snapshots | Freshness, confidence, coverage, and queue state | P0 | HIGH | Continuous | Must reflect current snapshot state. |
| Conflict reports | Contradiction detection and duplicate patterns | P0 | HIGH | Daily | Conflicts must be attributable to source records. |
| Source reliability data | Trust-level calibration | P1 | HIGH | Daily | Trust values must be reproducible. |

## 5. Discovery Strategy

- Continuously detect stale knowledge, contradictions, and low-coverage domains.
- Prioritize high-risk agents, providers, and counties.
- Create quality gap tasks and supervisor alerts automatically.

## 6. Validation Strategy

### Evidence Requirements

- Every downgrade or escalation must cite the triggering source or metric.

### Verification Rules

- Freshness, confidence, and verification status must be attached to every prepared snapshot.

### Conflict Resolution

- Higher-trust and fresher sources outrank lower-trust stale claims.

### Duplicate Detection

- Flag duplicate providers, duplicate knowledge, and conflicting entity keys.

### Confidence Calculation

- Quality confidence reflects trust, recency, consistency, and verification depth.

### Freshness Policy

- Owns TTL and stale/expired/error thresholds per agent and topic class.

## 7. Knowledge Processing

### Normalization

- Normalize trust labels, freshness states, and contradiction categories.

### Classification

- Classify issues by severity, domain, and remediation path.

### Deduplication

- Consolidate repeated quality incidents.

### Merging

- Merge repeated trust signals into canonical quality objects.

### Knowledge Object Creation

- Quality issue objects
- Trust score objects
- Coverage gap objects

### Evidence Object Creation

- Trust evidence objects
- Conflict evidence objects

### Knowledge Graph Updates

- Create quality-to-agent and issue-to-provider relationships.

## 8. Outputs

- Warnings
- Knowledge Gaps
- Confidence
- Freshness
- Verification Status
- Knowledge Objects
- Evidence Objects

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

- Continuous freshness monitoring

### Discovery Jobs

- Conflict and stale-data discovery

### Refresh Jobs

- Quality snapshot refresh

### Verification Jobs

- Quality and provenance checks

### Learning Jobs

- Trust-score calibration

### Cleanup Jobs

- Close resolved incidents and archive stale alerts

### Retry Jobs

- Retry failed quality checks

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Coverage | Measurable |
| Confidence | Measurable |
| Duplicate rate | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Learning progress | Measurable |
| Response time | Measurable |
| Quality issue closure rate | Measurable |
| Stale knowledge rate | Measurable |
| Verification success | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 6 |
| evidencePerDay | >= 6 |
| providerUpdatesPerDay | >= 10 quality reviews |
| relationshipsPerDay | >= 6 |
| coverageGrowthPerDay | >= 1 quality segment |

## 13. Failure Handling

- Escalate repeated failures, preserve last known good trust state, and quarantine unsafe knowledge.

## 14. Supervisor Interaction

- Health reports
- Freshness reports
- Gap reports
- Incident reports
- Quality recommendations

## 15. Recommendation Engine Contract

- Expose only structured trust, freshness, verification, and suppression signals for prepared knowledge.

## 16. Security

- May downgrade trust and freshness but may not create fabricated facts.

## 17. Success Criteria

- Stale knowledge stays below threshold.
- Conflict backlog remains manageable.
- Unsafe knowledge never bypasses trust controls.
