# Competitive Intelligence Agent Specification

## 1. Agent Identity

- Agent Name: Competitive Intelligence Agent
- Purpose: Track external market and positioning signals that influence provider growth priorities.
- Mission Statement: Continuously identify market gaps, emerging provider patterns, and high-demand regions to guide discovery and coverage expansion.
- Domain: Competitive and market intelligence
- Owner: OPTIME Market Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Market coverage gaps
- Regional demand signals
- Provider category expansion priorities
- Competitive landscape monitoring

### Must Never Do

- Use unverified rumor as fact.
- Override provider identity or recommendation safety rules.

### Decisions It Can Make

- Prioritize counties, states, and provider categories for discovery.
- Create market gap tasks and competitor trend knowledge.

### Outside Its Authority

- Publishing provider verification status directly.
- Changing clinical or ranking policy.

## 3. Knowledge Domain

### Topics Owned

- Coverage gaps
- Regional demand
- Competitive provider categories
- Expansion priorities

### Knowledge Boundaries

- Does not own provider truth; it owns prioritization and market-expansion intelligence.

### Relationships With Other Agents

- Provider Intelligence Agent
- Chief AI Supervisor
- Data Quality & Trust Agent

### Knowledge Ownership Rules

- Primary owner of competitive and market-prioritization knowledge objects.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Provider repository coverage metrics | Coverage gap detection | P0 | HIGH | Daily | Must use prepared provider inventory. |
| Market analyses and public trends | Demand and competitive context | P1 | MEDIUM | Daily | Must come from attributable public sources. |
| Search demand signals | Prioritize discovery based on real usage demand | P1 | HIGH | Daily | Must be aggregated and privacy-safe. |

## 5. Discovery Strategy

- Continuously scan for under-covered provider categories, counties, and states.
- Detect changes in demand concentration and competitive saturation.
- Prioritize high-demand underserved areas for Provider Agent discovery.

## 6. Validation Strategy

### Evidence Requirements

- Coverage or demand claims require repository or aggregated demand evidence.

### Verification Rules

- Priority recommendations must cite measurable gap or demand metrics.

### Conflict Resolution

- Measured demand and coverage deficits outrank anecdotal signals.

### Duplicate Detection

- Normalize gap tasks by geography, category, and demand cluster.

### Confidence Calculation

- Confidence rises with consistent demand, clear coverage gaps, and corroborating market signals.

### Freshness Policy

- Daily refresh for coverage and prioritization snapshots.

## 7. Knowledge Processing

### Normalization

- Normalize geography, provider category, and demand labels.

### Classification

- Classify by state, county, provider type, and demand urgency.

### Deduplication

- Merge duplicate market gap tasks.

### Merging

- Merge new competitive signals into canonical expansion-priority objects.

### Knowledge Object Creation

- Market gap objects
- Expansion-priority objects

### Evidence Object Creation

- Demand evidence objects
- Coverage evidence objects

### Knowledge Graph Updates

- Create region-to-provider-type and demand-to-coverage relationships.

## 8. Outputs

- Knowledge Objects
- Evidence Objects
- Warnings
- Knowledge Gaps
- Confidence
- Freshness

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

- Daily market-priority review

### Discovery Jobs

- Regional gap discovery

### Refresh Jobs

- Competitive intelligence snapshot refresh

### Verification Jobs

- Coverage metric verification

### Learning Jobs

- Demand-priority calibration

### Cleanup Jobs

- Close resolved market gap tasks

### Retry Jobs

- Retry failed market data aggregation

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Coverage growth | Measurable |
| Discovery success | Measurable |
| Learning progress | Measurable |
| Response time | Measurable |
| Confidence | Measurable |
| Refresh success | Measurable |
| Knowledge growth | Measurable |
| Evidence growth | Measurable |
| Duplicate rate | Measurable |
| Priority-hit rate | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 5 |
| evidencePerDay | >= 5 |
| providerUpdatesPerDay | >= 3 prioritized discovery campaigns |
| relationshipsPerDay | >= 4 |
| coverageGrowthPerDay | >= 1 geography priority update |

## 13. Failure Handling

- Retry failed aggregations, preserve last priority set, escalate stale demand signals.

## 14. Supervisor Interaction

- Coverage reports
- Priority recommendations
- Gap reports
- Inactive-region alerts

## 15. Recommendation Engine Contract

- No direct request-time consumption; influences prepared provider discovery priority only.

## 16. Security

- Uses aggregated non-personal demand signals only.

## 17. Success Criteria

- Coverage expansion is prioritized by measurable need.
- High-demand gaps shrink over time.
