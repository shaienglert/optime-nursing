# Documentation Filing Audit — 2026-09-09

## Scope

Repository documentation inventory and filing review. This audit classifies
the material; it does not validate the factual correctness of every historical
report and does not delete, move or rewrite historical evidence.

## Inventory

The scan found **478** Markdown/Text files outside `.git` and frontend
dependencies:

| Location | Files | Classification |
| --- | ---: | --- |
| `reports/` | 365 | Generated reports, dashboards, audits and historical evidence |
| `docs/` | 93 | Durable product, architecture, doctrine and agent specifications |
| `data/` | 7 | Data/evidence documentation and source artifacts |
| `backend/` | 5 | Backend engineering documentation |
| `frontend/` | 3 | Frontend engineering documentation |
| repository root | 4 | Entry-point and top-level planning documents |
| `benchmark/` | 1 | Benchmark-specific documentation |

Within `reports/`, **143** files are stored under `reports/versions/` and
**74** under `reports/daily/`. They are historical or generated surfaces, not
independent current sources of truth.

## Filing Assessment

| Area | Assessment | Action now |
| --- | --- | --- |
| Product/architecture doctrine | Filed in `docs/` and `docs/master-book/` | Added a single entry point: `docs/README.md`. |
| Governing rules | Filed, but previously discoverable only by knowing filenames | Linked the principles, registry, Law 00 and `AGENTS.md` from the library entry point. |
| Website structure | Implemented in `frontend/src/app`, but not previously listed as a route map | Added code-derived site map to `docs/README.md`. |
| Agent specifications | Filed consistently in `docs/agent_specs/` | Kept there; linked from the entry point. |
| Reports / snapshots | Physically filed, but many similarly named report surfaces can be mistaken for current truth | Defined active/history handling and authority order; no destructive cleanup. |
| Roadmaps and open work | Present in multiple dated documents | Linked and explicitly labelled as planning inputs, not a live board. |
| Data and database artifacts | Filed by technical domain | Kept separate from narrative documentation; provenance remains with data. |

## Findings

1. The repository is **not missing a documentation library**; it was missing a
   clear front door and an authority hierarchy.
2. `docs/master-book/22_FILE_INDEX.md` is a broad historical file inventory,
   not a practical navigation guide. `docs/README.md` is now the short,
   maintained navigation layer.
3. The main risk is stale or conflicting status language across reports and
   roadmaps. A dated report must not be read as current production truth without
   checking its source, date and implemented code.
4. The Master Book itself records that there is no single consolidated execution
   board. This audit preserves that fact rather than inventing a false status.
5. No untracked Markdown/Text documents were found in this working tree at the
   time of the audit.

## Follow-up Backlog (Administrative)

| Priority | Work | Acceptance condition |
| --- | --- | --- |
| High | Choose one maintained execution board | It has owner, update cadence, source links and explicit completion state. |
| High | Mark report generators with current/archive policy | Each current dashboard names its current output and version path. |
| Medium | Review duplicate top-level report names | Each duplicate family has one current pointer and preserved history. |
| Medium | Add a project-specific frontend developer guide | It documents actual routes, API boundaries and decision-state ownership. |
| Low | Add automated documentation link and freshness checks | CI detects broken internal links and stale current pointers. |

## Result

All scanned documentation now has a defined home in the filing taxonomy. The
repository has not been destructively reorganized: historical material remains
available and is explicitly separated from canonical documentation by the new
library index and governance rules.
