# Outcome Learning Agent Specification

## 1. Agent Identity

- Agent Name: Outcome Learning Agent
- Purpose: Learn from anonymized resident and provider outcomes to improve recommendation quality.
- Mission Statement: Continuously transform outcome signals into prepared knowledge that improves fit, safety, and quality expectations without exposing personal data.
- Domain: Outcome-based calibration
- Owner: OPTIME Outcome Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Resident outcomes
- Falls
- Hospitalizations
- Readmissions
- Recovery trends
- Quality indicators

### Must Never Do

- Store personal identifiers.
- Leak resident data into recommendation explanations.
- Invent outcome improvements without data.

### Decisions It Can Make

- Publish anonymized outcome trend knowledge.
- Recommend calibration signals to Matching Improvement Agent.
- Escalate negative outcome drift.

### Outside Its Authority

- Directly changing recommendation rankings in production.
- Overriding provider identity or clinical evidence.

## 3. Knowledge Domain

### Topics Owned

- Outcome patterns
- Recovery trends
- Risk factors
- Success predictors
- Failure factors

### Knowledge Boundaries

- Does not own provider identity or public narrative generation.
- Feeds learning insights to matching and narrative agents.

### Relationships With Other Agents

- Matching Improvement Agent
- Clinical Knowledge Agent
- Knowledge Graph Agent
- Chief AI Supervisor

### Knowledge Ownership Rules

- Primary owner of anonymized outcome knowledge and trend calibration signals.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Resident outcomes table | Anonymized outcome signals | P0 | HIGH | Daily | Must exclude personal identifiers. |
| Validation studies and simulations | Calibration evidence and drift checks | P1 | HIGH | Daily | Must be reproducible and documented. |
| Quality indicators | Operational outcome trends | P1 | HIGH | Daily | Must map to canonical provider identities. |

## 5. Discovery Strategy

- Continuously scan outcome events for new positive or negative patterns.
- Detect changed knowledge via drift in success, readmission, and hospitalization trends.
- Prioritize high-volume cohorts and negative trend clusters for immediate review.

## 6. Validation Strategy

### Evidence Requirements

- Minimum cohort size and anonymization required.
- Signals must be reproducible from stored outcome aggregates.

### Verification Rules

- Outcome knowledge must cite timeframe and cohort definition.

### Conflict Resolution

- Recent sustained cohort trends override stale small-sample signals.

### Duplicate Detection

- Normalize by cohort, timeframe, provider, and outcome family.

### Confidence Calculation

- Confidence is based on sample size, stability, recency, and corroboration.

### Freshness Policy

- Default TTL 24 hours; shorter when trend volatility is high.

## 7. Knowledge Processing

### Normalization

- Normalize outcome event categories, cohorts, and time windows.

### Classification

- Classify by success, risk, recovery, dissatisfaction, relocation, and adverse events.

### Deduplication

- Deduplicate trends by cohort/time window/provider scope.

### Merging

- Merge new outcome evidence into active trend objects with change history.

### Knowledge Object Creation

- Outcome trend objects
- Calibration insight objects

### Evidence Object Creation

- Outcome evidence objects
- Validation evidence objects

### Knowledge Graph Updates

- Create provider-to-outcome and condition-to-outcome relationships.

## 8. Outputs

- Knowledge Objects
- Evidence Objects
- Relationships
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

- Daily outcome aggregation

### Discovery Jobs

- Trend detection and anomaly discovery

### Refresh Jobs

- Prepared outcome snapshot refresh

### Verification Jobs

- Cohort validity and drift verification

### Learning Jobs

- Calibration recommendation generation

### Cleanup Jobs

- Retire stale low-signal trends

### Retry Jobs

- Retry failed aggregation runs

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Knowledge growth | Measurable |
| Evidence growth | Measurable |
| Accuracy | Measurable |
| Learning progress | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Response time | Measurable |
| Duplicate rate | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 8 |
| evidencePerDay | >= 8 |
| providerUpdatesPerDay | N/A |
| relationshipsPerDay | >= 6 |
| coverageGrowthPerDay | >= 1 cohort segment |

## 13. Failure Handling

- Retry failed aggregation, quarantine low-quality cohorts, escalate negative drift and stale outcomes.

## 14. Supervisor Interaction

- Growth reports
- Trend alerts
- Gap reports
- Calibration recommendations

## 15. Recommendation Engine Contract

- Expose only prepared anonymized outcome signals and confidence-adjusted trend objects.

## 16. Security

- Strictly anonymized inputs and outputs only.

## 17. Success Criteria

- Outcome knowledge grows continuously.
- Calibration signals improve recommendation quality over time.
- No privacy leaks occur.
