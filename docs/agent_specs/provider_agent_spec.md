# Provider Intelligence Agent Specification

## 1. Agent Identity

- Agent Name: Provider Intelligence Agent
- Purpose: Continuously expand and verify the provider repository.
- Mission Statement: Discover, verify, deduplicate, and enrich provider profiles so recommendations rely on prepared provider intelligence instead of live research.
- Domain: Provider verified capabilities
- Owner: OPTIME Provider Intelligence
- Version: v1.0
- Status: Specified

## 2. Responsibilities

### Responsible For

- Provider discovery
- Provider enrichment
- Provider verification
- Duplicate provider detection
- Prepared provider profile publication

### Must Never Do

- Invent provider services or amenities.
- Hide verification uncertainty.
- Perform recommendation ranking policy changes.

### Decisions It Can Make

- Create new provider objects.
- Merge duplicate providers.
- Update freshness, verification, and confidence states.

### Outside Its Authority

- Changing clinical interpretations.
- Overriding evidence quality scoring owned by Evidence Agent.

## 3. Knowledge Domain

### Topics Owned

- Identity
- Address
- Coordinates
- Ownership
- Care levels
- Programs
- Languages
- Amenities
- Pricing
- Capacity
- Verification status

### Knowledge Boundaries

- Does not own clinical best-practice guidance.
- Consumes activity, nutrition, and evidence enrichments from other agents.

### Relationships With Other Agents

- Activities Intelligence Agent
- Nutrition Intelligence Agent
- Data Quality & Trust Agent
- Knowledge Graph Agent

### Knowledge Ownership Rules

- Primary owner of provider identity and prepared provider profile objects.
- Secondary agents may enrich provider subdomains but not replace provider identity.

## 4. Input Sources

| Source | Purpose | Priority | Trust Level | Refresh Frequency | Validation Rules |
| --- | --- | --- | --- | --- | --- |
| CMS provider files | Core provider registry and ratings baseline | P0 | HIGH | Daily | Must match CMS ID and provider identity fields. |
| State inspection data | Operational status, sanctions, and inspection updates | P0 | HIGH | Daily | Must map to known provider identity or create review task. |
| Official provider websites | Programs, amenities, admissions, contact channels | P1 | MEDIUM | Daily | Identity and domain must match provider allowlist or verified ownership. |
| Public releases and facility updates | Service, ownership, and availability changes | P2 | MEDIUM | Daily | Requires cross-source consistency before high confidence. |

## 5. Discovery Strategy

- Continuously scan CMS and official provider sources for new providers and changes.
- Detect changes by address, ownership, phone, service, and ratings deltas.
- Prioritize counties and states with low coverage or high demand.
- Generate discovery tasks for missing care models and unexplored geographies.

## 6. Validation Strategy

### Evidence Requirements

- CMS or state source required for verified identity.
- At least one corroborating source for service changes.
- Official domain or portal response required for direct provider claims.

### Verification Rules

- Identity, address, CMS registration, and ownership must be normalized before publication.
- Duplicate candidates must be merged or sent to review.

### Conflict Resolution

- Higher-trust registry sources outrank lower-trust web claims.
- Unresolved service conflicts remain LIMITED or UNKNOWN.

### Duplicate Detection

- Match on CMS ID, normalized name, phone, coordinates, and address similarity.

### Confidence Calculation

- Confidence depends on source trust, verification count, consistency, and recency.

### Freshness Policy

- Default TTL 12 hours for provider snapshots; shorter TTL for high-volatility providers.

## 7. Knowledge Processing

### Normalization

- Normalize provider identity, address, phone, coordinates, ownership, and care taxonomy.

### Classification

- Classify providers by care model, services, payment options, and verification status.

### Deduplication

- Collapse duplicate provider identities into a single canonical profile.

### Merging

- Merge enriched attributes into prepared provider profiles with provenance.

### Knowledge Object Creation

- Provider objects
- Capability objects
- Verification memory objects

### Evidence Object Creation

- Provider evidence objects
- Inspection evidence objects
- Identity verification evidence objects

### Knowledge Graph Updates

- Create provider-to-capability and provider-to-location relationships.

## 8. Outputs

- Provider Objects
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

- Daily provider repository scan
- Hourly freshness queue review

### Discovery Jobs

- New provider discovery
- Service and pricing change detection

### Refresh Jobs

- Prepared provider snapshot refresh

### Verification Jobs

- Identity, duplicate, and service-consistency verification runs

### Learning Jobs

- Coverage expansion prioritization

### Cleanup Jobs

- Retire or deprecate inactive provider profiles

### Retry Jobs

- Retry source fetch and verification workflows

## 11. KPIs

| KPI | Measurable |
| --- | --- |
| Provider growth | Measurable |
| Coverage | Measurable |
| Duplicate rate | Measurable |
| Verification success | Measurable |
| Refresh success | Measurable |
| Discovery success | Measurable |
| Confidence | Measurable |
| Response time | Measurable |
| Learning progress | Measurable |
| Provider enrichment completeness | Measurable |

## 12. Daily Targets

| Target | Expectation |
| --- | --- |
| knowledgeObjectsPerDay | >= 12 |
| evidencePerDay | >= 12 |
| providerUpdatesPerDay | >= 20 |
| relationshipsPerDay | >= 10 |
| coverageGrowthPerDay | >= 1 county |

## 13. Failure Handling

- Retry failed discovery jobs.
- Escalate duplicate-provider conflicts.
- Keep last verified provider snapshot live until replacement is ready.
- Log all merges and verification failures.

## 14. Supervisor Interaction

- Provider growth reports
- Coverage reports
- Duplicate-provider alerts
- Verification incidents
- Expansion recommendations

## 15. Recommendation Engine Contract

- Expose only prepared provider profiles, capability status, confidence, freshness, and verification fields.
- No live fetches during recommendation execution.

## 16. Security

- May write provider profile and verification memory objects; may not expose private data or bypass allowlists.

## 17. Success Criteria

- Provider repository grows continuously.
- Duplicate rates stay below target.
- Prepared provider profiles remain recommendation-ready.
