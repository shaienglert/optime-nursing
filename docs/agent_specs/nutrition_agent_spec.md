# Nutrition Intelligence Agent Specification

## 1. Agent Identity

- Agent Name: Nutrition Intelligence Agent
- Purpose: Own nutrition, dining, and dietary support knowledge for provider fit.
- Mission Statement: Continuously discover and verify dietary support capabilities so nutrition and allergy needs are represented in prepared knowledge.
- Domain: Dietary and nutrition support
- Owner: OPTIME Nutrition Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Menus
- Diet programs
- Diabetic support
- Kosher
- Vegetarian
- Allergy support
- Texture-modified diets

### Must Never Do

- Infer specialized dietary support without evidence.
- Overstate allergy accommodations.

### Decisions It Can Make

- Create or update diet-support knowledge objects.
- Flag unresolved dietary gaps for review.

### Outside Its Authority

- Changing provider licensing or social-program facts.

## 3. Knowledge Domain

### Topics Owned

- Diet capabilities
- Menu support
- Dining accommodations
- Nutrition programs

### Knowledge Boundaries

- Does not own clinical disease guidance.
- Coordinates with Clinical Knowledge on medical diet needs.

### Relationships With Other Agents

- Clinical Knowledge Agent
- Provider Intelligence Agent
- Knowledge Graph Agent

### Knowledge Ownership Rules

- Primary owner of dietary support and menu accommodation knowledge.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| Provider menus and dining pages | Current dietary offerings and menu patterns | P0 | MEDIUM | Daily | Must be provider-attributed and current. |
| Provider verification memory | Directly verified dietary accommodations | P0 | HIGH | Daily | Requires verified provider identity and timestamp. |
| Clinical guidance | Medical diet requirements and terminology normalization | P1 | HIGH | Daily | Used for classification, not provider proof. |

## 5. Discovery Strategy

- Discover menus, dining program updates, and special-diet support changes.
- Prioritize providers with high diet-related demand or low coverage.
- Generate gaps for missing diabetic, allergy, kosher, and texture-modified support.

## 6. Validation Strategy

### Evidence Requirements

- Provider-attributed source required for provider-specific diet claims.
- Clinical guidance required for medical-diet terminology mapping.

### Verification Rules

- Special diet claims require provider evidence or direct verification.

### Conflict Resolution

- Direct verification outranks stale website content.

### Duplicate Detection

- Normalize by provider, diet type, and accommodation capability.

### Confidence Calculation

- Confidence is based on direct verification, official source recency, and corroboration.

### Freshness Policy

- Default TTL 24 hours; shorter for menus during active update windows.

## 7. Knowledge Processing

### Normalization

- Normalize diet labels and accommodation terminology.

### Classification

- Classify by medical diets, religious diets, allergy support, texture modification, and nutrition programs.

### Deduplication

- Deduplicate menu and capability claims by provider and diet type.

### Merging

- Merge current verified diet support into canonical provider nutrition objects.

### Knowledge Object Creation

- Nutrition support objects
- Diet compatibility objects

### Evidence Object Creation

- Menu evidence objects
- Diet verification evidence objects

### Knowledge Graph Updates

- Create provider-to-diet and condition-to-diet relationships.

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

- Daily nutrition discovery run

### Discovery Jobs

- Menu discovery
- Diet support change detection

### Refresh Jobs

- Prepared nutrition snapshot refresh

### Verification Jobs

- Diet-support verification jobs

### Learning Jobs

- Outcome-linked nutrition fit review

### Cleanup Jobs

- Retire stale or contradicted menu claims

### Retry Jobs

- Retry failed dining-source fetches

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Knowledge growth | Measurable |
| Evidence growth | Measurable |
| Coverage | Measurable |
| Confidence | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Learning progress | Measurable |
| Accuracy | Measurable |
| Duplicate rate | Measurable |
| Response time | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 8 |
| evidencePerDay | >= 8 |
| providerUpdatesPerDay | >= 10 |
| relationshipsPerDay | >= 6 |
| coverageGrowthPerDay | >= 1 diet-support segment |

## 13. Failure Handling

- Retry failed menu fetches, downgrade stale support claims, notify supervisor on unresolved contradictions.

## 14. Supervisor Interaction

- Growth reports
- Gap reports
- Diet-support incident alerts

## 15. Recommendation Engine Contract

- Expose only prepared nutrition support objects with confidence, freshness, and verification status.

## 16. Security

- Write nutrition and evidence objects only; no direct changes to unrelated provider fields.

## 17. Success Criteria

- Nutrition support knowledge expands daily.
- Diet-support claims remain traceable and fresh.
- Critical dietary gaps are surfaced before recommendation use.
