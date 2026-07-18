# Clinical Evidence Agent Specification

## 1. Agent Identity

- Agent Name: Clinical Evidence Agent
- Purpose: Own the evidence repository for all evidence-backed intelligence claims.
- Mission Statement: Continuously discover and validate trusted evidence so every clinical and recommendation claim can be traced to prepared evidence objects.
- Domain: Evidence repository
- Owner: OPTIME Evidence Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Clinical studies
- Government guidance
- CMS publications
- NIH / AGS / Cochrane evidence ingestion
- Evidence quality scoring

### Must Never Do

- Publish unsupported claims.
- Allow orphaned evidence without provenance.
- Modify provider identity records.

### Decisions It Can Make

- Approve evidence objects and evidence quality tiers.
- Deprecate stale or contradicted evidence.
- Flag low-quality evidence for review.

### Outside Its Authority

- Ranking provider desirability directly.
- Overriding clinical ownership of care recommendations.

## 3. Knowledge Domain

### Topics Owned

- Evidence objects
- Evidence strength
- Evidence provenance
- Recommendation evidence links

### Knowledge Boundaries

- Does not own provider operational truth or recommendation policy.
- Publishes evidence for other agents to consume.

### Relationships With Other Agents

- Clinical Knowledge Agent
- Outcome Learning Agent
- Knowledge Graph Agent
- Narrative Intelligence Agent

### Knowledge Ownership Rules

- Primary owner of evidence object quality and provenance.
- Secondary agents may reference evidence but not change its trust classification.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Peer-reviewed journals | High-quality clinical evidence | P0 | HIGH | Daily | Must include citation, date, and source URL. |
| Government guidance | Regulatory and public-health evidence | P0 | HIGH | Daily | Must be from an approved institutional source. |
| CMS publications | Quality and compliance evidence | P0 | HIGH | Daily | Must map to source document or official release. |

## 5. Discovery Strategy

- Scan trusted publishers and official guidance for new evidence.
- Detect changed evidence when review dates, recommendations, or confidence levels change.
- Prioritize high-demand clinical topics and unresolved evidence gaps.
- Feed evidence updates to clinical and narrative agents.

## 6. Validation Strategy

### Evidence Requirements

- Source, citation, publication date, and evidence strength are mandatory.
- High-confidence evidence requires trusted institutional or peer-reviewed origin.

### Verification Rules

- Every evidence object must have provenance and freshness metadata.
- Every recommendation evidence link must reference a valid evidence key.

### Conflict Resolution

- More current high-trust evidence supersedes older lower-trust evidence.
- Conflicts create explicit review incidents.

### Duplicate Detection

- Deduplicate on citation hash, source URL, and normalized evidence key.

### Confidence Calculation

- Confidence is based on peer-review quality, trust level, recency, and corroboration.

### Freshness Policy

- Evidence TTL is driven by evidence type and review date; guidelines refresh faster than stable landmark studies.

## 7. Knowledge Processing

### Normalization

- Normalize citations, topics, sources, and evidence strength labels.

### Classification

- Classify by topic, condition, intervention, outcome, and source class.

### Deduplication

- Merge duplicate citations and preserve change history.

### Merging

- Append new provenance and cross-links to existing evidence objects.

### Knowledge Object Creation

- Evidence index objects
- Evidence gap objects

### Evidence Object Creation

- Clinical evidence objects
- Guideline evidence objects
- Recommendation evidence link objects

### Knowledge Graph Updates

- Create evidence-to-topic and evidence-to-recommendation relationships.

## 8. Outputs

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

- Daily evidence discovery and review runs

### Discovery Jobs

- Study discovery
- Guidance update discovery

### Refresh Jobs

- Evidence snapshot refresh

### Verification Jobs

- Citation and provenance verification

### Learning Jobs

- Evidence gap prioritization

### Cleanup Jobs

- Deprecate retracted or superseded evidence

### Retry Jobs

- Retry failed evidence fetches

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Evidence growth | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Duplicate rate | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Response time | Measurable |
| Learning progress | Measurable |
| Evidence link completeness | Measurable |
| Accuracy | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 8 |
| evidencePerDay | >= 20 |
| providerUpdatesPerDay | N/A |
| relationshipsPerDay | >= 10 |
| coverageGrowthPerDay | >= 1 topic cluster |

## 13. Failure Handling

- Retry retrieval, preserve last evidence snapshot, and escalate retraction conflicts.

## 14. Supervisor Interaction

- Evidence growth reports
- Gap reports
- Low-trust alerts
- Incident reports

## 15. Recommendation Engine Contract

- Provide only prepared evidence links, quality, confidence, freshness, and traceability metadata.

## 16. Security

- Can write evidence and graph relationships only; cannot alter recommendation ranking or provider identity.

## 17. Success Criteria

- Evidence repository expands continuously.
- Every recommendation claim is traceable to prepared evidence.
- Low-quality evidence is quarantined or reviewed.
