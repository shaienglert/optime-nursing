# OPTIME End-to-End Decision Simulation

## Audit conclusion

**Not defensible yet**

The current production engine does not select one base-case winner. It returns five provider organizations at **Joint #1**. Each has the same eligibility state (`POTENTIALLY_ELIGIBLE`), patient match score (60.0), evidence confidence (19.78), capability-depth score (81.48), and practical-fit score (100.0). Quality/safety, staffing, and patient-relevant outcomes are unknown for all five. The displayed order is alphabetical only.

The result therefore cannot prove why one facility wins over another. It proves that current evidence and rules cannot distinguish the first five and that a family recommendation must wait for targeted verification.

## Governance and run boundary

- Classification: B, Implementation Completion (audit artifacts only).
- Relevant principles: PR-002, PR-003, PR-005, PR-006, PR-007, PR-009.
- Principle alteration: No.
- Owner approval required: No.
- Production code, ranking logic, canonical parameters, APIs, and production data changed: No.
- Internet crawl, facility profile generation, snapshot rebuild, or global cache rebuild: None performed.
- Production decision result cache: explicitly disabled for each fresh direct run.
- Active runtime version: `0c81e52c7136390c`.
- Active runtime timestamp: `2026-07-21T15:01:12+00:00`.
- Base response time: 4,667.67 ms in a fresh process.
- Candidates evaluated and ranked: 11,090.
- Eligibility counts: 1,057 `POTENTIALLY_ELIGIBLE`; 10,033 `INSUFFICIENT_EVIDENCE`; 0 `INELIGIBLE`; 0 excluded.
- Live runtime after the run: clean, cache swap count 1, no rebuild success event, no error.

## 1. Case received by the engine

### Structured family answers

| Input | Value | Engine treatment |
| --- | --- | --- |
| Relationship | Mom | Context only |
| Age group | 82 | Context only; no canonical need generated |
| Assistance | Bathing and dressing assistance | ADL support HIGH; transfer assistance initially MEDIUM |
| Mobility | Uses a walker | Stored but not mapped to a separate need |
| Memory | No current concerns | Does not itself add a need |
| Post-hospital rehabilitation | Yes | PT HIGH, OT HIGH, speech MEDIUM, stroke/neuro HIGH |
| Diet | Medically required gluten-free | Gluten-free PREFERENCE |
| Spoken language | Hebrew | Languages MEDIUM |
| Payment | Private pay | Stored but not mapped to a payer requirement |
| Budget | 0 | Correctly treated as unspecified; no affordability threshold |
| Urgency | Within 30 days | Stored but not mapped to availability/admission-date need |

### Natural-language case

> Looking for care for mother, age 82, after a recent stroke. She uses a walker, needs help with bathing and dressing, medication management, and transfer assistance. Physical therapy and occupational therapy are required. Speech therapy is preferred if appropriate for stroke recovery. She is mentally alert and has no dementia. She requires a medically necessary gluten-free diet and prefers Hebrew-speaking support. Miami-Dade is preferred. Private pay, budget not specified, and move needed soon.

### Effective mapped needs

The engine produced no `REQUIRED` needs. It mapped seven needs as `HIGH`, two as `MEDIUM`, and two as `PREFERENCE`:

| Family meaning | Canonical parameter | Effective level | Desired value | Audit note |
| --- | --- | --- | --- | --- |
| Bathing and dressing help | `adl_support` | HIGH | YES | Preserved |
| Medication management | `medication_support` | HIGH | YES | Preserved |
| Occupational therapy required | `ot` | HIGH | YES | “Required” is not preserved as REQUIRED |
| Recent-stroke rehabilitation | `post_stroke_neuro_evidence` | HIGH | YES | Preserved as HIGH |
| Physical therapy required | `pt` | HIGH | YES | “Required” is not preserved as REQUIRED |
| Speech therapy preferred | `speech_therapy` | HIGH | YES | Promoted from preference to HIGH by keyword matching |
| Transfer assistance | `transfer_assistance` | HIGH | YES | Natural language raises questionnaire MEDIUM to HIGH |
| Hebrew preferred | `languages` | MEDIUM | `hebrew` | Preference is represented as MEDIUM |
| Medicare acceptance | `medicare_attributes` | MEDIUM | YES | Governed default despite private-pay input |
| Medically required gluten-free diet | `gluten_free` | PREFERENCE | YES | Downgraded from medically required to preference |
| No dementia | `memory_care` | PREFERENCE | NO | Absence preference; generic dementia-positive rule suppressed |

Geography is separately mapped to exact city `MIAMI`, not Miami-Dade County. Budget is unspecified. No deal-breaker is generated. Age, walker use, private pay, urgency, current availability, admission date, and county radius do not become effective needs. Other family fields are unknown because they were not supplied; no missing answer was invented.

## 2. Base top five

| Display position | Provider | Canonical ID | CMS CCN | Eligibility | Match | Confidence | Price |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| Joint #1 | 24/7 NURSING CARE INC | `NPI-1962821785` | None | POTENTIALLY_ELIGIBLE | 60.0 | 19.78 | UNKNOWN |
| Joint #1 | A TOUCH OF KINDNESS HOME CARE INC | `NPI-1205485182` | None | POTENTIALLY_ELIGIBLE | 60.0 | 19.78 | UNKNOWN |
| Joint #1 | ABACA NURSING CARE INC | `NPI-1932782919` | None | POTENTIALLY_ELIGIBLE | 60.0 | 19.78 | UNKNOWN |
| Joint #1 | ABSOLUTE HEALTH CARE NOW INC | `NPI-1316729890` | None | POTENTIALLY_ELIGIBLE | 60.0 | 19.78 | UNKNOWN |
| Joint #1 | ADL FAMILYCARE SERVICES INC. | `NPI-1487211645` | None | POTENTIALLY_ELIGIBLE | 60.0 | 19.78 | UNKNOWN |

All five IDs and names match the active canonical index. They are NPI-identified provider organizations and have no CMS CCN in the canonical record. The result does not establish that any is a residential nursing facility, licensed for the requested setting, currently admitting, affordable, safe, or able to deliver the required rehabilitation plan.

### Why they are tied

For every provider:

- The only matched case need is `adl_support=YES`.
- That match comes from NPPES taxonomy, classified by the engine as `TAXONOMY_INFERRED` with multiplier 0.55.
- Six HIGH needs are UNKNOWN: medication support, OT, stroke/neuro rehabilitation, PT, speech therapy, and transfer assistance.
- There are no verified gaps.
- Exact-city matching adds 5 points.
- Safety, staffing, and outcome dimensions are wholly unknown.
- Capability depth is 81.48 from the same SERVICE-scoped ADL taxonomy match.
- Practical fit is 100 because Miami is the only known practical-fit comparison; language, Medicare, and gluten-free support are unknown.

The exact score calculation is:

`known ADL weight = 3.0`

`taxonomy-adjusted match = 3.0 × 0.55 = 1.65`

`evidence discount = 3.0 × (1 - 0.55) = 1.35`

`known-evidence match = 1.65 / (1.65 + 0 + 1.35) × 100 = 55.0`

`final patient match = 55.0 + 5.0 exact-Miami bonus = 60.0`

The four adjacent comparator decisions are all `true_tie`. Equal dimensions are patient match, capability depth, and practical fit. Unknown dimensions are quality/safety, staffing, and patient-relevant outcomes. Alphabetical name order is used only for deterministic display and does not create rank superiority.

## 3. Facility evidence and ranking explanation

### 24/7 NURSING CARE INC

- Canonical identity: `NPI-1962821785`; no CMS CCN.
- Selected case evidence: NPPES taxonomy `In Home Supportive Care`, evidence date 2014-04-09, supports ADL at taxonomy/proxy level only.
- Other evidence in its table: NPPES `Nursing Care` taxonomy supports `nursing_24_7` and `skilled_nursing_capabilities`, but neither is an effective mapped base need. The evidence explicitly says direct nurse modality remains unverified and is not licensure proof.
- Contradictions: none recorded.
- Staleness: no formal stale flag; the selected underlying taxonomy evidence is dated 2014-04-09 and therefore requires current confirmation.
- Why first: it is not uniquely first. It is alphabetically first among five true ties.

### A TOUCH OF KINDNESS HOME CARE INC

- Canonical identity: `NPI-1205485182`; no CMS CCN.
- Selected case evidence: NPPES `In Home Supportive Care`, evidence date 2024-06-12, supports ADL at taxonomy/proxy level only.
- Additional NPPES `Nursing Care` taxonomy exists for nursing capability, but is not licensure or direct capability proof and does not differentiate the base score.
- Contradictions/stale flags: none recorded.
- Why below the displayed first: no substantive reason. It is a true tie; alphabetic display order only. Missing facts could reverse or break the tie.

### ABACA NURSING CARE INC

- Canonical identity: `NPI-1932782919`; no CMS CCN.
- Selected case evidence: NPPES `In Home Supportive Care`, evidence date 2024-03-08, supports ADL at taxonomy/proxy level only.
- Additional NPPES `Nursing Care` taxonomy does not prove current direct capability or licensure and has no differentiating score effect.
- Contradictions/stale flags: none recorded.
- Why below the provider above: no substantive reason; true tie and alphabetic display order.

### ABSOLUTE HEALTH CARE NOW INC

- Canonical identity: `NPI-1316729890`; no CMS CCN.
- Selected case evidence: NPPES `In Home Supportive Care`, evidence date 2023-10-18, supports ADL at taxonomy/proxy level only.
- Additional NPPES non-emergency medical transport taxonomy exists but transportation was not mapped from the family case and does not affect ordering.
- Contradictions/stale flags: none recorded.
- Why below the provider above: no substantive reason; true tie and alphabetic display order.

### ADL FAMILYCARE SERVICES INC.

- Canonical identity: `NPI-1487211645`; no CMS CCN.
- Selected case evidence: NPPES `Homemaker`, evidence date 2026-05-19, supports ADL at taxonomy/proxy level only.
- This is its only evidence-bearing row in the selected parameter table.
- Contradictions/stale flags: none recorded.
- Why below the provider above: no substantive reason; true tie and alphabetic display order.

Across all five, there is no regulatory-verified, direct facility-verified, or facility-reported evidence supporting a mapped family need. “Documented” evidence consists only of NPPES taxonomy declarations. No selected conflict is recorded. Absence of a conflict is not proof of capability.

## 4. Full decision trace

The companion CSV contains one row per effective family factor and provider. The material behavior is summarized here:

| Factor | Eligibility effect | Ranking effect | UNKNOWN treatment |
| --- | --- | --- | --- |
| ADL support HIGH | One taxonomy-supported critical match makes each provider potentially eligible | 55 known-evidence points before geography | Not unknown |
| Medication support HIGH | UNKNOWN critical need | 0; excluded from score denominator | Neutral |
| OT HIGH | UNKNOWN critical need | 0; excluded from score denominator | Neutral |
| Stroke/neuro rehabilitation HIGH | UNKNOWN critical need | 0; excluded from score denominator | Neutral |
| PT HIGH | UNKNOWN critical need | 0; excluded from score denominator | Neutral |
| Speech therapy HIGH | UNKNOWN critical need | 0; excluded from score denominator | Neutral |
| Transfer assistance HIGH | UNKNOWN critical need | 0; excluded from score denominator | Neutral |
| Hebrew MEDIUM | No critical eligibility effect | 0; practical-fit unknown | Neutral |
| Medicare MEDIUM | No critical eligibility effect | 0; practical-fit unknown | Neutral |
| Gluten-free PREFERENCE | No critical eligibility effect | 0; practical-fit unknown | Neutral |
| No memory care PREFERENCE | No critical eligibility effect | 0 | Neutral |
| Exact Miami location | No eligibility effect | +5 to every top-five match score; practical fit 100 | Not unknown |

Parameters ignored or ineffective include age, walker use, relationship, private-pay selection, urgency, county preference, current availability, earliest admission, and all registry parameters outside the recommendation subset. `nursing_24_7`, `skilled_nursing_capabilities`, and transportation have evidence for some providers but no effect because they are not effective base needs. Safety, staffing, outcomes, rehabilitation capability, language, diet, pricing, payer compatibility, and availability are unavailable across the compared providers and cannot break the tie.

## 5. Pricing and budget

Base budget remains unspecified. `budget=0` causes no `published_rates` need and no affordability threshold. Every top-five `published_rates` value is `UNKNOWN` with source `Not verified`. No provider is penalized for missing price, and none can be described as affordable.

Private-pay intent is not the same as verified payment compatibility, and neither is affordability. Before a final decision, the family must verify current monthly charges, care-level add-ons, therapy charges, medication-management fees, deposits, and whether the provider supplies the relevant residential setting. Supplying a budget currently adds a preference for known rates; it does not implement a numeric maximum-price exclusion.

## 6. Engineering reproduction

1. Build the needs profile with `build_patient_needs_profile(questionnaire_state, natural_language_query)`.
2. Load all active canonical IDs and personalized parameter ordering from runtime `0c81e52c7136390c`.
3. For each of 11,090 candidates, evaluate needs with current parameter rows and classify eligibility.
4. For each known match, apply requirement weight and evidence multiplier. Apply verified gaps at full requirement weight. Exclude UNKNOWN from both known numerator and denominator.
5. Add the exact-city bonus of 5 after calculating known-evidence match.
6. Sort by eligibility, patient match, quality/safety, staffing, capability depth, outcomes, practical fit, then name.
7. Apply comparator thresholds. When all available dimensions are within thresholds and the rest are unknown, label a true tie and retain name only as deterministic display order.

For each top provider: `3 × 0.55 = 1.65` matched, `3 × 0.45 = 1.35` discounted, no known gaps, 55.0 known-evidence score, +5 Miami, final 60.0. Evidence certainty is `3 / 27 × 100 = 11.11`. Two of five secondary dimensions are available, so coverage is 40%; confidence is `11.11 × 0.7 + 40 × 0.3 = 19.78`.

## 7. Challenge to the result

- Weakest evidence supporting Joint #1: an NPPES taxonomy declaration used as a proxy for ADL capability; it is explicitly not licensure proof.
- Most important UNKNOWN: whether the provider can deliver the post-stroke rehabilitation plan (PT, OT, speech as appropriate, and neuro/stroke support). Medication and transfer support are also critical.
- Easiest fact to break the tie: direct, current, authoritative evidence that one provider can or cannot deliver any HIGH need. Safety, staffing, outcomes, residential setting, availability, or current price could also materially change the decision.
- Competitor most likely to overtake: indeterminate among the other four tied providers; the current evidence supports no defensible prediction.
- Unverified claims: all selected capability support is taxonomy-inferred. No top provider has direct or regulatory proof for a mapped clinical need.
- Important source age: the first displayed provider’s underlying selected taxonomy is dated 2014-04-09. The runtime verification timestamp does not make the underlying declaration current capability proof.
- Gap strength: zero. The top five are true ties.
- Family defense: no. Presenting the alphabetically first provider as a first recommendation would overstate the evidence.

**Not defensible yet**

## 8. Validation

- Five names and IDs matched the active canonical index: confirmed.
- CCNs: none present for the base top five; none invented.
- Evidence and prices: copied from current active parameter tables; no missing fact filled.
- Budget: unspecified in base; no affordability threshold used.
- UNKNOWN: retained as UNKNOWN and neutral, never converted to NO.
- Family and engineering conclusions: both state that there is no unique winner.
- Sensitivities: each run in a fresh process from an independent copy of the base input.
- Source mutations: no code, ranking, canonical parameter, API, facility evidence, or production data edits.
- External work: no internet crawl, profile rebuild, snapshot rebuild, or global cache rebuild.

One disclosed local side effect occurred before the clean simulation: an initial attempt through the production API invoked unified-case persistence and created/updated local patient-case records. That contaminated API result was discarded. The reported runs call the production decision function directly in fresh processes and do not use those records. No facility, evidence, ranking, parameter, or snapshot data was changed.