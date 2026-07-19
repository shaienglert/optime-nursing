# RESET_RECONCILIATION_REPORT

## EXECUTIVE TRUTH

- The repository contains substantial implemented runtime code (FastAPI backend, Next.js frontend, ingestion, scoring, supervisor loops), but operational truth is mixed and not uniformly production-complete.
- Canonical data and reporting surfaces are inconsistent: a statewide inventory reports 64/67 counties while legacy discovery/executive surfaces still show 3/67.
- Recommendation runtime exists and executes deterministic gating, but still uses explicit weighted scoring profiles and has benchmark accuracy gaps.
- Agent ecosystem is partially operational in runtime snapshots, while multiple generated agent surfaces are still UNPROVEN placeholder outputs.
- This report is evidence-based from code paths, generated artifacts, and Git baseline; documentation-only claims were not treated as implementation proof.

## WHAT IS ACTUALLY WORKING

### Current System Classification

| Area | Status | Evidence |
| --- | --- | --- |
| Frontend app shell and results flow | WORKING | `frontend/src/app/page.tsx`, `frontend/src/app/results/results-page-client.tsx` |
| Recommendation engine runtime | WORKING | `frontend/src/lib/optime-v2-engine.ts` |
| Questionnaire/person model state | WORKING | `frontend/src/context/questionnaire-context.tsx` |
| Backend API server and startup wiring | WORKING | `backend/app/main.py` |
| CMS ingestion pipeline (provider/quality/staffing/inspection) | WORKING | `backend/app/main.py` (`run_phase1_ingestion`), `backend/app/services/cms_*_import.py` |
| SQLite ORM model layer | WORKING | `backend/app/database.py`, `backend/app/models/*.py` |
| Supervisor and prepared agent snapshot loop | WORKING | `backend/app/services/agent_knowledge_reports.py`, `backend/app/services/chief_ai_supervisor.py` |
| Executive report scheduler + archive + SMTP path | WORKING | `backend/app/services/executive_report_service.py`, `backend/app/services/report_archive_service.py`, `backend/app/services/email_service.py` |
| Validation script framework | WORKING | `scripts/run_*validation*.cjs`, `scripts/run_phase19_recommendation_validation.cjs` |

## WHAT IS PARTIAL

| Area | Status | Why Partial |
| --- | --- | --- |
| Canonical facility universe | PARTIAL | Multiple inventories disagree and are mixed by population/care type; canonical convergence incomplete (`database/florida_senior_living_inventory.json` vs `database/south_florida_senior_living_inventory.json`, `reports/discovery_report.md`). |
| Geographic coverage | PARTIAL | Statewide inventory is 64/67 counties, not complete (`reports/florida_discovery_inventory.md`). |
| AHCA/Florida Health Finder official integration | PARTIAL | AHCA links/license IDs exist but direct authoritative ingestion pipeline is not proven (`scripts/build_florida_senior_living_inventory.py`, `scripts/build_intelligence_wave1.py`). |
| Decision logic governance | PARTIAL | Must/critical gating exists, but formal professional rule authority governance is not enforced end-to-end (`frontend/src/lib/optime-v2-engine.ts`, `backend/app/services/evidence_source_integrity.py`). |
| Agent runtime estate | PARTIAL | Runtime snapshots exist, but generated registries contain UNPROVEN placeholders and missing concrete identity mapping (`reports/agent_registry.md`, `reports/agent_status_dashboard.md`). |
| Validation truth quality | PARTIAL | Technical validations run, but external/real-world agreement gates fail (`reports/human_advisor_benchmark.md`, `reports/real_world_outcome_validation.md`, `reports/recommendation_accuracy_dashboard.md`). |

## WHAT IS PLACEHOLDER/UNPROVEN

| Area | Status | Evidence |
| --- | --- | --- |
| Agent registry/dashboard identity surfaces | PLACEHOLDER | `reports/agent_registry.md` and `reports/agent_status_dashboard.md` use `UNPROVEN_AGENT` rows. |
| Visual/media intelligence source payload | PLACEHOLDER | `backend/app/services/intelligence_agent.py` includes generated placeholder imagery (`source.unsplash.com`, `placehold.co`). |
| Several social/workforce signals in intelligence layers | UNPROVEN | `scripts/build_intelligence_wave1.py` and related builders emit many source entries with null URLs/UNKNOWN confidence. |

## WHAT IS MISSING

- A single enforced canonical source-of-truth policy across all facility datasets and report generators.
- A fully consistent runtime agent identity map (spec names, status names, generated registry names).
- End-to-end professional rule authority enforcement (rule source, scope, validation state, authority level applied at decision time).
- A true independent validation track with advisor agreement above release thresholds.
- Modular API routing implementation for `backend/app/api/facilities.py` (file exists but currently empty).

## FALSE COMPLETENESS FINDINGS

1. Discovery status marked COMPLETE in `reports/discovery_report.md` while coverage in same report is only 3/67 and source file is south-florida snapshot, not statewide canonical.
2. `reports/executive_dashboard.md` still states 3/67 coverage while statewide inventory report states 64/67.
3. Master-book completeness shows all chapters generated (`docs/master-book/MASTER_BOOK_COMPLETENESS_REPORT.md`), but same report acknowledges runtime consistency gaps and UNPROVEN agent placeholders.
4. Agent architecture/spec docs declare complete agent landscape, but runtime-generated agent registry/dashboard still unresolved as `UNPROVEN_AGENT` placeholders.

## CANONICAL DATA STATUS

### Facility Sources Currently Ingested/Used

- CMS Provider dataset (`4pq5-n9py`) via backend import/cache: `backend/app/services/cms_service.py`, `backend/app/services/cms_provider_import.py`.
- CMS quality/staffing/inspection datasets via backend import services.
- Seniorly listings/details and extracted Florida HealthFinder profile links in statewide build script: `scripts/build_florida_senior_living_inventory.py`.
- Additional intelligence layers use CMS + inventory-derived + synthetic placeholders: `scripts/build_intelligence_wave1.py`, `scripts/build_intelligence_layer_v2.py`.

### Canonical Store Candidate

- Runtime relational candidate: `facilities` table in SQLite via `backend/app/models/facility.py`.
- Runtime import default is limited by env (`OPTIME_IMPORT_LIMIT`, default 100 in `render.yaml`), so runtime DB may be partial even if broader JSON inventories exist.

### Current Record Counts (Repository Evidence)

- `database/florida_senior_living_inventory.json`: 713 records, 64/67 counties, generated `2026-07-18T05:39:28+00:00`, CMS-linked records 694.
- `database/south_florida_senior_living_inventory.json`: 784 records, generated `2026-07-15T09:02:09+00:00`.
- `database/market_communities_south_florida.json`: 141 records, generated `2026-07-15T07:04:41+00:00`.

### Coverage and Conflict Findings

- Statewide and legacy discovery tracks are not reconciled.
- Care-type composition in statewide inventory is heavily skewed to Skilled Nursing (694/713), so broad senior-living claims across categories are not yet justified.
- Report disagreement is explicit between `reports/discovery_report.md` (3/67) and `reports/florida_discovery_inventory.md` (64/67).

## DECISION LOGIC STATUS

### Implemented Path Audit

| Stage | Status | Evidence |
| --- | --- | --- |
| USER INPUT | IMPLEMENTED | Questionnaire and rich profile state in `frontend/src/context/questionnaire-context.tsx`. |
| EXPERT INTERPRETATION | PARTIAL | Engine derives personas and clinical reasoning (`frontend/src/lib/optime-v2-engine.ts`), but parts rely on heuristic text/cues. |
| MUST | IMPLEMENTED | Hard rejection reasons for required support/budget/distance/language in `collectHardRejectionReasons` and recommendation assembly. |
| OUR RECOMMENDATION | PARTIAL | Critical/important criteria and narratives exist, but not a formal separate governed layer named `OUR RECOMMENDATION`. |
| NICE TO HAVE | IMPLEMENTED | Optional/preference criteria (`OPTIONAL`, `PREFERENCE`) influence ranking but not hard eligibility. |
| eligibility/filtering | IMPLEMENTED | Accepted/rejected split by hard rejection reasons (`hardRejectionReasons.length`). |
| candidate selection | IMPLEMENTED | Deterministic checklist + ranking logic + fallback recommendations. |
| Top 5 | IMPLEMENTED | Results UI currently uses `TOP_RECOMMENDATION_COUNT = 5` in `results-page-client.tsx`. |
| comparison/evidence display | PARTIAL | Evidence/contributors/checklists are shown, but strict matrixed Top-5 decision table is not fully formalized. |

### Explicit Decision-Risk Findings

- Arbitrary weights present: persona weight profiles and weighted totals are hard-coded in `frontend/src/lib/optime-v2-engine.ts` (`PERSONA_WEIGHT_PROFILES`, `weightedTotal`).
- Unsupported professional rules risk: clinical/critical constraints are partly encoded from heuristics/text cues without a formal authority registry gate.
- AI-generated assumptions present in intelligence enrichment: synthetic/heuristic provenance and placeholder media are active (`backend/app/services/intelligence_agent.py`).
- UNKNOWN treated as NO/0: not found in the core deterministic checklist path; code explicitly states UNKNOWN reduces confidence only.
- Ranking logic without complete traceable justification: partial; traceability structures exist, but advisor benchmark indicates practical ranking quality gap.

## PROFESSIONAL RULE STATUS

### Active Rule Inventory (Current Runtime)

| Rule | Where Used | Source/Evidence in Code | Validation Status |
| --- | --- | --- | --- |
| Required care level is mandatory | `frontend/src/lib/optime-v2-engine.ts` | `buildMatchQualityResult`, hard rejection logic | IMPLEMENTED_NOT_FORMALLY_GOVERNED |
| Budget mandatory constraint | `frontend/src/lib/optime-v2-engine.ts` | `hasStrictBudgetRequirement` and hard rejection reason | IMPLEMENTED_NOT_FORMALLY_GOVERNED |
| Distance/location mandatory constraint | `frontend/src/lib/optime-v2-engine.ts` | mandatory distance checks and hard rejection | IMPLEMENTED_NOT_FORMALLY_GOVERNED |
| Mandatory language support constraint | `frontend/src/lib/optime-v2-engine.ts` | mandatory language rejection | IMPLEMENTED_NOT_FORMALLY_GOVERNED |
| Memory-care mandatory when cognitive need present | `frontend/src/lib/optime-v2-engine.ts` | mandatory memory criterion | IMPLEMENTED_NOT_FORMALLY_GOVERNED |
| Unknown should reduce confidence only | `frontend/src/lib/optime-v2-engine.ts` | explicit trace/audit statement in recommendation report output | IMPLEMENTED |
| Recommendation knowledge freshness/confidence gate | `backend/app/services/agent_knowledge_reports.py`, `/recommendation/knowledge-guard` | `recommendation_guard_decision` policy checks | IMPLEMENTED |
| Evidence source tiering and freshness scoring | `backend/app/services/evidence_source_integrity.py` | `source_tier`, `freshness_status_for_claim`, `confidence_for_claim` | IMPLEMENTED_NOT_FULLY_VALIDATED |

### Authority/Governance Reality

- Formal A/B/C/D professional authority governance is not yet operationally enforced in ranking decisions.
- Rule metadata is distributed across code and reports; no single runtime authority registry controls promotion of rules into MUST.

## AGENT STATUS

### Declared vs Runtime Operational Status

| Agent | Purpose | Implementation Path | Last Verifiable Output | Status |
| --- | --- | --- | --- | --- |
| Clinical Knowledge Agent | Clinical requirement knowledge | `backend/app/services/agent_knowledge_reports.py` (`AGENT_REPORT_DEFS`) | `reports/agent_status_report.md` refresh timestamp present | PARTIAL |
| Provider Intelligence Agent | Provider capability knowledge | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Clinical Evidence Agent | Evidence repository | Declared in docs/specs; not present in runtime `AGENT_REPORT_DEFS` | Spec/docs only | UNPROVEN |
| Activities Intelligence Agent | Activities fit | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Nutrition Intelligence Agent | Dietary support | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Outcome Learning Agent | Outcome calibration | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Knowledge Graph Agent | Relationship graph | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Data Quality & Trust Agent | Trust/freshness/conflicts | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Narrative Intelligence Agent | Narrative packaging | Declared in docs/specs; not present in runtime `AGENT_REPORT_DEFS` | Report registry entries exist but operational identity inconsistent | UNPROVEN |
| Matching Improvement Agent | Ranking policy improvements | `backend/app/services/agent_knowledge_reports.py` | `reports/agent_status_report.md` | PARTIAL |
| Competitive Intelligence Agent | Market intelligence | Declared in docs/specs; not present in runtime `AGENT_REPORT_DEFS` | Spec/docs only | UNPROVEN |
| Chief AI Supervisor | Supervisory governance | `backend/app/services/chief_ai_supervisor.py`, supervisor routes in `backend/app/main.py` | `reports/supervisor_daily_report.md`, supervisor endpoints | WORKING |

## RUNTIME CONSISTENCY GAPS

1. Discovery source mismatch: `reports/discovery_report.md` is generated from south-florida inventory while statewide canonical inventory exists separately.
2. Coverage mismatch in active reports: `reports/executive_dashboard.md` shows 3/67 while `reports/florida_discovery_inventory.md` shows 64/67.
3. Agent identity mismatch: runtime status report contains concrete agent keys, while `reports/agent_registry.md` and `reports/agent_status_dashboard.md` show `UNPROVEN_AGENT` placeholders.
4. API architecture mismatch: route inventory is centralized in `backend/app/main.py` (42 decorators), but `backend/app/api/facilities.py` exists and is empty.
5. Data-universe mismatch: runtime DB ingestion defaults to limited import count (`render.yaml` sets `OPTIME_IMPORT_LIMIT=100`), while large JSON inventories imply broader universe.
6. Validation mismatch: technical validation scripts pass some gates, but external agreement gate fails (`Advisor agreement 52%`).

## BLOCKERS

- No reconciled canonical facility universe across runtime DB, statewide inventory, and legacy south-florida reporting streams.
- Inconsistent reporting surfaces create contradictory operational truth.
- Agent operational observability is degraded by placeholder/unproven generated surfaces.
- Professional rule governance is not enforced as a centralized authority mechanism in runtime decisions.
- External validation quality gate is failing (advisor agreement).

## RECOMMENDED EXECUTION ORDER

1. Freeze one canonical facility dataset + one canonical report source path and retire conflicting legacy report generators.
2. Reconcile runtime DB ingest scope with canonical universe policy (explicitly define production candidate universe).
3. Normalize agent naming/identity registry and eliminate UNPROVEN placeholder generation in operational dashboards.
4. Establish central professional-rule registry with source, scope, validation state, and runtime enforcement hooks.
5. Re-run external benchmark after decision-governance corrections and track deltas in one canonical accuracy dashboard.

## GIT / CHANGE BASELINE

- Branch: `main`
- HEAD: `85f86f1edc5f093317ed917fbd5e7fb58cdd35fe`
- Working tree during audit start: clean (`git status --short` empty)
- Recent relevant commits:
  - `85f86f1` Fix one-time SMTP startup validation logging and completion state
  - `75ad654` Add one-time startup SMTP validation email on deployment
  - `13ca085` Phase 48: automate daily executive intelligence reporting
  - `2b353ef` Close Master Book gaps: Decision Psychology Research and Outcome Framework
  - `31d08e8` Create OPTIME Master Knowledge Book

## VALIDATION EVIDENCE MAP

- API/runtime wiring: `backend/app/main.py`, `backend/app/services/executive_report_service.py`, `backend/app/services/agent_knowledge_reports.py`.
- Canonical data evidence: `database/florida_senior_living_inventory.json`, `database/south_florida_senior_living_inventory.json`, `reports/florida_discovery_inventory.md`, `reports/discovery_report.md`.
- Decision logic evidence: `frontend/src/lib/optime-v2-engine.ts`, `frontend/src/app/results/results-page-client.tsx`.
- Professional rule/evidence trace evidence: `backend/app/services/evidence_source_integrity.py`, `/recommendation/knowledge-guard` route in `backend/app/main.py`.
- Agent status evidence: `backend/app/services/agent_knowledge_reports.py`, `reports/agent_status_report.md`, `reports/agent_registry.md`, `reports/agent_status_dashboard.md`.
- Validation status evidence: `reports/recommendation_accuracy_dashboard.md`, `reports/human_advisor_benchmark.md`, `reports/real_world_outcome_validation.md`.

WORKING: frontend app shell/results, backend API runtime, CMS ingestion services, scheduler/report pipeline, core recommendation execution path
PARTIAL: canonical data convergence, AHCA direct integration, agent runtime observability, professional-rule governance, external validation quality
PLACEHOLDER: UNPROVEN agent registry/dashboard rows, placeholder media/synthetic signal pathways in intelligence enrichment
MISSING: unified canonical data policy + reconciled report pipeline, centralized rule authority registry, non-placeholder operational agent registry
BLOCKERS: contradictory coverage reports, mixed data universes, failed advisor agreement gate, unresolved agent identity consistency
