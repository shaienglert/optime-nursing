# OPTIME Gap Analysis

## Method

Each subsystem is evaluated for missing capabilities, weak assumptions, duplicate logic, missing tables/APIs/UI/validation, and risk dimensions.

## Part 2: Subsystem Gap Matrix

| Subsystem | Missing Capabilities | Weak Assumptions | Duplicate Logic | Missing Tables/APIs/UI/Validation |
| --- | --- | --- | --- | --- |
| Matching Engine | Central policy registry for weights and penalties | Client runtime equals source of truth | Score computation mirrored in multiple scripts | Missing backend match-explain API and deterministic replay endpoint |
| Questionnaire | Progressive save/recovery and household collaboration | Single-user linear completion assumption | Question transforms in context + engine helpers | Missing formal questionnaire sessions table and API |
| Clinical Reasoning | Contraindication rule engine and specialty fallback paths | Generic narrative suffices for all acuity levels | Clinical phrasing duplicated in scripts | Missing clinical assertion lint validation in CI |
| Narrative Engine | Versioned narrative templates with A/B governance | One narrative style fits all family personas | Narrative snippets in UI and scripts | Missing narrative CMS and review workflow UI |
| Facility Memory Engine | Memory conflict resolution workflow UI | Latest response always best | Expiry and confidence logic in script + service paths | Missing memory event history read API |
| Provider Portal | Production-grade dashboard, analytics, and lead funnel | API-first is enough for provider adoption | Provider update semantics across identity and capability services | Missing complete frontend provider portal surfaces |
| Verification Engine | SLA tracking, escalation routing, reminder automation | Provider response latency is manageable | Verification states interpreted in several layers | Missing queue-backed verification task table |
| OSINT | Source health monitoring and legal-safe takedown handling | Public signal stability | Signal weighting and provenance in several scripts | Missing OSINT ingestion run table and governance API |
| Knowledge Graph | Runtime graph service and query endpoints beyond docs | Graph edges in table imply graph completeness | Graph relationship concepts repeated in docs/scripts | Missing entity normalization and edge lineage API |
| Evidence Engine | Runtime enforcement of evidence links per narrative statement | Script validation is sufficient for prod | Evidence maps duplicated in script constants | Missing persisted recommendation-evidence linkage writes |
| Reports | Unified taxonomy and machine-readable index | Markdown alone is operationally sufficient | Similar metric logic across many scripts | Missing report metadata registry table |
| Provider Inbox | Full inbox UI, triage statuses, and assignment | Request records imply usable inbox | Verification and inbox status are split | Missing inbox APIs for list/filter/acknowledge |
| Simulation Framework | Scenario catalog governance and seed control | Ad-hoc scripts are maintainable long term | Helper logic reused but fragmented | Missing simulation run ledger table |
| Audit Framework | End-to-end immutable event trail from UI to outcome | Report pass means runtime safe | Audit calculations repeated per script | Missing centralized audit policy service |

## Risk View By Domain

### Performance and Scalability Risks

- Frontend-heavy ranking execution increases payload and consistency risk as dataset grows.
- Report scripts repeatedly load full facility sets, creating batch inefficiency.
- JSON text blobs in intelligence profile fields limit query performance and indexing at scale.

### Security Risks

- OTP debug paths and simulation-heavy flows need strict environment gating.
- Provider APIs need stronger throttling and abuse controls.
- Broader SOC2-style controls and secret management lifecycle are not evident in current structure.

### Clinical Risks

- Clinical evidence linkage is validated in scripts but not yet enforced at runtime for every delivered narrative.
- Lack of centralized contraindication service can lead to edge-case overstatements.

### Business Risks

- Provider value proposition may stall without robust dashboard and lead management UX.
- Family conversion optimization is limited without integrated contact-throughcome operational tooling.

### Legal/Privacy Risks

- OSINT usage governance needs stronger retention, deletion, and consent boundaries.
- Outcome analytics must maintain strict de-identification with policy-level audits.

## Top 25 Priority Improvements

1. Move final ranking computation to a versioned backend scoring service.
2. Add match replay API with deterministic seed and policy version.
3. Introduce scoring policy registry table for weights, thresholds, penalties.
4. Persist recommendation-evidence links for every delivered statement.
5. Add clinical assertion linting in CI for unsupported/overstated language.
6. Implement contraindication and risk-guard rule engine.
7. Build provider inbox APIs: list, triage, SLA, acknowledge, resolve.
8. Build provider dashboard UI for verification, completeness, and leads.
9. Add verification queue and reminder scheduler.
10. Add questionnaire session persistence API and resume UX.
11. Introduce entity-normalized knowledge graph service endpoints.
12. Add graph lineage query endpoint for explanation provenance.
13. Create OSINT run ledger with source health and legal flags.
14. Add report metadata registry for discoverability and governance.
15. Add simulation run registry with dataset/version fingerprint.
16. Consolidate duplicated confidence/expiry logic into shared backend module.
17. Add ingestion freshness and staleness alerts by source.
18. Add role-based API rate limiting and anomaly detection.
19. Enforce environment-based disabling of debug verification outputs.
20. Implement PII scanning and data retention policy automation for reports.
21. Add multi-tenant readiness boundaries for enterprise provider groups.
22. Add CRM integration layer for provider lead export and follow-up.
23. Add revenue-grade subscription entitlements in provider APIs.
24. Add outcome closed-loop deployment gate (weekly calibration approvals).
25. Add executive KPI dashboard unifying family, provider, and outcome funnels.
