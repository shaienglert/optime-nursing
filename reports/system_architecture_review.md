# OPTIME System Architecture Review

## Executive Summary

This review evaluates the current OPTIME platform across product, architecture, clinical safety, and senior living operations readiness.

Overall position:

- Strong simulation culture and deterministic matching core.
- Strong momentum in verification, memory persistence, provider identity controls, and evidence framing.
- Primary gap is fragmentation: logic is spread across frontend runtime engine, report scripts, and backend APIs without a single orchestration and governance layer.
- Primary risk is production readiness at scale (security hardening, queueing, observability, API completeness, and enterprise workflow depth).

## Part 1: Current Architecture By Subsystem

| Subsystem | Current State | Strengths | Maturity |
| --- | --- | --- | --- |
| Matching Engine | Implemented mainly in frontend engine runtime | Deterministic tiering and tie-break behavior, rich audit outputs | Medium |
| Questionnaire | Implemented with context/provider + graph logic | Strong personalization and future-care preference support | Medium |
| Clinical Reasoning | Implemented in scoring audits and simulation narrative | Good explainability scaffolding and checklist output | Medium |
| Narrative Engine | Implemented in results UI and report generators | Family-first language improvements are present | Medium |
| Facility Memory Engine | Implemented in backend service + overlay in scripts | Recency, expiry, conflict handling exists | Medium-High |
| Provider Portal | Partially implemented via APIs and data models | Role controls, field audit and revert patterns exist | Medium |
| Verification Engine | Implemented (request/response/memory persistence) | Unknown handling and confidence workflow are explicit | Medium-High |
| OSINT | Implemented via scripts and profile enrichment | Trusted-source cap and source coverage reporting | Medium |
| Knowledge Graph | Mostly design-level plus lightweight graph edges table | Clear conceptual model | Low-Medium |
| Evidence Engine | Implemented as table schema + scripted validation | Evidence source governance structure added | Medium |
| Reports Layer | Extensive report generation across scripts | Strong transparency and validation cadence | High |
| Provider Inbox | Documented and partially represented in verification flow | Verification request artifacts exist | Low-Medium |
| Simulation Framework | Extensive scenario runners in scripts | Broad regression checks and domain audits | High |
| Audit Framework | Strong report and traceability patterns | Ranking traceability and benchmark guards present | Medium-High |

## Part 3: Family Journey Review (Architecture Lens)

Flow reviewed:

Family -> Questionnaire -> Matching -> Narrative -> Verification -> Provider Response -> Updated Recommendation -> Contact Provider -> Move In -> Outcome Learning

Weak points identified:

1. Questionnaire to matching handoff relies heavily on client-side runtime state with limited backend trace persistence.
2. Verification trigger UX exists, but provider response SLA and escalation workflow are not end-to-end operationalized.
3. Updated recommendation path is available in simulations but not yet hardened as a fully traceable event pipeline.
4. Contact-provider and move-in workflow data capture is still partly synthetic in reports.
5. Outcome learning exists but has limited explicit closed-loop deployment governance for weekly model/weight updates.

## Part 5: Data Flow Map

| Source | Owner | Trust Level | Refresh Frequency | Expiration/Decay Policy | Primary Consumers |
| --- | --- | --- | --- | --- | --- |
| CMS provider/quality/staffing | CMS + OPTIME ingestion | High | Scheduled import/startup and scripted refresh | Medium term (monthly/quarterly) | Matching, quality scoring, clinical narratives |
| State inspections | State agencies + ingestion jobs | High | Periodic ingestion | Medium term | Safety and compliance scoring |
| Provider portal submissions | Verified facility users | High if identity verified, else moderate | Near real-time | TTL by capability category | Facility memory, verification, profile completeness |
| Family inputs/questionnaire | Family users | Moderate to high for preference data | Per session | Session + profile retention policy | Matching, narrative personalization |
| OSINT/public web | OPTIME intelligence collection | Moderate (source weighted) | Scheduled runs | Faster decay due volatility | Intelligence profile, tie-break context |
| Clinical evidence references | OPTIME evidence curation | High if trusted sources | Periodic review tasks | Review-date governed | Clinical explanation layer |
| Activity calendar imports | Provider + parsers | Moderate to high | Import driven | 30-180 day relevance | Activities fit and confidence |
| Reviews/social signals | Public platforms + parsing | Moderate | Scheduled collection | Rapid decay and drift | Family experience and risk narrative |
| Outcome learning events | OPTIME analytics | High when tracked internally | Daily/weekly | Longitudinal | Matching improvement, calibration |

## Part 7: Matching Engine Review

Reproducibility and explainability status:

- Score traceability exists and report scripts provide deterministic replay patterns.
- Tiered logic and unknown-handling guards are explicit in simulation outputs.
- Remaining concern: a substantial portion of ranking behavior still executes client-side, increasing drift risk between UI behavior and backend API contract.

No hidden weights / magic number assessment:

- Many weights are explicit and surfaced in reports.
- Some thresholds are embedded in engine/script code and not centrally versioned in a single score policy registry.

## Part 8: Clinical Review

Strengths:

- Clinical explanation scaffolding and evidence record requirements are now defined.
- Family-language translation patterns reduce jargon risk.
- Verification workflow separates UNKNOWN from NO in key flows.

Gaps:

- Some narrative statements remain template-driven and not fully bound to persisted evidence link records at recommendation time.
- Clinical claim governance is script-validated but not yet enforced by a centralized runtime policy service.
- Clinical terminology QA and contraindication checks need stronger automated linting.

## Part 9: Business Review

Value to families:

- High: transparent recommendations, verification workflow, family-first explanation trajectory.

Value to providers:

- Medium-High: portal identity flow, capability updates, memory persistence, profile completeness incentives.

Revenue model opportunities:

- Provider subscription tiers by verification speed, profile enrichment, lead analytics, and occupancy optimization.
- Enterprise API/analytics packages for multi-facility groups.
- Premium family concierge workflows and verified comparison packs.

## Architecture Verdict

The platform is credible and differentiated in explainable matching plus validation culture, but requires an orchestration and governance consolidation phase before enterprise-scale rollout.
