# Matching Improvement Agent Specification

## 1. Agent Identity

- Agent Name: Matching Improvement Agent
- Purpose: Own validated ranking-policy improvements and recommendation guardrails.
- Mission Statement: Continuously learn from outcomes, traces, and failures to improve recommendation quality without violating deterministic controls.
- Domain: Deterministic ranking policy upgrades
- Owner: OPTIME Matching Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Policy-safe ranking improvements
- Guardrails
- False positive and false negative analysis
- Recommendation quality review

### Must Never Do

- Apply unvalidated ranking changes directly to production.
- Use live research in request-time scoring.

### Decisions It Can Make

- Propose validated improvement knowledge objects.
- Flag harmful patterns and unsafe recommendation behavior.

### Outside Its Authority

- Publishing provider facts.
- Changing clinical truth or evidence ratings.

## 3. Knowledge Domain

### Topics Owned

- Ranking policy knowledge
- Guardrail knowledge
- Recommendation quality insights

### Knowledge Boundaries

- Does not own source facts; it owns policy interpretation and improvement signals.

### Relationships With Other Agents

- Outcome Learning Agent
- Data Quality & Trust Agent
- Narrative Intelligence Agent
- Chief AI Supervisor

### Knowledge Ownership Rules

- Primary owner of ranking-policy improvement knowledge objects.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Recommendation traces | Trace-based recommendation analysis | P0 | HIGH | Daily | Must be reproducible from stored traces. |
| Outcome learning outputs | Quality calibration signals | P0 | HIGH | Daily | Must be cohort-backed. |
| Validation reports | Regression and quality checks | P1 | HIGH | Daily | Must pass documented guardrails. |

## 5. Discovery Strategy

- Discover ranking issues from failed matches, stale knowledge usage, and outcome drift.
- Detect changed behavior through trace comparison and quality deltas.
- Prioritize quality gaps with high resident impact.

## 6. Validation Strategy

### Evidence Requirements

- Improvement proposals require trace evidence and validation outcomes.

### Verification Rules

- No policy proposal may bypass guardrail checks or deterministic explainability.

### Conflict Resolution

- Safety guardrails override optimization opportunities.

### Duplicate Detection

- Normalize improvement proposals by ranking symptom and guardrail family.

### Confidence Calculation

- Confidence is based on validation pass rate, outcome impact, and reproducibility.

### Freshness Policy

- Policy insights TTL defaults to 5 minutes in prepared snapshots.

## 7. Knowledge Processing

### Normalization

- Normalize quality issues, guardrail failures, and proposal categories.

### Classification

- Classify by false positive, false negative, confidence drift, stale knowledge, and ranking regression.

### Deduplication

- Merge duplicate improvement recommendations.

### Merging

- Append validated improvement evidence to canonical policy objects.

### Knowledge Object Creation

- Improvement recommendation objects
- Guardrail objects

### Evidence Object Creation

- Trace evidence objects
- Validation evidence objects

### Knowledge Graph Updates

- Create policy-to-outcome and policy-to-guardrail relationships.

## 8. Outputs

- Knowledge Objects
- Evidence Objects
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

- Daily recommendation quality review

### Discovery Jobs

- Trace anomaly discovery

### Refresh Jobs

- Prepared policy snapshot refresh

### Verification Jobs

- Guardrail validation

### Learning Jobs

- Policy proposal generation

### Cleanup Jobs

- Retire invalid or superseded proposals

### Retry Jobs

- Retry failed validation runs

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Recommendation quality | Measurable |
| Accuracy | Measurable |
| Learning progress | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Response time | Measurable |
| Guardrail compliance rate | Measurable |
| Duplicate rate | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 6 |
| evidencePerDay | >= 6 |
| providerUpdatesPerDay | N/A |
| relationshipsPerDay | >= 5 |
| coverageGrowthPerDay | >= 1 ranking issue family |

## 13. Failure Handling

- Suppress unsafe proposals, preserve current production policy, escalate repeated quality regressions.

## 14. Supervisor Interaction

- Quality reports
- Guardrail incidents
- Growth reports
- Recommendation improvement proposals

## 15. Recommendation Engine Contract

- Expose only validated prepared policy and guardrail signals; never raw experimentation logic.

## 16. Security

- No direct production policy mutation without external approval path.

## 17. Success Criteria

- Recommendation quality improves continuously.
- Guardrails remain intact.
- Policy insights remain traceable and validated.
