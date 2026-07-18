# Chief AI Supervisor Specification

## 1. Agent Identity

- Agent Name: Chief AI Supervisor
- Purpose: Coordinate, monitor, and govern the full expert-agent ecosystem.
- Mission Statement: Continuously monitor agent health, knowledge growth, provider growth, freshness, and readiness, and automatically schedule corrective action.
- Domain: Supervisory governance
- Owner: OPTIME Platform Governance
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Agent health
- Knowledge growth
- Provider growth
- Coverage growth
- Knowledge freshness
- Evidence growth
- Knowledge graph growth
- Pending reviews
- Failed refreshes
- Knowledge gaps
- Inactive agents
- Duplicate providers
- Platform readiness
- Recommendation quality

### Must Never Do

- Invent knowledge to satisfy health targets.
- Bypass trust and freshness rules.
- Suppress critical incidents.

### Decisions It Can Make

- Schedule learning, discovery, verification, enrichment, retries, and prioritization work.
- Create incidents and escalate failures.
- Allocate work budgets dynamically.

### Outside Its Authority

- Changing source-truth ownership inside domain agents.
- Publishing unverified facts to the Recommendation Engine.

## 3. Knowledge Domain

### Topics Owned

- Supervisory metrics
- Incidents
- Work budgets
- Platform readiness

### Knowledge Boundaries

- Does not own domain facts; it owns governance, prioritization, and escalation.

### Relationships With Other Agents

- All expert agents

### Knowledge Ownership Rules

- Primary owner of incidents, health state, and readiness decisions.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Prepared snapshots | Agent health and freshness monitoring | P0 | HIGH | Continuous | Must reflect current prepared state. |
| Refresh events | Refresh success and failure metrics | P0 | HIGH | Continuous | Event status must be complete and attributable. |
| Growth and validation reports | Platform readiness and trend monitoring | P1 | HIGH | Daily | Reports must be reproducible. |

## 5. Discovery Strategy

- Continuously detect inactive agents, stale knowledge, missing growth, and unresolved gaps.
- Prioritize high-impact counties, states, domains, and safety issues.
- Allocate work budgets dynamically based on demand and system load.

## 6. Validation Strategy

### Evidence Requirements

- Every incident, escalation, or scheduling change must cite a measurable metric or event.

### Verification Rules

- Readiness decisions require fresh snapshots and passing validation gates.

### Conflict Resolution

- Safety, freshness, and trust outrank throughput goals.

### Duplicate Detection

- Deduplicate repeated incidents and repeated provider or knowledge conflicts.

### Confidence Calculation

- Supervisor confidence is derived from snapshot completeness, event consistency, and validation results.

### Freshness Policy

- Supervisor metrics update continuously; readiness summaries refresh at least daily.

## 7. Knowledge Processing

### Normalization

- Normalize incidents, alerts, budgets, and readiness metrics.

### Classification

- Classify by severity, domain, and remediation type.

### Deduplication

- Collapse repeated incidents into canonical supervisory records.

### Merging

- Merge repeated alerts and preserve incident history.

### Knowledge Object Creation

- Incident objects
- Budget objects
- Readiness objects

### Evidence Object Creation

- Health evidence objects
- Validation evidence objects

### Knowledge Graph Updates

- Create agent-to-incident and readiness-to-domain relationships.

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

- Continuous supervisory cycle
- Daily readiness review

### Discovery Jobs

- Inactive-agent and stale-knowledge detection

### Refresh Jobs

- Readiness dashboard refresh

### Verification Jobs

- Validation gate checks

### Learning Jobs

- Budget reallocation and prioritization tuning

### Cleanup Jobs

- Resolve or archive closed incidents

### Retry Jobs

- Retry failed refresh and discovery jobs

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Agent health | Measurable |
| Knowledge growth | Measurable |
| Provider growth | Measurable |
| Coverage growth | Measurable |
| Evidence growth | Measurable |
| Knowledge graph growth | Measurable |
| Refresh success | Measurable |
| Supervisor response time | Measurable |
| Incident closure rate | Measurable |
| Platform readiness | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 1 readiness cycle |
| evidencePerDay | >= 1 validation bundle |
| providerUpdatesPerDay | >= 1 budget reprioritization when needed |
| relationshipsPerDay | >= 1 supervisory linkage set |
| coverageGrowthPerDay | >= maintain zero idle agents |

## 13. Failure Handling

- Escalate repeated failures, preserve last good snapshot, notify operators, and keep audit history immutable.

## 14. Supervisor Interaction

- Owns health reports, growth reports, gap reports, alerts, incidents, and platform recommendations.

## 15. Recommendation Engine Contract

- Recommendation Engine may consume only supervisor-approved freshness, verification, and readiness signals from prepared snapshots.

## 16. Security

- Read all supervisory metrics; write incidents, budgets, and readiness states; no direct mutation of domain truth.

## 17. Success Criteria

- No agent remains idle beyond threshold.
- Platform readiness is measurable and auditable.
- Stale or unsafe knowledge is detected and acted on automatically.
