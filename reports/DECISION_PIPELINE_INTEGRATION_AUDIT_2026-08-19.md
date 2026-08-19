# OPTIME Nursing Decision Pipeline Integration Audit — 2026-08-19

## Scope

Audit the live recommendation path end to end. The purpose is to distinguish components that exist in the repository from components that actually influence the production Top-5.

## Executive finding

The production results page calls the backend `/decision-engine/recommendations` path directly. It does **not** execute the richer `frontend/src/lib/optime-v2-engine.ts` ranking engine. As a result, several months of Human Intelligence, lifestyle/persona logic, adaptive-question logic, facility intelligence, outcomes learning, and Knowledge Fabric infrastructure are not systematically participating in the production rank order.

This is an integration failure, not a missing-feature problem.

## Runtime truth

| Layer | Exists | Captures useful information | Consumed by production recommendation rank | Status |
|---|---:|---:|---:|---|
| Nevada canonical universe | YES | YES | YES | CONNECTED |
| Nevada HCQC / ALiS regulatory history | YES | YES | YES | CONNECTED |
| CMS / federal nursing evidence | YES | YES | YES where applicable | CONNECTED |
| Facility parameter/evidence table | YES | YES | YES | CONNECTED |
| Basic patient needs: ADL, medication, memory, rehab | YES | YES | YES | CONNECTED |
| HumanIntelligenceV2 raw questionnaire | YES | YES | PARTIAL | SEVERELY UNDERUSED |
| Widow / bereavement / recent loss | YES | YES | NO material rank effect | DISCONNECTED |
| Loneliness / social-isolation risk | YES | YES | NO material rank effect | DISCONNECTED |
| Community-size / privacy / personality preference | YES | YES | NO | DISCONNECTED |
| Independence priorities | YES | YES | NO material rank effect | DISCONNECTED |
| Human Intelligence scoring outputs | YES | YES | NO direct rank use | DISCONNECTED |
| Adaptive questions / information gain | YES | YES | NO decision-readiness gate | DISCONNECTED |
| Facility Intelligence Profile: social energy / engagement / activities / reputation | YES | YES | NO systematic Nevada rank use | DISCONNECTED |
| Knowledge Fabric knowledge objects | YES schema | potentially | NO direct recommendation query | DISCONNECTED |
| `recommendation_eligible` knowledge gate | YES schema | YES | NO runtime consumer found | DISCONNECTED |
| 20 Knowledge Centers | YES governance/research package | YES | NO normalized rank bridge | DISCONNECTED |
| RecommendationVerificationAudit | YES schema | YES | NO production write path found | DISCONNECTED |
| ResidentOutcome learning | YES schema | YES | NO rank feedback loop found | DISCONNECTED |
| Rich frontend OPTIME V2 engine | YES | YES | NO on current Results page | ORPHANED / LEGACY PARALLEL ENGINE |

## Concrete evidence from the 84-year-old Las Vegas test

Persona: 84, recently widowed, mentally alert, mobile, needs help with bathing, dressing, meals and medication.

Production correctly selected Assisted Living/RFG rather than SNF. However the five recommendations were all 6–10 bed residential group homes and were ordered primarily by regulatory history. The production engine did not materially reason over the fact that the person was recently widowed, socially vulnerable, independent-minded, or potentially better suited to a larger social community.

This is consistent with the backend code path: the active patient-needs mapper principally turns the questionnaire into facility capability parameters. By contrast, the questionnaire already contains fields including `widowStatus`, `lossTiming`, `socialActivityChangeSinceLoss`, `griefSupportInterest`, `communitySizePreference`, `privacyImportance`, `abilityToLeaveIndependently`, `lonelinessRisk`, `socialIsolationConcern`, `transition_success_probability` and related signals.

## Duplicate-engine problem

Two materially different decision systems exist:

1. **Backend production decision engine** — evidence-governed, canonical, strong on care-setting and regulatory truth, but narrow on person/lifestyle/transition fit.
2. **Frontend OPTIME V2 engine** — contains personas, social/lifestyle/family/cultural/future-care logic, hard rejection rules, match-quality tiers and Decision Intelligence narratives, but historically used heuristic/synthetic facility signals in places and is no longer the production ranking path.

The correct fix is **not** to switch production back to the old frontend V2 engine. The correct fix is to migrate its valid human-decision semantics into the governed backend, using only evidence-backed facility signals and UNKNOWN when evidence is absent.

## Required target pipeline

Every material recommendation signal must have this trace:

`COLLECTED -> VALIDATED -> KNOWLEDGE / RULE -> PATIENT SIGNAL -> FACILITY SIGNAL -> DECISION DIMENSION -> RANK EFFECT -> EXPLANATION -> OUTCOME LEARNING`

A signal that stops before `RANK EFFECT` is not integrated.

## Integration contracts to enforce

### Human Intelligence contract

Production must consume, at minimum:

- social interaction need
- loneliness/social-isolation risk
- bereavement and transition risk
- community-size preference
- privacy / introvert-extrovert preference
- independence priorities
- family involvement / visit rhythm
- cultural / language / religious requirements
- food requirements
- future-care / avoid-future-moves preference
- geographic/family access constraints

Explicit user data is authoritative. Inference must carry provenance and confidence. UNKNOWN remains UNKNOWN.

### Facility person-fit contract

Production ranking must distinguish facility care capability from facility living environment. Evidence-backed facility dimensions should include, when available:

- licensed/verified capacity and resulting community-size band
- activity / social programming evidence
- social-energy / community-engagement evidence
- apartment/private-space evidence
- transportation / independent-exit evidence
- dining and dietary evidence
- family visiting / hosting evidence
- cultural/language/religious evidence
- care-continuum evidence
- regulatory and clinical evidence

No directory rating or marketing statement becomes licensing truth.

### Decision-readiness contract

If a material person-fit dimension can change the Top-5 and the user has not supplied it, the system must surface an adaptive clarification rather than silently break the tie on an unrelated dimension.

Example: for a recently widowed, cognitively intact person choosing between a 6-bed group home and a 150-bed senior community, community-style preference is decision-relevant. If unknown, the system must explicitly flag the uncertainty.

### Knowledge Fabric contract

Knowledge objects may affect recommendations only when:

- active
- verified/eligible under governance
- `recommendation_eligible = 1`
- not expired/stale beyond policy
- conflict state permits use
- evidence provenance is retained

Every knowledge object used must be emitted in the recommendation audit trace.

### Outcome-learning contract

Resident outcomes must not silently change weights. Any learning loop must be versioned, measurable, auditable, protected against sparse-data overfitting, and reversible.

## First implementation tranche

1. Add a governed backend Human Intelligence runtime context.
2. Add decision-readiness/adaptive clarification for high-impact missing person-fit dimensions.
3. Add evidence-backed community-size signal from Nevada official bed count; do not infer social quality from size alone.
4. Add a separate `human_person_fit` dimension to the rank/explanation contract.
5. Preserve care-setting, licensing, regulatory and CMS truth as independent dimensions.
6. Add tests using the 84-year-old widow case proving that bereavement/community-style information reaches the decision context and cannot disappear silently.
7. Add a CI integration matrix that fails when a declared decision layer has no runtime consumer.

## Later tranches

- Governed bridge for Knowledge Fabric recommendation-eligible objects.
- Nevada facility lifestyle/social enrichment with provenance.
- Adaptive question selection based on expected rank information gain.
- RecommendationVerificationAudit persistence.
- Outcome-learning feedback loop with versioned governance.
- Retire or clearly label the parallel frontend ranking engine after valid semantics are migrated.

## Non-negotiable rules

- No synthetic facility facts.
- No inferred care classification where official evidence exists.
- UNKNOWN stays UNKNOWN.
- Research knowledge changes decision rules only through an explicit governed rule/evidence path.
- Person fit and clinical/regulatory fit remain separate and explainable.
- A successful CI run is not sufficient; production E2E must prove the signal changed the runtime decision context.