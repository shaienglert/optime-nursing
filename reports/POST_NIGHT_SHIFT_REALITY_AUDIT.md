# POST NIGHT SHIFT REALITY AUDIT

Generated at UTC: 2026-07-20
Audit scope: Phase 2 to Phase 9 implementation reality versus claims
Audit mode: Read-only audit, no feature build, no repair

## EXECUTIVE TRUTH

- Git history confirms start baseline [192ea1b](../.git) and reported night-shift end [066fb74](../.git).
- Phase artifacts for 2-9 mostly exist and validators pass mechanically.
- Core production recommendation runtime is still centered on [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts) and not on phase registries/schemas/snapshots.
- Professional rule registry, three-layer schema, evidence matrix snapshot, top5 artifact, and traceability matrix are not loaded by runtime frontend/backend recommendation flow.
- Mechanical validation is strong; external professional and real-world validation remain partial.

## WHAT ACTUALLY BECAME OPERATIONAL

- Questionnaire answer capture and persistence in session state:
  - [frontend/src/app/page.tsx](../frontend/src/app/page.tsx)
  - [frontend/src/context/questionnaire-context.tsx](../frontend/src/context/questionnaire-context.tsx)
- Facility retrieval from backend runtime DB:
  - [frontend/src/lib/api.ts](../frontend/src/lib/api.ts)
  - [backend/app/main.py](../backend/app/main.py)
- Candidate generation, eligibility, ranking, accepted/rejected/fallback handling, display top 5 slice:
  - [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts)
  - [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx)

## WHAT WAS IMPLEMENTED BUT NOT WIRED

- Rule registry artifact not consumed by runtime scoring path:
  - [database/professional_rule_registry.json](../database/professional_rule_registry.json)
- Three-layer decision model schema not consumed by runtime scoring path:
  - [database/three_layer_decision_model_schema.json](../database/three_layer_decision_model_schema.json)
- Candidate governance policy artifact not consumed by runtime path:
  - [database/candidate_governance_policy.json](../database/candidate_governance_policy.json)
- Top5 decision table artifact not consumed by frontend results:
  - [database/top5_decision_table.json](../database/top5_decision_table.json)
- Recommendation traceability matrix artifact not consumed by runtime UI/API decision path:
  - [database/recommendation_traceability_matrix.json](../database/recommendation_traceability_matrix.json)

## WHAT IS MECHANICAL ONLY

- Phase validators and registry runners:
  - [scripts/validate_professional_rule_governance.py](../scripts/validate_professional_rule_governance.py)
  - [scripts/validate_three_layer_decision_model.py](../scripts/validate_three_layer_decision_model.py)
  - [scripts/validate_facility_evidence_matrix.py](../scripts/validate_facility_evidence_matrix.py)
  - [scripts/validate_candidate_governance.py](../scripts/validate_candidate_governance.py)
  - [scripts/validate_top5_decision_table.py](../scripts/validate_top5_decision_table.py)
  - [scripts/validate_recommendation_traceability.py](../scripts/validate_recommendation_traceability.py)
  - [scripts/validate_separated_validation_program.py](../scripts/validate_separated_validation_program.py)
  - [scripts/run_phase2_to_phase8_validation_bundle.py](../scripts/run_phase2_to_phase8_validation_bundle.py)

## WHAT IS DOCUMENTATION/SCHEMA ONLY

- Governance and reconciliation reports claiming completion:
  - [reports/PHASE2_TO_PHASE9_RECONCILIATION_REPORT.md](../reports/PHASE2_TO_PHASE9_RECONCILIATION_REPORT.md)
  - [reports/PROFESSIONAL_RULE_GOVERNANCE_REPORT.md](../reports/PROFESSIONAL_RULE_GOVERNANCE_REPORT.md)
  - [reports/THREE_LAYER_DECISION_MODEL_REPORT.md](../reports/THREE_LAYER_DECISION_MODEL_REPORT.md)
  - [reports/FACILITY_EVIDENCE_MATRIX_REPORT.md](../reports/FACILITY_EVIDENCE_MATRIX_REPORT.md)
  - [reports/CANDIDATE_GOVERNANCE_REPORT.md](../reports/CANDIDATE_GOVERNANCE_REPORT.md)
  - [reports/TOP5_DECISION_TABLE_REPORT.md](../reports/TOP5_DECISION_TABLE_REPORT.md)
  - [reports/RECOMMENDATION_TRACEABILITY_REPORT.md](../reports/RECOMMENDATION_TRACEABILITY_REPORT.md)
  - [reports/SEPARATED_VALIDATION_PROGRAM_REPORT.md](../reports/SEPARATED_VALIDATION_PROGRAM_REPORT.md)

## VERIFY EVERY PHASE CLAIM

| PHASE | CLAIMED DELIVERABLE | FILE EXISTS? | ACTUAL LOGIC IMPLEMENTED? | RUNTIME WIRED? | USED BY PRODUCTION FLOW? | VALIDATION TYPE | EXTERNAL VALIDATION? | REAL-WORLD VALIDATION? | STATUS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | Professional rule governance registry + validator | YES | YES (registry + checks) | NO (registry not loaded in runtime) | NO | Mechanical validator | PARTIAL | NO | IMPLEMENTED_NOT_WIRED |
| 3 | Three-layer decision model schema + validator | YES | YES (schema + checks) | NO | NO | Mechanical validator | NO | NO | MECHANICAL_ONLY |
| 4 | Facility evidence matrix schema/snapshot/builder/validator | YES | YES (offline builder + checks) | NO (snapshot not loaded by engine) | NO | Mechanical validator | NO | NO | IMPLEMENTED_NOT_WIRED |
| 5 | Candidate governance policy + validator | YES | YES (policy + static pattern checks) | NO (policy file not consumed) | NO | Mechanical validator | NO | NO | MECHANICAL_ONLY |
| 6 | Top-5 decision table artifact generation | YES | YES (offline generation script) | NO (frontend computes top5 directly from engine output) | NO | Mechanical validator | NO | NO | IMPLEMENTED_NOT_WIRED |
| 7 | Recommendation traceability matrix | YES | YES (offline matrix build from top5 artifact) | NO | NO | Mechanical validator | NO | NO | IMPLEMENTED_NOT_WIRED |
| 8 | Separated validation program tracks | YES | YES (registry + runner + checks) | NO (not used in recommendation runtime) | NO | Mechanical validator orchestration | PARTIAL | NO | MECHANICAL_ONLY |
| 9 | Reconciliation closure report + bundle script | YES | YES (bundle runner + report) | NO | NO | Mechanical bundle | PARTIAL | NO | DOCUMENTED_ONLY |

## REAL USER FLOW TRACE

Source flow traced from executable code in [frontend/src/app/page.tsx](../frontend/src/app/page.tsx), [frontend/src/context/questionnaire-context.tsx](../frontend/src/context/questionnaire-context.tsx), [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx), [frontend/src/lib/api.ts](../frontend/src/lib/api.ts), [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts), [backend/app/main.py](../backend/app/main.py).

| FLOW ARROW | STATUS | EVIDENCE |
| --- | --- | --- |
| USER OPENS QUESTIONNAIRE -> answers questions | WIRED | [frontend/src/app/page.tsx](../frontend/src/app/page.tsx) |
| answers questions -> answers stored | WIRED | setState + session save in [frontend/src/context/questionnaire-context.tsx](../frontend/src/context/questionnaire-context.tsx) |
| answers stored -> interpretation | WIRED | buildClinicalRequirements / assessClinicalCapability in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts) |
| interpretation -> professional rule registry lookup | NOT WIRED | no registry load call in frontend/backend runtime paths |
| professional rule registry lookup -> MUST / OUR_RECOMMENDATION / NICE_TO_HAVE | NOT WIRED | classification file exists only in schema/registry, not runtime-generated from registry |
| MUST / OUR_RECOMMENDATION / NICE_TO_HAVE -> canonical facility universe | NOT WIRED | runtime fetches /facilities from DB, not [database/florida_senior_living_inventory.json](../database/florida_senior_living_inventory.json) |
| canonical facility universe -> facility evidence matrix | NOT WIRED | evidence matrix snapshot built offline script only |
| facility evidence matrix -> eligibility | NOT WIRED | eligibility uses engine checklist + care type heuristics directly |
| eligibility -> candidate selection | WIRED | accepted/rejected/fallback in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts) |
| candidate selection -> Top 5 | WIRED | slice(0,5) in [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx) |
| Top 5 -> comparison table | NOT WIRED | no production comparison-table component in results path |
| comparison table -> evidence drill-down | PARTIAL | in-card checklist evidence exists in results page; no runtime source-trace drilldown route wired in UI |

## PROFESSIONAL RULE RUNTIME STATUS

Audited file: [database/professional_rule_registry.json](../database/professional_rule_registry.json)

- total rules: 23
- Level A: 5
- Level B: 6
- Level C: 6
- Level D: 6
- UNKNOWN authority level: 0
- unknown/unmapped entries: 5
- externally validated rules: 0
- internally validated only / pending external: 23
- rules with missing evidence field: 0
- rules marked active_runtime in registry: 22

Runtime consumption test:

- no runtime code path loads [database/professional_rule_registry.json](../database/professional_rule_registry.json) in production recommendation flow.
- status: IMPLEMENTED_NOT_WIRED

Rules actually called by production recommendation runtime:

- hardcoded logic in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts), not registry-driven lookup.

Rules existing only in registry:

- all registry metadata entries as registry-driven control are not runtime-consumed.

## THREE-LAYER MODEL RUNTIME STATUS

Required classes audited: MUST / OUR_RECOMMENDATION / NICE_TO_HAVE

- MUST in runtime path:
  - generated via hardcoded mandatory checks and hard rejection logic in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts)
  - classification type: USER-EXPLICIT + HARDCODED safety logic
- OUR_RECOMMENDATION in runtime path:
  - implicit by accepted ranking output from [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts)
  - classification type: HARDCODED / LEGACY engine behavior
- NICE_TO_HAVE in runtime path:
  - preference items exist as PREFERENCE tier in checklist scoring, but not emitted as governed NICE_TO_HAVE class object
  - classification type: PARTIAL HARDCODED

Governance bypass risk:

- old/hardcoded logic can bypass phase governance artifacts because runtime does not load three-layer schema or rule registry.

## HARDCODED WEIGHTS STILL ACTIVE

Active material weights/thresholds/modifiers in runtime path:

- persona weight profiles: active in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts)
- care taxonomy inference weighted signals: active in [frontend/src/lib/api.ts](../frontend/src/lib/api.ts)
- distance step points and mandatory thresholds: active in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts)
- tie-breakers and ranking modifiers: active in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts)
- understanding-profile weights: active for questionnaire readiness UI in [frontend/src/lib/understanding-profile.ts](../frontend/src/lib/understanding-profile.ts), not primary ranking engine driver

Status per material item:

- PERSONA_WEIGHT_PROFILES: ACTIVE
- inferCareTaxonomy weighted buckets: ACTIVE
- parseDistancePoints bands: ACTIVE
- completeness tie-breaker: ACTIVE
- preference bonus in ranking: ACTIVE
- understanding-profile DOMAIN_WEIGHTS: ACTIVE (UI/readiness), not direct candidate ranking gate

Can an unvalidated weight still change:

- eligibility? YES (care taxonomy + mandatory heuristics can affect hard rejection)
- candidate ordering? YES
- Top 5? YES
- displayed recommendation? YES

## FACILITY EVIDENCE RUNTIME STATUS

Evidence matrix reality:

- [database/facility_evidence_matrix_schema.json](../database/facility_evidence_matrix_schema.json): schema artifact
- [database/facility_evidence_matrix_snapshot.json](../database/facility_evidence_matrix_snapshot.json): offline snapshot from builder
- [scripts/build_facility_evidence_matrix_snapshot.py](../scripts/build_facility_evidence_matrix_snapshot.py): offline generation

Runtime usage in recommendation path:

- not dynamically loaded by frontend engine
- engine uses facility payload fields + inferred taxonomy + checklist heuristics

Reported warning quantified:

- runtime FL facilities in DB: 100
- confidence_level unknown/null: 100 (100.0%)
- known confidence_level: 0

UNKNOWN and conflict handling:

- engine preserves UNKNOWN checklist states and excludes UNKNOWN from match-score denominator.
- evidence matrix conflict policy exists in artifact, not consumed by recommendation runtime.

## TOP-5 RUNTIME STATUS

Top5 answers with evidence:

- Is Top 5 generated from a real user profile? PARTIAL
  - production UI top5: YES from actual questionnaire state
  - phase6 artifact top5_decision_table.json: NO (generated by offline scripted scenario)
- Does it use canonical facility universe? NO
  - runtime uses backend /facilities DB sample (100 FL records), not canonical 713 artifact
- Does it apply actual MUST requirements? YES
  - via hard rejection and critical NO checks in engine
- Does it use governed professional rules? NO
  - no registry lookup
- Does it preserve UNKNOWN? YES
  - UNKNOWN affects confidence and remains in verification sections
- Does it use real facility evidence? PARTIAL
  - uses backend facility and intelligence payload fields, plus heuristic inference
- Is it connected to frontend results? YES (engine output), but NO for phase6 artifact file
- Can user drill into source evidence? PARTIAL
  - checklist-level evidence visible in results cards; no registry-driven/source-trace drilldown route wired in results
- Can legacy Match Score override it? YES
  - ranking is directly score-driven by existing engine formula and tie-breakers

## REALISTIC END-TO-END CASE RESULT

Externally defined case executed through actual runtime engine path (integration run):

Case:

- age 80
- post-stroke
- explicit 24/7 nursing requirement
- rehab required
- medication management
- mobility limitations
- family preference Miami-Dade nearby
- social engagement desirable
- budget unknown

Observed runtime result:

- accepted_count: 92
- rejected_count: 8
- top5_count: 5
- top5 produced successfully
- UNKNOWN gaps preserved per facility (multiple MUST_UNKNOWN items)

Top5 for executed case:

1) BISCAYNE HEALTH AND REHABILITATION CENTER
2) CRESTVIEW REHABILITATION CENTER, LLC
3) CORAL GABLES NURSING AND REHABILITATION CENTER
4) BROWARD NURSING & REHABILITATION CENTER
5) MORTON PLANT REHABILITATION CENTER

Per facility (all 5 observed similarly in run):

- MUST SATISFIED: Skilled nursing capability; Neurological rehabilitation; Physical therapy
- MUST FAILED: none
- MUST UNKNOWN: Licensed nurses 24/7; Speech therapy; Occupational therapy; Swallowing assessment support; Walker accessibility; Fall prevention protocol; Mobility and transfer assistance
- OUR RECOMMENDATION alignment: present via ranking explanation text
- NICE TO HAVE alignment: limited/empty in this run
- EVIDENCE GAPS: present and explicit
- SOURCE TRACEABILITY: score trace strings present in output

## CHAIN BREAKS

- Break 1: interpretation -> professional rule registry lookup (NOT WIRED)
- Break 2: registry classification -> runtime MUST/OUR/NICE_TO_HAVE mapping (NOT WIRED)
- Break 3: canonical facility universe integration into production recommendation fetch (NOT WIRED)
- Break 4: facility evidence matrix integration into runtime scoring/eligibility (NOT WIRED)
- Break 5: phase6 top5 artifact to frontend (NOT WIRED)
- Break 6: phase7 traceability matrix to runtime evidence drilldown (NOT WIRED)

## AGENT RUNTIME REALITY

Claimed agent participation audited across production flow:

- professional interpretation:
  - NO EVIDENCE in production recommendation path (hardcoded engine logic)
- evidence collection:
  - PARTIAL runtime evidence (backend intelligence collection may run when profiles missing)
  - [backend/app/main.py](../backend/app/main.py), [backend/app/services/intelligence_agent.py](../backend/app/services/intelligence_agent.py)
- facility evaluation:
  - frontend deterministic engine, not autonomous agent orchestration
- candidate selection:
  - frontend engine deterministic sorting, no agent invocation in results path
- Top 5:
  - frontend engine slicing, no agent invocation in results path
- validation:
  - offline scripts and mechanical validators, not autonomous runtime decision agent

Per claimed agent class status:

- ACTUAL RUNTIME INVOCATION: intelligence collection service (data enrichment)
- OFFLINE SCRIPT ONLY: benchmark/simulation/phase validators/builders
- SPEC ONLY: multiple governance/agent report claims without runtime recommendation invocation
- NO EVIDENCE: professional interpretation agent controlling live recommendation selection

## MECHANICAL VALIDATION

Current mechanical outputs observed:

- phase validators and bundle runner report PASS
- this confirms artifact consistency and rule checks
- this does not prove runtime wiring to production user flow

## INTEGRATION VALIDATION

- Partial integration exists for questionnaire -> engine -> results rendering.
- Integration of phase artifacts (registry/schema/matrix/top5 artifact/traceability matrix) into runtime is missing.
- Integration status: PARTIAL

## EXTERNAL PROFESSIONAL VALIDATION

- Registry indicates external validation still required for material rule sets.
- Externally validated rule count observed: 0.
- Status: PARTIAL / PENDING

## REAL-WORLD VALIDATION

- No new real-world outcome validation completion was found in phase 2-9 runtime wiring.
- Status: PARTIAL

## 52% BENCHMARK STATUS

- Latest benchmark artifact found: [reports/human_advisor_benchmark.md](../reports/human_advisor_benchmark.md)
- Stated benchmark: Average Agreement 52%, Benchmark Status FAIL
- report_registry metadata points to this benchmark file as latest tracked benchmark entry
- Mechanical PASS outputs do not replace this external benchmark
- Status: remains latest visible external benchmark in current repository evidence

## FALSE COMPLETENESS FINDINGS

Material overstatements identified where COMPLETE/PASS language exceeds runtime wiring:

1) Phase 2 marked complete despite no runtime registry consumption.
2) Phase 3 marked complete though three-layer schema not runtime-consumed.
3) Phase 4 marked complete though evidence matrix is offline snapshot.
4) Phase 5 marked complete though candidate governance policy file not runtime-consumed.
5) Phase 6 marked complete though top5 artifact is offline and not frontend source.
6) Phase 7 marked complete though traceability matrix is offline and not runtime-linked.
7) Phase 8 marked complete though separated validation tracks are reporting-only for runtime.
8) Phase 9 closure report uses complete language while major chain breaks remain.

False completeness count: 8

## MISSING REQUIRED DELIVERABLES

- REQUIRED_DELIVERABLE_MISSING: [reports/NIGHT_SHIFT_FINAL_REPORT.md](../reports)

## CRITICAL BLOCKERS

- No runtime professional rule registry lookup in production recommendation path.
- No runtime three-layer class generation from governed registry artifacts.
- Canonical universe not wired to production /facilities result source.
- Evidence matrix not wired into runtime eligibility/scoring.

## EXACT IMPLEMENTATION GAP LIST

- G-001: registry exists but not runtime-loaded for recommendation decisions.
- G-002: three-layer model schema exists but live classification is hardcoded.
- G-003: canonical 713/64-67 universe not used by production /facilities feed.
- G-004: evidence matrix snapshot not consumed in runtime recommendation decisions.
- G-005: top5 artifact generated offline; frontend top5 derives from live engine only.
- G-006: traceability matrix generated offline; no runtime UI drilldown bound to it.
- G-007: external/professional validation remains 0 externally validated rules.
- G-008: unvalidated hardcoded weights remain active in live ranking path.
- G-009: confidence_level unknown for 100/100 runtime FL facilities.
- G-010: required night-shift final report file missing.

## RECOMMENDED NEXT EXECUTION ORDER

1) Wire runtime registry loader and rule lookup in recommendation path.
2) Bind runtime outputs to governed three-layer classes per recommendation item.
3) Reconcile production /facilities source with canonical facility universe contract.
4) Integrate facility evidence matrix fields into eligibility and confidence computation.
5) Connect runtime Top5 and traceability views to source-level evidence drilldown.
6) Run integration tests for explicit MUST/UNKNOWN cases after wiring.
7) Perform external professional review gates before completeness claims.
