# Texas Recommendation Coverage Matrix v1

Status: RESEARCH / DATA-COVERAGE CANON — NOT PRODUCTION SCORING

Purpose: map the approved Resident–Senior Living Success Factors Canon against data that OPTIME Nursing can currently source or has explicitly designed for, and identify what still requires resident/family input, provider verification, Texas-specific ingestion, or future outcome learning.

## Ground Rules

- Coverage is not predictive weight and is not model accuracy.
- A factor marked AUTO-PARTIAL may support a recommendation but cannot be treated as fully known.
- UNKNOWN never becomes match or mismatch without evidence.
- Provider marketing claims are not equivalent to verified capability.
- CMS data apply to Medicare/Medicaid-certified nursing facilities/SNFs; they do not provide equivalent coverage for Texas assisted-living facilities.
- The repository currently documents a CMS ingestion strategy but does not contain a Texas HHSC/TULIP ingestion implementation. Texas ALF regulatory data is therefore SOURCE-IDENTIFIED / NOT-YET-INTEGRATED.

## Current Source Reality

### CMS nursing-facility data already designed in OPTIME
The existing CMS source specifications identify Provider Information, PBJ staffing, Quality Measures, Inspections/Deficiencies, Ownership, and Penalties as canonical source families keyed by CCN. They expose facility identity/location/beds/ratings, RN/LPN/CNA staffing hours, turnover indicators, quality measures, deficiencies and severity, and enforcement history.

### Repository intelligence stores
The repository contains large community intelligence stores for workforce, social, cultural, management, outcome, trend, signal-graph, deep-intelligence, and confidence data. Their existence is useful infrastructure, but file presence alone is not treated as verified Texas coverage or as authoritative evidence for a particular factor.

### Texas Assisted Living
No Texas/HHSC/TULIP ingestion path was found in the current repository search. Until implemented and verified, Texas ALF regulatory information must be treated as an external source opportunity rather than current prepared knowledge.

## Coverage Status Taxonomy

- **AUTO-KNOWN** — facility-side fact can be obtained from a prepared authoritative data source when the applicable facility is in source scope.
- **AUTO-PARTIAL** — useful evidence exists, but it does not fully establish the fit construct.
- **FAMILY/RESIDENT INPUT** — cannot be responsibly inferred from provider data.
- **PROVIDER VERIFY** — requires direct facility evidence or validated resident-experience evidence.
- **SOURCE-IDENTIFIED / NOT-INTEGRATED** — authoritative source exists, but current OPTIME repository does not yet ingest it for Texas.
- **OUTCOME-LEARNING** — cannot be validated adequately before placement; should be learned prospectively.
- **RESEARCH-ONLY** — do not operationally weight yet.

## 16-Factor Coverage Matrix

| Canonical factor | Influence | Resident / family side | Nursing-facility facility side today | Texas ALF facility side today | Current coverage judgment | What remains unknown |
| --- | --- | --- | --- | --- | --- | --- |
| Clinical Capability Fit | HARD GATE | diagnosis/care goals only as necessary; ADL, medication, transfers, dementia, rehab, diet and other required supports | Provider type plus CMS quality/inspection evidence can support safety/care context, but CMS does not by itself prove every specialty service is available | licensing/regulatory source must be integrated; detailed capabilities require provider verification | AUTO-PARTIAL + PROVIDER VERIFY | exact service availability, admission criteria, acuity limits, current capability |
| Decision Participation / Move Voluntariness | HIGH | resident/family confirmation | no public facility dataset establishes this | same | FAMILY/RESIDENT INPUT | whether resident understands, agrees, feels coerced or participated |
| Transition Preparation / Expectation Realism | HIGH | urgency, prior visits, expectations, understanding of daily life | provider transition/orientation program requires verification | provider transition/orientation program requires verification | FAMILY INPUT + PROVIDER VERIFY | expectation gaps and quality of actual pre-move preparation |
| Functional & Cognitive Care-Needs Fit | HIGH / HARD GATE where necessary | ADLs, mobility, cognition, behavior, transfer needs, rehab goals | CMS provides facility-level outcomes and staffing context; resident-specific capability still requires verified service limits | Texas ALF capability requires state/provider evidence | AUTO-PARTIAL + FAMILY INPUT + PROVIDER VERIFY | whether this specific person can be safely retained as needs evolve |
| Autonomy / Choice Fit | HIGH | which choices matter: schedule, meals, bathing, activities, privacy, visitors | not established by CMS | not established by HHSC licensing alone | FAMILY INPUT + PROVIDER VERIFY | real daily autonomy rather than policy/marketing language |
| Preference Congruence / Person-Centred Daily Life | MEDIUM-HIGH | routines, food, privacy, sleep, activities, religion/culture only as legitimate daily-life need | public CMS data insufficient | regulatory data insufficient | FAMILY INPUT + PROVIDER VERIFY | whether preferences are actually honored in practice |
| Resident–Staff Relationship Capability | HIGH | desired interaction/support style | PBJ turnover/staffing and administrator turnover are useful proxies, not direct relationship quality | no PBJ-equivalent currently integrated | AUTO-PARTIAL for NH; PROVIDER/EXPERIENCE VERIFY | whether staff know residents, continuity at unit level, responsiveness/respect |
| Family Connection / Visitability | MEDIUM-HIGH | desired visit frequency, family locations, transport constraints | provider location is available from CMS and travel can be derived | location becomes available once Texas facility universe is ingested | AUTO-PARTIAL + FAMILY INPUT | actual practical visitability, visiting rules, family capacity |
| Family–Staff Communication Expectations | MEDIUM-HIGH | desired reporting frequency, involvement, escalation expectations | no CMS field directly establishes fit | no regulatory field alone establishes fit | FAMILY INPUT + PROVIDER VERIFY | actual communication process and responsiveness |
| Social Connection / Engagement Fit | HIGH | social style, desired activities, desired level of interaction | CMS does not provide rich person-specific engagement data; repository has social intelligence infrastructure whose Texas provenance must be validated | same plus Texas provider enrichment required | PROVIDER VERIFY / DATA-PROVENANCE AUDIT | actual participation, peer fit, activity relevance and accessibility |
| Social Climate | HIGH | desired social environment | no authoritative CMS social-cohesion measure | no authoritative Texas licensing social-cohesion measure | PROVIDER/RESIDENT-EXPERIENCE VERIFY | cohesion, conflict, belonging, loneliness risk |
| Sense-of-Home / Privacy / Personalization Fit | MEDIUM-HIGH | privacy, room, belongings, outdoor/common space, personalization priorities | CMS provider info may describe capacity, not lived home-like experience | Texas facility data/provider evidence required | FAMILY INPUT + PROVIDER VERIFY | actual room options, personalization rules, environment experience |
| Staffing Stability / Consistency | HIGH | usually no user input needed unless continuity is a stated MUST | CMS/PBJ supports nurse turnover; CMS also reports administrator departures/turnover-related measures | no equivalent source integrated today | AUTO-KNOWN/PARTIAL for NH; SOURCE-IDENTIFIED GAP for ALF | unit-level continuity, agency dependence, manager stability outside CMS scope |
| Staffing Sufficiency / Skill Mix | HIGH | acuity determines required staffing capability | CMS/PBJ provides RN and total nurse hours/resident-day, weekend staffing and staffing ratings | Texas ALF staffing evidence is not currently integrated and is not equivalent to PBJ | AUTO-KNOWN for CMS measures; SOURCE-IDENTIFIED GAP for ALF | shift/unit-specific staffing and specialty competence |
| Verified Facility Quality / Safety History | HARD GATE or HIGH | family may define unacceptable events but should not supply facility facts | CMS inspections, deficiencies, penalties, quality measures, complaints/surveys and claims/MDS outcome measures provide strong facility evidence | Texas HHSC/TULIP licensing/inspection/enforcement source needs ingestion and normalization | AUTO-KNOWN for applicable NH; SOURCE-IDENTIFIED / NOT-INTEGRATED for ALF | non-public incident detail, current changes after last publication |
| Multiple-Relocation / Continuum-of-Care Risk | MEDIUM-HIGH | expected future needs; couple separation constraints | provider type and history can inform context but do not prove future retention capability | provider continuum/service structure must be verified | AUTO-PARTIAL + FAMILY INPUT + PROVIDER VERIFY | admission/discharge thresholds, escalation options, likelihood of forced transfer |

## What OPTIME Can Know Before Asking the Family

For a CMS-certified nursing facility, OPTIME can potentially know substantial **facility-side truth** before the first user question:

- identity, address and certified-bed capacity
- ownership context
- overall/staffing/inspection/QM ratings as descriptive signals
- RN/total nurse staffing levels and weekend staffing
- nursing staff turnover and administrator turnover-related signals where reported
- inspection/deficiency history and severity
- penalties/payment denials
- MDS/claims quality outcomes where published

This materially informs only a subset of the 16 fit constructs. It is strongest for **Safety/Quality, Staffing Sufficiency, Staffing Stability, and parts of Clinical/Functional Capability context**. It is weak for **Autonomy, Social Climate, Resident–Staff Relationship quality, Daily-Life Preference Fit, Family Communication, Transition Preparedness, and Sense of Home**.

Therefore the correct product behavior is not to ask the family for information the government already provides, and not to pretend public data can answer human-fit questions that it cannot measure.

## Operational Coverage Count — Not a Weight

The following is a simple factor-coverage inventory, not a prediction score:

- 16 canonical factors total.
- 4 factors have strong authoritative facility-side public evidence for CMS nursing facilities: **Verified Quality/Safety, Staffing Sufficiency, Staffing Stability, facility identity/location context used in Visitability**.
- 4 additional factors have useful but incomplete public/provider-side evidence: **Clinical Capability, Functional/Cognitive Care-Needs Fit, Resident–Staff Relationship proxies, Continuum-of-Care context**.
- The remaining factors require resident/family preference/transition information and/or verified provider/resident-experience evidence.
- For Texas Assisted Living, current repository coverage is materially lower because no HHSC/TULIP ingestion implementation was found. Do not reuse CMS nursing-home fields as if they covered assisted living.

No percentage in this section should be interpreted as recommendation influence or predictive accuracy.

## Minimum Resident/Family Inputs Before First Search

Ask only information necessary to create a meaningful first candidate set:

1. Who is moving: one person or a couple.
2. Target geography / practical family-access region.
3. Critical care needs that can change eligibility: ADL/mobility/transfers, cognition/dementia when relevant, medication/nursing/rehab needs, other necessary specialty support.
4. Budget only if it is a binding constraint.
5. Explicit known MUSTs such as remaining together as a couple.

Do not require autonomy, social, dining, activities, room, communication, religious/cultural, or transition-preference questions before first search unless the user has already stated one as a MUST.

## Market-Driven Next-Best-Question Examples

After an initial candidate set exists, choose the next question based on observed decision value:

- If many otherwise eligible communities differ materially in continuum of care and future escalation is plausible: ask about willingness to move again versus preference to remain in one campus.
- If the strongest options differ mainly in family visitability: ask what realistic visit frequency matters.
- If clinical/safety candidates are similar but social models differ: ask one social-style or engagement question.
- If private rooms eliminate many otherwise strong choices, ask whether privacy is a MUST before excluding them.
- If a couple can enter together but several communities may separate them later as care needs diverge, surface that trade-off explicitly before asking for a couple-continuity preference.

## Immediate Texas Data Actions

1. Build a Texas facility universe separated by facility class: Nursing Facility/SNF vs Assisted Living.
2. Reuse the existing CMS CCN-keyed ingestion architecture for Texas nursing facilities rather than creating a parallel model.
3. Add Texas HHSC/TULIP as a distinct regulatory adapter for assisted living and Texas-specific enforcement/inspection data.
4. Preserve source/provenance and facility-class semantics so CMS-only measures never leak into ALF records.
5. Audit the existing community intelligence JSON stores for Texas records and provenance before treating them as prepared knowledge.
6. Add provider-verification fields for autonomy, communication, daily-life practices, continuum limits, couple handling, room/personalization and transition support.
7. Design future post-placement outcome collection at 30/90/180/365 days to validate which pre-placement fit constructs actually predict success.

## Decision

OPTIME already has enough public-data architecture to build a strong objective evidence layer for Texas **nursing facilities**, but not enough verified data to claim complete person-to-community fit. For **Texas assisted living**, regulatory ingestion is currently a material gap. The next implementation priority is therefore Texas source ingestion/provenance plus provider verification for the human-fit dimensions—not a larger intake questionnaire and not numeric scoring weights.