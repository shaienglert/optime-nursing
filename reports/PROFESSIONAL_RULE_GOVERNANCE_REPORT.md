# Professional Rule Governance Report

Generated At (UTC): 2026-07-20T00:00:00Z
Phase: 2
Scope: Professional Rule Governance only
Baseline Commit: 410efd3
Phase 1 Commit: 192ea1b

## EXECUTIVE TRUTH

- One canonical registry created: database/professional_rule_registry.json.
- One governance validator created: scripts/validate_professional_rule_governance.py.
- Active implemented decision rules inventoried from runtime code and operational validators.
- Documentation-only formulas were not counted as implementation.
- Governance principle enforced in policy and validator: NO EVIDENCE = NO PROFESSIONAL CLAIM.

Inventory summary:

- TOTAL RULES: 23
- LEVEL A: 5
- LEVEL B: 6
- LEVEL C: 6
- LEVEL D: 6
- UNKNOWN/UNMAPPED: 5

## ACTIVE RULE INVENTORY

Implementation-first inventory (runtime and operational script logic):

| RULE_ID | RULE_NAME | USER_SIGNAL | INTERPRETATION | DECISION_EFFECT | CURRENT_LOCATION | CURRENT_IMPLEMENTATION | SOURCE/EVIDENCE | VALIDATION_STATUS | CURRENT_RISK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PR-A-001 | User non-negotiable budget hard gate | Notes indicate strict budget | Budget is MUST | Hard exclusion | frontend/src/lib/optime-v2-engine.ts | Active | User explicit declaration | MECHANICALLY_VALIDATED | Low |
| PR-A-002 | User non-negotiable distance hard gate | Notes + distance mandatory | Geography is MUST | Hard exclusion | frontend/src/lib/optime-v2-engine.ts | Active | User explicit declaration | MECHANICALLY_VALIDATED | Low |
| PR-A-003 | User non-negotiable language hard gate | Language required flags | Language continuity is MUST | Hard exclusion | frontend/src/lib/optime-v2-engine.ts | Active | User explicit declaration | MECHANICALLY_VALIDATED | Low |
| PR-A-004 | Required care-level compatibility gate | assistance/memory/future-care | Safety compatibility gate | Hard exclusion | frontend/src/lib/optime-v2-engine.ts | Active | 42 CFR Part 483 + care-type mapping | EXTERNAL_VALIDATION_REQUIRED | Medium |
| PR-A-005 | Critical clinical capability absence gate | Critical capability state NO | Missing critical support = unsafe | Hard exclusion | frontend/src/lib/optime-v2-engine.ts | Active | 42 CFR Part 483 + critical checklist logic | EXTERNAL_VALIDATION_REQUIRED | Medium |
| PR-B-001 | Clinical requirement extraction | Questionnaire + notes | Build professional checklist | Checklist + questions | frontend/src/lib/optime-v2-engine.ts | Active | Internal mapping logic; external validation pending | MECHANICAL_ONLY | Medium |
| PR-B-002 | Capability assessment with memory-first evidence | Requirement key + facility evidence | Prefer verified evidence, then transparent fallback | YES/NO/LIMITED/UNKNOWN state | frontend/src/lib/optime-v2-engine.ts | Active | Verified memory + metadata cues | MECHANICAL_ONLY | Medium |
| PR-B-003 | Recommendation knowledge guard | Agent freshness/verification/confidence | Use only policy-eligible prepared knowledge | USED/SKIPPED trace log | backend/app/services/agent_knowledge_reports.py | Active | Policy trace persisted | MECHANICALLY_VALIDATED | Low |
| PR-B-004 | Source tier classification | source_name/source_type | Rank source authority | TIER_1..TIER_4 | backend/app/services/evidence_source_integrity.py | Active | Source tier definitions | MECHANICALLY_VALIDATED | Low |
| PR-B-005 | Claim freshness classification | claim_type + dates | Domain freshness windows | CURRENT/AGING/STALE/UNKNOWN | backend/app/services/evidence_source_integrity.py | Active | Freshness policy logic | MECHANICALLY_VALIDATED | Low |
| PR-B-006 | Claim confidence calculation | tier + freshness + conflict | Confidence declines with stale/conflict | confidence 0..1 | backend/app/services/evidence_source_integrity.py | Active | Confidence formula | MECHANICALLY_VALIDATED | Low |
| PR-C-001 | Preference YES bonus | Preference assessments | Preferences shape order only | Ranking bonus | frontend/src/lib/optime-v2-engine.ts | Active | Checklist preference yes count | MECHANICAL_ONLY | Medium |
| PR-C-002 | Family/clinical tie-break | Equal scores | Resolve ties transparently | Ranking order | frontend/src/lib/optime-v2-engine.ts | Active | Accepted sort chain | MECHANICAL_ONLY | Medium |
| PR-C-003 | Fallback ranking when none accepted | accepted length is zero | Show best available with uncertainty | Display order | frontend/src/lib/optime-v2-engine.ts | Active | Fallback sort logic | MECHANICALLY_VALIDATED | Low |
| PR-C-004 | Distance band scoring | Distance minutes | Travel burden preference | Family-fit adjustment | frontend/src/lib/optime-v2-engine.ts | Active | parseDistancePoints heuristic | MECHANICAL_ONLY | Medium |
| PR-C-005 | Future-care preference adjustment | futureCarePreference | Preference-sensitive ordering | Ranking adjustment | frontend/src/lib/optime-v2-engine.ts | Active | evaluateFutureCarePreference | MECHANICAL_ONLY | Medium |
| PR-C-006 | UNKNOWN affects confidence only | UNKNOWN checklist state | Unknown is not NO | Confidence/readiness only | frontend/src/lib/optime-v2-engine.ts | Active | Explicit score trace and formula | MECHANICALLY_VALIDATED | Low |
| PR-D-001 | Persona weight profile table | Persona classification | Heuristic weight map | Explanatory/material weighting | frontend/src/lib/optime-v2-engine.ts | Active | Static map | UNVALIDATED | High |
| PR-D-002 | Understanding domain weights | Coverage signals | Heuristic readiness weighting | Understanding score | frontend/src/lib/understanding-profile.ts | Active | Static map | UNVALIDATED | Medium |
| PR-D-003 | Understanding critical multipliers | Missing critical domains | Heuristic penalty curve | Penalty to understanding score | frontend/src/lib/understanding-profile.ts | Active | Static multipliers | UNVALIDATED | Medium |
| PR-D-004 | Intelligence overlay caps | signal_details + provenance | Heuristic overlay adjustments | Priority score adjustment | frontend/src/lib/optime-v2-engine.ts | Active | Cap/delta heuristics | UNVALIDATED | High |
| PR-D-005 | Distance step points | distance values | Heuristic translation | Score adjustment | frontend/src/lib/optime-v2-engine.ts | Active | Step-function bands | UNVALIDATED | Medium |
| PR-D-006 | Synthetic benchmark multipliers | Persona benchmark profiles | Simulation-only advisor proxy | Benchmark-only score | scripts/run_human_advisor_benchmark.cjs | Active non-runtime | Synthetic test logic | UNVALIDATED | Medium |

Explicit UNKNOWN/UNMAPPED entries (implemented code paths not currently invoked by active runtime recommendation path):

- PR-U-001: weightedTotal helper
- PR-U-002: buildMatchQualityResult helper
- PR-U-003: buildIntelligenceReport helper
- PR-U-004: collectHardRejectionReasons helper
- PR-U-005: hasMandatoryMismatch helper

## AUTHORITY MODEL A/B/C/D

- Level A: hard requirements only from explicit user non-negotiable inputs or binding authoritative safety constraints.
- Level B: validated professional rules that can support OUR_RECOMMENDATION but are not automatic MUST unless independently hard.
- Level C: evidence-informed preferences for OUR_RECOMMENDATION/NICE_TO_HAVE only.
- Level D: unvalidated/internal/synthetic heuristics; cannot produce professional MUST/OUR_RECOMMENDATION as validated fact.

## WHO CAN VALIDATE

Accepted validators by class:

- AUTHORITATIVE SOURCE VALIDATION: regulator/government/statutory/licensing/official public-health authority.
- PROFESSIONAL VALIDATION: independent qualified professional, documented guideline/consensus, independent review.
- OUTCOME VALIDATION: real-world outcome methodology with traceable cohort and metrics.
- INTERNAL REVIEW ONLY: OPTIME internal, AI agents, synthetic tests.

Governance constraints:

- Internal review alone cannot upgrade unsupported rules to Level A or B.
- AI cannot self-validate professional rules.

## RULE REGISTRY STATUS

Registry: database/professional_rule_registry.json

- Rule records: 23
- Unknown/unmapped records: 5
- Hardcoded weights audited: 9
- Canonical output classes used: MUST, OUR_RECOMMENDATION, NICE_TO_HAVE, CLARIFY, INVESTIGATE, NO_ACTION

## MUST GOVERNANCE

Policy implemented:

- MUST may originate only from user explicit non-negotiable constraints or Level A rules.
- Validator fails if MUST appears in Level B/C/D rule entries.

Current status: PASS

## OUR RECOMMENDATION GOVERNANCE

Policy implemented:

- OUR_RECOMMENDATION may originate from Level B or Level C (with transparent confidence/evidence).
- Validator fails if Level D independently emits OUR_RECOMMENDATION.

Current status: PASS

## NICE TO HAVE GOVERNANCE

Policy implemented:

- NICE_TO_HAVE may originate from non-MUST user preferences or low-impact Level C preferences.
- NICE_TO_HAVE must not hard-exclude.

Current status: PASS

## ANTI-HALLUCINATION POLICY

Canonical rule:

- If evidence is insufficient for professional interpretation, do not invent one.
- Allowed outputs for insufficient evidence: CLARIFY, INVESTIGATE, UNKNOWN, NO_ACTION.
- UNKNOWN must not be silently converted to NO/zero professional claim.

Mechanical enforcement in validator:

- Scans for unsupported UNKNOWN-to-negative conversion patterns.
- Requires explicit UNKNOWN confidence-only handling in active recommendation code.

Current status: PASS

## HARDCODED WEIGHTS AUDIT

Material hardcoded weights/heuristics inventory:

- Persona weights (UNVALIDATED)
- Understanding domain weights (UNVALIDATED)
- Understanding critical multipliers (UNVALIDATED)
- Distance point bands (UNVALIDATED)
- Intelligence overlay caps (UNVALIDATED)
- Confidence penalty by missing-intelligence count (UNVALIDATED)

Summary:

- UNVALIDATED MATERIAL WEIGHTS: 6
- No unsupported material weight is labeled professionally validated.

## TRACEABILITY MODEL

Required trace path model established:

- USER ANSWER
- RULE_ID
- INTERPRETATION
- AUTHORITY LEVEL
- SOURCE
- OUTPUT CLASS
- DECISION EFFECT

Mechanics:

- Rule identity and evidence are canonicalized in database/professional_rule_registry.json.
- Recommendation knowledge usage is trace-logged by backend recommendation_guard_decision.
- Recommendation score/evidence trace API remains available via recommendation_score_trace.

Current status: PARTIAL

Reason:

- Registry path is complete for governed rule metadata.
- Full per-recommendation runtime attachment of RULE_ID for every UI decision artifact is not yet implemented.

## MECHANICAL VALIDATION

Validator: scripts/validate_professional_rule_governance.py

Gates fail on:

- MUST from unsupported Level B/C/D logic
- Level D hard exclusion
- Level D independent OUR_RECOMMENDATION
- Missing RULE_ID
- Active Level A/B without traceable source evidence
- AI/internal-only as sole validator for active Level A/B
- Silent UNKNOWN-to-negative conversion patterns
- Unsupported weight labeled validated
- Duplicate/conflicting RULE_ID
- Report/registry count mismatch

Current status: PASS

## EXTERNAL VALIDATION STATUS

- Level A/B rules with external/professional validation still required: 5
- Mechanical pass does not equal professional validity.

Current status: PARTIAL

## REAL-WORLD VALIDATION STATUS

- Outcome validation remains separate and cannot be substituted by synthetic tests.
- Professional rule validity is not promoted solely from synthetic mechanics.

Current status: PARTIAL

## KNOWN UNKNOWNS

- Five implemented helper paths are currently UNKNOWN/UNMAPPED in active runtime invocation.
- Several Level D heuristics are materially influential and remain unvalidated.
- Full rule-level runtime attachment to every user-facing recommendation action is not complete.

## BLOCKERS

- External professional validation for B-level clinical interpretation mappings not yet attached.
- Authoritative external review evidence for all A-level clinical hard constraints needs formal sign-off artifacts.

## NEXT RECOMMENDED PHASE

- Phase 3 should focus on runtime RULE_ID propagation and full per-recommendation trace payload linkage, after external validation artifacts for A/B governance are attached.

Do not execute Phase 3 in this phase.
