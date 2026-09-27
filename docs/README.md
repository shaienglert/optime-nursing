# OPTIME Documentation Library

This is the entry point for project documentation. It distinguishes **current
sources of truth** from implementation guides, evidence data, and historical
reports. A report is evidence of a run or an investigation; it is not a product
rule unless this index explicitly names it as authoritative.

## Start Here

| Need | Canonical place |
| --- | --- |
| Product purpose and executive context | [Master Book: Executive Summary](master-book/00_EXECUTIVE_SUMMARY.md), [Vision and Mission](master-book/03_VISION_AND_MISSION.md) |
| Non-negotiable product rules | [Principles](OPTIME_PRINCIPLES.md), [Principles Registry](OPTIME_PRINCIPLES_REGISTRY.md), [Law 00](LAW_00_TRUSTED_INTELLIGENT.md), repository [AGENTS.md](../AGENTS.md) |
| System architecture | [Master Book: System Architecture](master-book/05_SYSTEM_ARCHITECTURE.md), [Data Model](DATA_MODEL.md), [API Reference](master-book/18_API_REFERENCE.md) |
| Site structure and customer journeys | [Site map below](#site-map-derived-from-the-current-app), [Frontend overview](master-book/19_FRONTEND.md), [Results comparison flow](OPTIME_RESULTS_COMPARISON_FLOW.md) |
| Agents and their authority | [Agent directory](master-book/06_AGENT_DIRECTORY.md), [Agent specifications](agent_specs/), [Agent responsibility matrix](agent_specs/agent_responsibility_matrix.md) |
| Data sources and verification | [Data sources](DATA_SOURCES.md), [CMS data sources](CMS_DATA_SOURCES.md), [Verification standards](master-book/25_VERIFICATION_STANDARDS.md) |
| Current roadmap and open work | [Current status](master-book/28_CURRENT_STATUS.md), [Next tasks](master-book/30_NEXT_TASKS.md), [Master roadmap](../MASTER_ROADMAP.md) |
| Historical audits, experiments, and run outputs | [Reports](../reports/), [filing audit](../reports/DOCUMENTATION_FILING_AUDIT_2026-09-09.md) |

## Documentation Map

| Area | What belongs there | Status / rule |
| --- | --- | --- |
| `docs/master-book/` | Durable product, architecture, system, governance, status and roadmap chapters | Reference layer. Prefer updating the relevant chapter instead of adding another broad overview. |
| `docs/` | Domain specifications, doctrine, data source definitions, market/launch plans and contracts | Use for durable, topic-specific product documentation. |
| `docs/agent_specs/` | Agent scope, authority, interfaces, operating procedures and ownership | Specification layer; do not use an agent report as its specification. |
| `backend/docs/` | Backend technical runbooks, incidents and implementation notes | Engineering operational documentation. |
| `reports/` | Dated audits, simulations, dashboards, validation outputs and investigations | Evidence/history layer. Must say its scope and date; it does not override doctrine. |
| `reports/versions/` | Superseded snapshots of generated report surfaces | Archive only; never use as current truth. |
| `reports/daily/` | Daily run artifacts; `daily/latest.md` is the current pointer | Short-lived operational history. |
| `data/` | Source-derived datasets and verification artifacts, not narrative policy | Data/evidence layer. Keep provenance with the data. |
| `database/` | Schema, migrations and runtime data artifacts | Engineering/data layer; not a general document library. |

## Site Map (Derived From the Current App)

The product routes below are derived from `frontend/src/app`. This is a route
map, not a promise that every route is production-complete.

| Audience | Route | Purpose |
| --- | --- | --- |
| Family / visitor | `/` | Main entry point |
| Family / visitor | `/intake`, `/adaptive-interview`, `/questionnaire` | Collect needs and preferences |
| Family / visitor | `/results`, `/results/details`, `/results/personal-report` | Recommendations, details and personal report |
| Family / visitor | `/compare`, `/profiles`, `/workspace` | Compare, review and manage the decision journey |
| Family / visitor | `/facilities`, `/facilities/[id]`, `/facility/[id]` | Facility discovery and profiles |
| Institution | `/provider`, `/provider/[facilityId]` | Provider/facility experience |
| Institution | `/facility-outreach/[token]` | Respond to evidence/outreach requests |
| Internal | `/admin`, `/admin/executive-intelligence`, `/admin/platform-operations`, `/admin/facility-outreach` | Operational and intelligence administration |

## Governing Rules

1. **Outcome only:** recommendation logic cannot use commercial incentives.
2. **No evidence, no score:** missing values are not estimated.
3. **Visible uncertainty and explanation:** a recommendation must disclose why,
   sources, confidence and missing information.
4. **Unknown is not negative evidence:** incomplete coverage is not a penalty.
5. **Verified case-relevant evidence can strengthen a proven match; generic
   profile completeness cannot.**
6. **Principle Impact Check:** before a substantial change to ranking, scoring,
   recommendations, agents, evidence, unknown/confidence semantics, source
   governance, monetization boundaries or canonical architecture, use the
   check in the [Principles Registry](OPTIME_PRINCIPLES_REGISTRY.md). Product
   principle changes and architectural deviations require explicit owner
   approval.

The complete, authoritative wording and lifecycle record are in
[OPTIME Principles](OPTIME_PRINCIPLES.md) and the
[Principles Registry](OPTIME_PRINCIPLES_REGISTRY.md). This summary does not
replace them.

## Current Work: How to Read It Safely

There are several roadmaps and status reports created at different times.
Treat the following as planning inputs, not a single live execution board:

| Source | What it tells you | Caution |
| --- | --- | --- |
| [Master roadmap](../MASTER_ROADMAP.md) | Cross-domain capability sequence | Generated 2026-08-05; validate against current code before acting. |
| [Current status](master-book/28_CURRENT_STATUS.md) | Measured historical snapshot | Explicitly identifies mixed-surface inconsistencies. |
| [Next tasks](master-book/30_NEXT_TASKS.md) | Evidence-derived backlog | Calls out the absence of one consolidated execution board. |
| [Filing audit](../reports/DOCUMENTATION_FILING_AUDIT_2026-09-09.md) | Documentation ownership, gaps and handling rules | Administrative audit, not product truth. |

## Adding a New Document

1. Decide whether it is a durable rule/specification, implementation guide,
   data artifact, or run-specific report.
2. Put it in the corresponding location in the map above.
3. Add date, owner/scope, source inputs and a clear statement of whether it is
   authoritative.
4. Link it from the closest index. Do not create a second “master” document
   for an existing topic.
5. For semantic product changes, complete the Principle Impact Check before
   implementation.

Detailed filing rules are in [Documentation Governance](DOCUMENTATION_GOVERNANCE.md).
