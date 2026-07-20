# POST_STROKE_MIAMI DECISION AUTOPSY

## Frozen Run Reference
- Frozen result commit: `ca2d26b3f298599b7345d133007104ec57c94e98`
- Frozen benchmark artifact: `reports/REAL_CASE_POST_STROKE_MIAMI_OPTIME_RESULT.json`
- Runtime entrypoint: `benchmark/adapters/optime_runtime_runner.cjs`
- Runtime universe: 100 facilities
- Canonical universe: 713 facilities
- Frozen top 5 unchanged: YES

## Executive Finding
The frozen OPTIME result is traceable to the real runtime, but the decision is not fully defensible as a consumer-facing Miami-Dade recommendation because the adapter never turned the case’s geographic preference into a mandatory geographic constraint, hard-coded a budget value, and did not preserve enough per-candidate trace data to fully reconstruct the score.

## Top-5 Identity Forensics
1. JOHN KNOX VILLAGE OF POMPANO BEACH
   - Canonical ID: 84
   - Address: 700 SW 4TH STREET, POMPANO BEACH, FL 33060
   - County: Broward
   - CMS: 105255
   - Type: Continuing Care Retirement Communities (CCRC) / Skilled Nursing
   - Identity status: CONFIRMED_CANONICAL_ID
   - Location sources: CMS Provider Information; Medicare Care Compare
   - Flag: GEOGRAPHY_CONFLICT
2. RIVER GARDEN HEBREW HOME FOR THE AGED
   - Canonical ID: 162
   - Address: 11401 OLD SAINT AUGUSTINE RD, JACKSONVILLE, FL 32258
   - County: Duval
   - CMS: 105016
   - Type: Skilled Nursing
   - Identity status: CONFIRMED_CANONICAL_ID
   - Location sources: CMS Provider Information; Medicare Care Compare
   - Flag: GEOGRAPHY_CONFLICT
3. BISCAYNE HEALTH AND REHABILITATION CENTER
   - Canonical ID: 375
   - Address: 12505 NE 16TH AVE, NORTH MIAMI, FL 33161
   - County: Miami-Dade
   - CMS: 105008
   - Type: Skilled Nursing
   - Identity status: CONFIRMED_CANONICAL_ID
   - Location sources: CMS Provider Information; Medicare Care Compare
   - Flag: IDENTITY_OK
4. CORAL GABLES NURSING AND REHABILITATION CENTER
   - Canonical ID: 348
   - Address: 7060 SW 8TH STREET, MIAMI, FL 33144
   - County: Miami-Dade
   - CMS: 105005
   - Type: Skilled Nursing
   - Identity status: CONFIRMED_CANONICAL_ID
   - Location sources: CMS Provider Information; Medicare Care Compare
   - Flag: IDENTITY_OK
5. SANDS AT SOUTH BEACH CARE CENTER, THE
   - Canonical ID: 372
   - Address: 42 COLLINS AVENUE, MIAMI BEACH, FL 33139
   - County: Miami-Dade
   - CMS: 105229
   - Type: Skilled Nursing
   - Identity status: CONFIRMED_CANONICAL_ID
   - Location sources: CMS Provider Information; Medicare Care Compare
   - Flag: IDENTITY_OK

## Geography Autopsy
- The case preference `Miami-Dade or nearby` was stored as a note and `referenceLocationValue`, but it was not converted into a mandatory county constraint because `hasMandatoryDistanceRequirement()` only triggers on phrases like `only in miami-dade`, `stay in miami-dade`, `must stay close`, or `distance is mandatory`.
- `parseDistancePoints()` depends on `distanceProfile.driveTimes.normal` or `distanceFromFamily`; the adapter did not populate either field, so distance scored neutral.
- `hasDistanceConstraint()` was false because the adapter did not inject family distance inputs or drive-time values.
- `collectHardRejectionReasons()` only rejects on geography when the distance constraint is active and family fit is below threshold, so geography did not act as a hard filter.
- John Knox Village of Pompano Beach outranked Miami-Dade facilities because the engine favored care-fit, CCRC/future-care coverage, and rehabilitation persona weights, while geography remained neutral.
- River Garden Hebrew Home in Jacksonville is canonically a Duval County skilled nursing facility; it is not a Miami-Dade facility and should not be treated as geographically local.

## Requirements Autopsy
- `24/7 nursing availability` -> MUST in the user case, derived from `buildClinicalRequirements()` as `Licensed nurses 24/7` / `Skilled nursing capability`; evidence in the frozen run is UNKNOWN at the top-5 level.
- `post-stroke rehabilitation` -> MUST, derived from `hasStrokeHistory` and `Neurological rehabilitation`; evidence mostly UNKNOWN at the frozen top-5 surface.
- `physical therapy` -> OUR_RECOMMENDATION, derived from `buildClinicalRequirements()`; evidence UNKNOWN on the frozen top-5 surface.
- `occupational therapy` -> OUR_RECOMMENDATION, derived from `buildClinicalRequirements()`; evidence UNKNOWN on the frozen top-5 surface.
- `limited mobility` -> MUST, derived from `hasMobilityLimitations` and `Walker accessibility` / `Fall prevention protocol`; evidence UNKNOWN at the frozen top-5 surface.
- `transfer assistance` -> OUR_RECOMMENDATION, derived from `Mobility and transfer assistance`; evidence UNKNOWN.
- `bathing assistance` -> NOT_CONNECTED_TO_RUNTIME; the frozen benchmark adapter did not map this signal into the runtime state.
- `dressing assistance` -> NOT_CONNECTED_TO_RUNTIME; the frozen benchmark adapter did not map this signal into the runtime state.
- `medication management` -> MUST in the case intent, but NOT_CONNECTED_TO_RUNTIME in the frozen adapter because it was not explicitly mapped into a clinical requirement.
- `Miami/family proximity` -> OUR_RECOMMENDATION in the case intent, but the frozen adapter did not promote it to a mandatory distance constraint.
- `no dementia requirement` -> NOT_A_REQUIREMENT; nothing in the frozen case or engine created a negative dementia-only constraint.
- `Hebrew/language preference` -> NOT_CONNECTED_TO_RUNTIME; the frozen adapter did not populate a language requirement.
- `social activities` -> OUR_RECOMMENDATION; the case only contained a soft social preference and the adapter did not encode a social frequency requirement.
- `movies/music/conversation` -> NOT_CONNECTED_TO_RUNTIME; no such runtime preference was injected.
- `gluten-free diet` -> NOT_CONNECTED_TO_RUNTIME; no dietary restriction was injected.
- `food quality` -> NOT_CONNECTED_TO_RUNTIME; no explicit food requirement was injected.
- `budget <= $17,000` -> MISCLASSIFIED; the adapter hard-coded `budget: 7000` instead of preserving unknown budget truth.

## Score Decomposition
- `SCORE_TRACEABILITY_FAILURE = YES`
- Exact total scores for the frozen top-5 are not preserved in the frozen artifact.
- The governing formula is visible: `final_score = tiered_match_quality(critical, important, optional) - mismatch_penalties` with ranking tie-breakers from `OUR_RECOMMENDATION alignment`, `NICE_TO_HAVE alignment`, `legacy heuristic match score`, profile completeness, clinical quality, and family fit.
- Available component evidence for John Knox:
  - Rehabilitation persona selected.
  - Care-fit favored skilled nursing / rehabilitation / CCRC coverage.
  - Geography was neutral, not mandatory.
  - Future care alignment was positive.
- Available component evidence for River Garden:
  - Rehabilitation persona selected.
  - Skilled nursing matched, but geography was Duval County / Jacksonville.
  - Future care alignment was weaker because no CCRC signal is preserved in the frozen top-5 output.
- Exact numeric reconciliation is not possible from the frozen artifact alone.

## Comparison Facility Audit
- THE PALACE NURSING AND REHABILITATION CENTER: no canonical record found in the canonical inventory or runtime feed; not in candidate pool; excluded for missing canonical record.
- VI AT AVENTURA: canonical record found; identity resolved; Miami-Dade; not present in the 100-facility runtime feed; excluded from the frozen candidate pool.
- RIVIERA HEALTH RESORT: canonical record found; identity resolved; Miami-Dade; not present in the runtime feed; excluded from the frozen candidate pool.
- MIAMI JEWISH HEALTH: canonical record found as `MIAMI JEWISH HEALTH SYSTEMS, INC`; identity resolved; Miami-Dade; entered runtime pool; eligible but below top-5 because the frozen output preserves no stronger future-care / CCRC signal than the surfaced top-ranked communities.
- EAST RIDGE AT CUTLER BAY: canonical inventory contains `East Ridge Rehabilitation and Nursing Center`; identity alias exists, but the alias was not present in the runtime feed used for the frozen run.
- WEST GABLES HEALTH CARE CENTER: canonical record found; identity resolved; Miami-Dade; not present in the runtime feed; excluded from the frozen candidate pool.
- CORAL GABLES NURSING AND REHABILITATION CENTER: canonical record found; identity resolved; Miami-Dade; entered runtime pool; surfaced as rank 4 in the frozen top-5.
- VICTORIA NURSING AND REHABILITATION CENTER: no canonical record found in the local canonical inventory; not in candidate pool.

## Candidate Funnel
- Canonical universe: 713
- Runtime universe: 100
- Discovered: 100
- Identity resolved: 100
- Evidence evaluated: 100
- Eligible candidates: 55
- Rejected candidates: 45
- Ranked candidates: 55
- Top 5 selected: 5
- Exact MUST_ELIGIBLE / MUST_VERIFICATION_REQUIRED / MUST_REJECTED stage split is not preserved in the frozen artifact, so the funnel is only partially reconstructable.
- `CANDIDATE_FUNNEL_TRACEABILITY_FAILURE = YES`

## Unknown Governance
- UNKNOWN budget was not respected: the adapter hard-coded `budget: 7000`, which can avoid a price penalty and is not equivalent to unknown.
- UNKNOWN geography was treated as neutral because the adapter never populated the distance fields required by `parseDistancePoints()`.
- UNKNOWN language, gluten-free, PT/OT, social programming, and diet details were not connected to runtime state, so they could not influence the score as unknowns should.
- Missing evidence was preserved as UNKNOWN in the top-5 output, but the absence of injected runtime fields means several case signals never entered the decision path at all.

## Root Causes
- RUNTIME_WIRING_ERROR / HIGH: the benchmark adapter hard-coded `budget: 7000`, set `futureCarePreference` unconditionally, and did not populate distance, language, or dietary fields from the case.
- GEOGRAPHY_LOGIC_ERROR / HIGH: the engine only makes geography mandatory for explicit distance phrases; a soft Miami-Dade preference was not enough to constrain the ranking.
- MUST_CLASSIFICATION_ERROR / HIGH: several case-level needs were not carried into the runtime state, so they could not be enforced as MUSTs.
- UNKNOWN_GOVERNANCE_ERROR / HIGH: unknown budget and missing evidence were not preserved cleanly through the adapter boundary.
- TRACEABILITY_ERROR / HIGH: the frozen artifact does not retain candidate-by-candidate score decompositions or stage transitions.
- IDENTITY_RESOLUTION_ERROR / MEDIUM: external alias names such as East Ridge / Miami Jewish / Riviera were not normalized in the frozen artifact, making the comparison audit partial.
- NO_ERROR / EXPECTED_BEHAVIOR / LOW: canonical identity for the surfaced top-5 facilities is confirmed through CMS Provider Information and Medicare Care Compare.

## Decision Verdict
1. Can we currently defend John Knox Village as #1 for this person from the available evidence? `INSUFFICIENT_EVIDENCE`
2. Is River Garden Hebrew Home correctly identified and geographically appropriate? `YES` for identity, `NO` for geography.
3. Did geography materially influence the ranking as intended? `NO`
4. Were all true MUST requirements enforced? `NO`
5. Can the Top-5 ranking be fully reconstructed from evidence + scoring? `NO`
6. Is the frozen Top 5 trustworthy enough to show a real consumer today? `NO`

## Validation
- Frozen top 5 unchanged: YES
- Recommendation logic changed: NO
- Weights changed: NO
- Canonical data modified: NO
- Autopsy traceable to real run: YES

## Closing
This autopsy preserves the frozen decision baseline before remediation. It does not change recommendation logic, weights, or canonical data.