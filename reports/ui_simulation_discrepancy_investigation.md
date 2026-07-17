# UI vs Simulation Discrepancy Investigation

## Persona
- Age: 60-64
- Care: Fully Independent
- Activities: Social activities
- Budget: 11600

1. Engine result count before UI filtering
- 100

2. Result count after UI filtering
- 100

3. Result count after quality gate filtering
- Pre-fix behavior: 100
- Post-fix behavior: 100 (best available matches still displayed)

4. Exact code path that converts non-empty results into an empty list
- results-page-client.tsx:
- - Non-empty recommendations are hidden when this condition fails: `engineOutput.qualityCheck.passed && engineOutput.accepted.length > 0`.
- - Pre-fix empty-state path: quality gate failure branch rendered warning only and suppressed recommendation sections.
- - Post-fix behavior: warning banner is shown, and best available matches still render with badge "Below confidence threshold".

5. Is the live UI using the same engine version as run_dynamic_persona_simulation_audit.cjs?
- YES. Both import frontend/src/lib/optime-v2-engine.ts (hash: 3e87c98d6eba).

6. Compare simulation top result vs live UI top result vs engine hash/version

| Path | Top Result | Score | Engine Hash |
| --- | --- | --- | --- |
| Simulation mode | JOHN KNOX VILLAGE OF POMPANO BEACH | 80.91 | 3e87c98d6eba |
| Live UI path (production mode) | JOHN KNOX VILLAGE OF POMPANO BEACH | 80.01 | 3e87c98d6eba |

7. Quality gate fallback behavior update
- Applied: warning banner shown when quality gate fails.
- Applied: best available matches still displayed.
- Applied: matches are marked as "Below confidence threshold".

## Care Type Distribution

| Care Type | Count |
| --- | --- |
| Independent Living | 12 |
| Active Adult 55+ | 0 |
| Assisted Living | 38 |
| Memory Care | 2 |
| Skilled Nursing | 35 |
| Rehabilitation | 74 |
| CCRC | 1 |
| Continuing Care | 0 |
| Hospice | 0 |
| UNKNOWN | 0 |

## Top 20 Before Quality Gate Filtering

| Rank | Facility | Care Types | Score | Rejected? | Rejection Reason |
| --- | --- | --- | --- | --- | --- |
| 1 | JOHN KNOX VILLAGE OF POMPANO BEACH | Independent Living, CCRC | 80.01 | NO | N/A |
| 2 | AVIATA AT THE SEA - PASADENA | Assisted Living, Independent Living | 64.83 | NO | N/A |
| 3 | CLEARWATER CENTER | Assisted Living, Independent Living | 63.48 | NO | N/A |
| 4 | TARPON BAYOU CENTER | Assisted Living, Independent Living | 63.44 | NO | N/A |
| 5 | AVANTE AT LEESBURG, INC | Assisted Living, Independent Living | 63.30 | NO | N/A |
| 6 | BARTOW CENTER | Assisted Living, Independent Living | 61.79 | NO | N/A |
| 7 | RIVER GARDEN HEBREW HOME FOR THE AGED | Assisted Living | 44.42 | NO | N/A |
| 8 | AVIATA AT EMERALD SHORES | Assisted Living, Independent Living, Memory Care | 43.74 | NO | N/A |
| 9 | ATHENS POST ACUTE LLC | Assisted Living, Independent Living, Memory Care | 41.86 | NO | N/A |
| 10 | AVIATA AT THE SEA - POMPANO BEACH | Assisted Living, Skilled Nursing, Independent Living | 19.14 | NO | N/A |
| 11 | EGRET COVE CENTER | Assisted Living, Skilled Nursing, Independent Living | 17.97 | NO | N/A |
| 12 | GROVES CENTER | Assisted Living, Skilled Nursing, Independent Living | 17.72 | NO | N/A |
| 13 | FAIRWAY OAKS CENTER | Assisted Living, Skilled Nursing, Independent Living | 17.64 | NO | N/A |
| 14 | COMMUNITY CONVALESCENT CENTER | Skilled Nursing, Assisted Living | 14.30 | NO | N/A |
| 15 | BISCAYNE HEALTH AND REHABILITATION CENTER | Rehabilitation | 6.61 | NO | N/A |
| 16 | CORAL GABLES NURSING AND REHABILITATION CENTER | Rehabilitation, Assisted Living | 6.28 | NO | N/A |
| 17 | TERRACES OF LAKE WORTH CARE CENTER AND REHAB | Rehabilitation | 6.16 | NO | N/A |
| 18 | Rehabilitation Center of The Palm Beaches, The | Rehabilitation, Assisted Living | 6.11 | NO | N/A |
| 19 | NORTH HEALTHCARE AND REHABILITATION CENTER | Rehabilitation | 5.81 | NO | N/A |
| 20 | WESTLAKE NURSING AND REHAB CENTER | Rehabilitation, Assisted Living | 5.64 | NO | N/A |

## Failed Facilities and Recommended Fix

- None for this persona.