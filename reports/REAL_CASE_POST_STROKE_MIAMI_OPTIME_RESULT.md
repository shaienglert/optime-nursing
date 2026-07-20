# REAL CASE POST STROKE MIAMI OPTIME RESULT

## Provenance
- Generated at: 2026-07-20T10:35:47.8755406Z
- Git commit: 95f4b7f7074b6ba2af7e28455189de6fd2b3e2d1
- Case ID: POST_STROKE_MIAMI_001
- Case version: 1.0.0
- Runtime entrypoint: benchmark/adapters/optime_runtime_runner.cjs

## Case
- Scenario: 80-year-old post-stroke senior with explicit clinical requirements and unknown budget.
- Location: Miami-Dade, FL
- Person profile: age 80, age group 80-84, gender Male, mobility Limited
- Explicit needs: 24/7 nursing availability; rehabilitation capability; medication management; post-stroke support
- Explicit non-negotiables: 24/7 nursing availability; rehabilitation capability; medication management
- Preferences: Miami-Dade or nearby; social engagement desirable
- Known unknowns: budget; facility-level evidence gaps
- Expected clarifications: maximum monthly budget; preferred language support; family visit frequency constraints

## Runtime Result
- run_status: OK
- accepted_count: 55
- rejected_count: 45
- fallback_count: 0
- chain_breaks: []

## Top 5
1. JOHN KNOX VILLAGE OF POMPANO BEACH
   - facility_id: 62
   - canonical_facility_id: 84
   - location: POMPANO BEACH, FL
   - must_satisfied: Future care pathway: Full continuum of care on one campus
   - must_failed: none
   - must_unknown: none
   - recommendation_alignment: No additional medical capability translation was required from the current profile.
   - nice_to_have_alignment: No explicit lifestyle preferences were captured in this profile.
   - tradeoffs: Future care preference was considered (Full continuum of care on one campus). Confirmed future-care alignment: Future care pathway: Full continuum of care on one campus.
   - evidence_gaps: none
   - confidence: 100
2. RIVER GARDEN HEBREW HOME FOR THE AGED
   - facility_id: 7
   - canonical_facility_id: 162
   - location: JACKSONVILLE, FL
   - must_satisfied: none
   - must_failed: none
   - must_unknown: Future care pathway: Full continuum of care on one campus
   - recommendation_alignment: No additional medical capability translation was required from the current profile.
   - nice_to_have_alignment: No explicit lifestyle preferences were captured in this profile.
   - tradeoffs: Future care preference was considered (Full continuum of care on one campus). Confirmed future-care alignment: none yet.
   - evidence_gaps: Future care pathway: Full continuum of care on one campus
   - confidence: UNKNOWN
3. BISCAYNE HEALTH AND REHABILITATION CENTER
   - facility_id: 4
   - canonical_facility_id: 375
   - location: NORTH MIAMI, FL
   - must_satisfied: none
   - must_failed: none
   - must_unknown: Future care pathway: Full continuum of care on one campus
   - recommendation_alignment: No additional medical capability translation was required from the current profile.
   - nice_to_have_alignment: No explicit lifestyle preferences were captured in this profile.
   - tradeoffs: Future care preference was considered (Full continuum of care on one campus). Confirmed future-care alignment: none yet.
   - evidence_gaps: Future care pathway: Full continuum of care on one campus
   - confidence: UNKNOWN
4. CORAL GABLES NURSING AND REHABILITATION CENTER
   - facility_id: 3
   - canonical_facility_id: 348
   - location: MIAMI, FL
   - must_satisfied: none
   - must_failed: none
   - must_unknown: Future care pathway: Full continuum of care on one campus
   - recommendation_alignment: No additional medical capability translation was required from the current profile.
   - nice_to_have_alignment: No explicit lifestyle preferences were captured in this profile.
   - tradeoffs: Future care preference was considered (Full continuum of care on one campus). Confirmed future-care alignment: none yet.
   - evidence_gaps: Future care pathway: Full continuum of care on one campus
   - confidence: UNKNOWN
5. SANDS AT SOUTH BEACH CARE CENTER, THE
   - facility_id: 54
   - canonical_facility_id: 372
   - location: MIAMI BEACH, FL
   - must_satisfied: none
   - must_failed: none
   - must_unknown: Future care pathway: Full continuum of care on one campus
   - recommendation_alignment: No additional medical capability translation was required from the current profile.
   - nice_to_have_alignment: No explicit lifestyle preferences were captured in this profile.
   - tradeoffs: Future care preference was considered (Full continuum of care on one campus). Confirmed future-care alignment: none yet.
   - evidence_gaps: Future care pathway: Full continuum of care on one campus
   - confidence: UNKNOWN

## Notes
- This artifact freezes the exact committed OPTIME runtime output for the requested case.
- No recommendation logic was modified before running the benchmark.