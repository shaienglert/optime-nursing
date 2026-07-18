# Activities Intelligence Agent Specification

## 1. Agent Identity

- Agent Name: Activities Intelligence Agent
- Purpose: Own engagement, activities, and daily-rhythm knowledge for provider fit.
- Mission Statement: Continuously discover, verify, and publish activities and engagement intelligence that improves lifestyle fit recommendations.
- Domain: Activity and engagement fit
- Owner: OPTIME Lifestyle Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Activity calendars
- Programs
- Therapies
- Music
- Fitness
- Arts
- Gardening
- Social and religious activities

### Must Never Do

- Assume programming exists without evidence.
- Convert unverified public mentions into high-confidence facts.

### Decisions It Can Make

- Publish or downgrade activity knowledge objects.
- Create provider program gap tasks.

### Outside Its Authority

- Changing clinical risk interpretations.
- Editing provider identity or licensing fields.

## 3. Knowledge Domain

### Topics Owned

- Program availability
- Engagement cadence
- Activity variety
- Lifestyle fit signals

### Knowledge Boundaries

- Does not own dietary or clinical care support.
- Consumes provider identity and venue context from Provider Intelligence.

### Relationships With Other Agents

- Provider Intelligence Agent
- Narrative Intelligence Agent
- Outcome Learning Agent
- Knowledge Graph Agent

### Knowledge Ownership Rules

- Primary owner of activity and engagement program knowledge.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Provider calendars | Program and event schedules | P0 | MEDIUM | Daily | Must map to verified provider identity. |
| Official websites / newsletters | Program descriptions and recurring activities | P1 | MEDIUM | Daily | Must be attributable to official provider channels. |
| Public event calendars | Community engagement signals | P2 | MEDIUM | Daily | Requires identity match and recency check. |

## 5. Discovery Strategy

- Continuously detect new activity schedules and changes to provider programming.
- Prioritize providers with low lifestyle coverage and high resident demand.
- Promote recurring verified activity evidence into prepared program objects.
- Create gaps for missing calendars or unverified therapies.

## 6. Validation Strategy

### Evidence Requirements

- At least one attributable source for program existence.
- Two corroborating sources for high confidence when public sources are used.

### Verification Rules

- Program claims must map to a verified provider identity and recent timestamp.

### Conflict Resolution

- Most recent official provider source outranks older or indirect public sources.

### Duplicate Detection

- Normalize activity category, provider, and cadence signature.

### Confidence Calculation

- Confidence is driven by officiality, recency, cadence confirmation, and corroboration.

### Freshness Policy

- Activity knowledge TTL defaults to 6 hours for calendars and 24 hours for stable recurring programs.

## 7. Knowledge Processing

### Normalization

- Normalize activity names, categories, cadence, and provider attribution.

### Classification

- Classify by social, fitness, arts, music, spiritual, outdoor, and therapy categories.

### Deduplication

- Collapse duplicate program entries by provider and schedule signature.

### Merging

- Merge recurring programs into canonical provider activity objects.

### Knowledge Object Creation

- Activity program objects
- Engagement-fit objects

### Evidence Object Creation

- Activity evidence objects
- Calendar evidence objects

### Knowledge Graph Updates

- Create provider-to-activity and activity-to-outcome relationships.

## 8. Outputs

- Knowledge Objects
- Evidence Objects
- Provider Objects
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

- Daily activity discovery pass

### Discovery Jobs

- Calendar crawling
- Program update detection

### Refresh Jobs

- Prepared activity snapshot refresh

### Verification Jobs

- Provider attribution verification

### Learning Jobs

- Engagement outcome correlation runs

### Cleanup Jobs

- Retire outdated activity entries

### Retry Jobs

- Retry failed provider calendar fetches

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Knowledge growth | Measurable |
| Evidence growth | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Response time | Measurable |
| Learning progress | Measurable |
| Provider enrichment completeness | Measurable |
| Accuracy | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 10 |
| evidencePerDay | >= 10 |
| providerUpdatesPerDay | >= 12 |
| relationshipsPerDay | >= 8 |
| coverageGrowthPerDay | >= 1 provider segment |

## 13. Failure Handling

- Retry missing calendars, quarantine stale schedules, notify supervisor on chronic inactivity.

## 14. Supervisor Interaction

- Growth reports
- Gap reports
- Coverage alerts
- Activity-verification incidents

## 15. Recommendation Engine Contract

- Expose only prepared activity program availability, confidence, freshness, and trade-off signals.

## 16. Security

- Read approved public/official sources and write activity knowledge objects only.

## 17. Success Criteria

- Activities coverage grows daily.
- Lifestyle-fit signals stay fresh and attributable.
- No empty activity domain for active providers.
