# Recommendation Influence Model v1

Status: RESEARCH / DECISION POLICY CANON — NO NUMERIC PRODUCTION WEIGHTS

Purpose: define how Resident–Senior Living Success Factors influence an OPTIME recommendation before prospective validation permits numeric weighting.

## Influence Classes

- HARD GATE: a known mismatch may make a provider ineligible when the requirement is genuinely mandatory.
- HIGH: should materially affect ordering among eligible providers when evidence is known.
- MEDIUM: meaningful discriminator, but should not dominate stronger care/safety/relationship dimensions.
- CONTEXTUAL: affects recommendation only when explicitly important to the resident/family or when it changes another validated factor.
- RESEARCH-ONLY: collect if useful, but do not use as an independent ranking factor yet.

UNKNOWN never becomes MATCH or MISMATCH. A missing value cannot create a hard exclusion unless a separate safety rule requires verified evidence before eligibility.

## Canonical Recommendation Influence

| Factor | Influence | Gate condition | Ranking role | Current scientific position |
| --- | --- | --- | --- | --- |
| Clinical Capability Fit | HARD GATE | Known inability to meet a mandatory care need | Eligible providers that verify the needed capability rank above UNKNOWN | Necessary capability; exact success magnitude varies |
| Verified Safety / Regulatory Risk | HARD GATE or HIGH | Severe/current safety risk under Guardian policy | Strong negative evidence materially lowers recommendation | High-value operational evidence; outcome-specific |
| Mandatory Budget Fit | HARD GATE | Known cost above approved MUST budget | Within-budget unknown/known values retain provenance | User constraint, not scientific predictor |
| Mandatory Geography / Access | HARD GATE when declared MUST | Known violation of approved location/visit constraint | Otherwise used through visitability | User constraint; direct success effect is indirect |
| Couple Co-residence / Separation Constraint | HARD GATE when declared MUST | Facility cannot keep couple together as required | Unknown remains eligible but flagged | Operational requirement; couple outcome evidence limited |
| Functional / Cognitive Care-Needs Fit | HIGH and sometimes HARD GATE | Specific unmet care need | Major fit dimension | Recurrent adjustment/care relevance |
| Autonomy / Choice Fit | HIGH | No generic gate unless resident declares a MUST | Major personal-fit dimension | Strong recurring QoL/adjustment construct |
| Resident–Staff Relationship Capability | HIGH | No direct pre-placement gate except serious evidence of failure | Major fit dimension; use verified proxies and later outcomes | Strong construct, limited prospective coefficients |
| Social Connection / Social Climate Fit | HIGH | No generic gate | Major adaptation/QoL discriminator | Recurrent across assisted-living and nursing-home literature |
| Decision Participation / Move Voluntariness | HIGH | Not a provider exclusion | Modifies confidence in transition recommendation and timing | Recurrent adjustment factor |
| Transition Preparation / Expectation Realism | HIGH | Not a provider exclusion | Drives transition plan and next-best questions | Moderate evidence; causal magnitude not established |
| Staffing Stability / Consistency | HIGH for quality layer | No universal threshold yet | Stable verified staffing ranks above materially unstable staffing when resident acuity makes continuity important | Moderate-high quality evidence; direct placement-success validity still to be learned |
| Staffing Sufficiency / Skill Mix | HIGH for safety/care capability | Can become gate if required competency/coverage is absent | Material quality/capability discriminator | Moderate-high, heterogeneous measures |
| Preference Congruence / Daily-Life Fit | MEDIUM-HIGH | Can become HARD GATE only for explicit legitimate MUST | Important resident-specific ranking dimension | Moderate-high QoL/sense-of-home evidence |
| Family Connection / Visitability | MEDIUM-HIGH | Gate only when family declares it MUST | Ranks based on practical continued connection, not miles alone | Moderate evidence |
| Family–Staff Communication Fit | MEDIUM-HIGH | Rarely a gate | Important family-experience dimension | Moderate evidence |
| Meaningful Engagement Fit | MEDIUM | Gate only for explicit MUST | Personal relevance matters more than activity count | Moderate evidence |
| Sense-of-Home / Privacy / Personalization | MEDIUM | May become MUST for specific resident | Personal-fit dimension | Moderate descriptive/association evidence |
| Continuum-of-Care / Avoidable Relocation Risk | MEDIUM-HIGH | Can become gate where foreseeable required care cannot be supported | Important long-horizon discriminator | Limited-moderate direct evidence; strong operational relevance |
| Self-Efficacy / Coping Capacity | CONTEXTUAL | Never a provider gate | Changes transition support needed, not provider desirability directly | Moderate association; causality unknown |
| Private Room | CONTEXTUAL | Gate only if resident explicitly requires it | Preference/environment variable only | Not a generic quality factor |
| Facility Size | RESEARCH-ONLY | None | Do not independently rank | Conflicting evidence |
| Ownership / Chain / Profit Status | RESEARCH-ONLY | None except verified regulatory consequences | Do not independently rank | Conflicting evidence; use actual quality outcomes instead |
| Couple Success Score | RESEARCH-ONLY | None | No numeric couple-fit score | Direct evidence insufficient |

## 'How Much' Rule

V1 intentionally does not assign percentages or point weights. Published effect sizes refer to different outcomes, populations and study designs and are not interchangeable with product weights.

The only authorized strength ordering before prospective OPTIME validation is:

1. Mandatory eligibility / safety gates
2. HIGH evidence-backed resident-specific fit and operational quality dimensions
3. MEDIUM / MEDIUM-HIGH discriminators
4. CONTEXTUAL resident-declared preferences
5. RESEARCH-ONLY variables

Within the same class, OPTIME must not invent a fixed mathematical precedence unless an explicit user MUST, safety rule, or validated domain rule establishes it.

## Evidence Examples That Must Not Become Product Weights

- A model explaining 60.6% of adjustment variance used multiple predictors together; this is not a 60.6% weight for any one factor.
- Choice and staff relationship explaining 25% of QoL variance together is not a 25% ranking weight.
- Staffing turnover associations with deficiencies quantify a specific quality relationship, not the proportion of placement success explained by turnover.

## Recommendation Architecture

1. Apply legal/safety and resident-declared MUST gates.
2. Preserve UNKNOWN rather than exclude it.
3. Build separate evidence-backed dimensions: Care Capability, Safety/Operations, Human/Autonomy Fit, Social/Relationship Fit, Daily-Life Fit, Transition/Continuity Fit.
4. Rank Known Match above Unknown inside the same relevant dimension.
5. Surface trade-offs instead of collapsing all dimensions into an opaque universal score.
6. Use Next-Best-Question only when an UNKNOWN can materially alter eligibility, ordering or a meaningful trade-off.
7. After placements, learn numeric calibration only from prospective outcome data with cohort, timeframe and provenance.

## Outcome Validation Required Before Numeric Weights

At minimum collect: placement selected, move-in, 30/90/180/365-day retention, avoidable transfer/move-out, resident satisfaction/QoL where feasible, family satisfaction, safety events, hospitalization/ED use when relevant, complaints, transition distress/adjustment and reason for termination/relocation. Numeric weights require prospective validation against these outcomes rather than conversion of literature coefficients.