# Documentation Governance and Filing Rules

## Purpose

Keep OPTIME documentation navigable, truthful and non-duplicative. The
repository contains both durable documentation and many generated or
time-specific reports. They must not be treated as equivalent.

## Authority Order

When documents conflict, use this order unless a newer approved principle
explicitly supersedes an older one:

1. `AGENTS.md` and `docs/OPTIME_PRINCIPLES_REGISTRY.md` for repository and
   constitutional governance.
2. `docs/OPTIME_PRINCIPLES.md` and `docs/LAW_00_TRUSTED_INTELLIGENT.md` for
   doctrine.
3. Relevant implementation code and tests for implemented behavior.
4. `docs/master-book/` and durable topic specifications for maintained design.
5. Dated reports for observations, validation evidence and historical context.

Reports never silently change a governing principle or implemented behavior.

## Filing Rules

| Document type | File it in | Naming rule | Required metadata |
| --- | --- | --- | --- |
| Constitutional rule / product principle | `docs/` and update the Principles Registry | Stable descriptive name | Owner approval reference where needed; implementation/test links |
| Durable product or architecture chapter | `docs/master-book/` | Numbered chapter if part of the Master Book | Purpose, current status, dependencies, limitations |
| Topic-specific spec, data source guide, launch plan or contract | `docs/` | Stable descriptive name | Scope, owner, source of truth |
| Agent specification | `docs/agent_specs/` | `<agent>_spec.md` where applicable | Authority, inputs, outputs, guardrails |
| Backend runbook / incident guide | `backend/docs/` | Stable operational name | Operational owner, trigger and recovery steps |
| Audit, investigation, validation or simulation | `reports/` | `TOPIC_YYYY-MM-DD.md` for new time-bound work | Date, scope, source data, conclusion, limitations |
| Daily generated report | `reports/daily/` | Generator-owned convention | Run time, generator/version and current-pointer policy |
| Superseded report snapshot | `reports/versions/` | Generator-owned timestamp convention | Parent report and snapshot time |
| Source data / evidence extract | `data/` | Source/domain-oriented path | Source, retrieval time, validation state, provenance |
| Database schema / migration / runtime artifact | `database/` | Database-oriented path | Migration or producer identity; no narrative product policy |

## Rules That Prevent Documentation Drift

- One canonical document per durable topic. Link to it instead of cloning it.
- A generated report must identify its run date and input scope. If it has no
  date, treat it as potentially stale until validated.
- Current dashboards must have a clearly named current pointer; historical
  snapshots belong in `reports/versions/` or `reports/daily/`.
- Do not delete or rewrite historical reports merely to make the tree cleaner.
  Archive only after identifying the replacement and preserving provenance.
- Keep factual claims close to their source data. Do not convert unverified
  discovery leads into durable product facts.
- A plan or status document must state its snapshot date. It cannot claim to be
  a live task board without an update mechanism.

## Maintenance Cadence

| Cadence | Owner action |
| --- | --- |
| Every feature / PR | Update the closest durable spec if behavior changes; add a dated report only for the evidence of the work. |
| Weekly | Refresh `reports/daily/latest.md` and identify reports that should move to `reports/versions/`. |
| Monthly | Review the documentation index, current status and next-task sources; mark obsolete planning surfaces. |
| Before a semantic system change | Run the Principle Impact Check from the Principles Registry. |

## Explicit Non-Actions

This governance policy does not authorize deletion, data migration, renaming of
generated artifacts, or changes to ranking semantics. Those actions require a
separate scoped decision.
