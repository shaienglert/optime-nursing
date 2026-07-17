# UI vs Simulation Discrepancy Investigation

## Persona
- Age: 60-64
- Care: Fully Independent
- Activities: Social activities
- Budget: 11600

1. Engine result count before UI filtering
- 39

2. Result count after UI filtering
- 39

3. Result count after quality gate filtering
- Pre-fix behavior: 39
- Post-fix behavior: 39 (best available matches still displayed)

4. Exact code path that converts non-empty results into an empty list
- results-page-client.tsx:
- - Non-empty recommendations are hidden when this condition fails: `engineOutput.qualityCheck.passed && engineOutput.accepted.length > 0`.
- - Pre-fix empty-state path: quality gate failure branch rendered warning only and suppressed recommendation sections.
- - Post-fix behavior: warning banner is shown, and best available matches still render with badge "Below confidence threshold".

5. Is the live UI using the same engine version as run_dynamic_persona_simulation_audit.cjs?
- YES. Both import frontend/src/lib/optime-v2-engine.ts (hash: 63abe7697938).

6. Compare simulation top result vs live UI top result vs engine hash/version

| Path | Top Result | Score | Engine Hash |
| --- | --- | --- | --- |
| Simulation mode | JOHN KNOX VILLAGE OF POMPANO BEACH | 57.33 | 63abe7697938 |
| Live UI path (production mode) | JOHN KNOX VILLAGE OF POMPANO BEACH | 56.69 | 63abe7697938 |

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
| 1 | JOHN KNOX VILLAGE OF POMPANO BEACH | Independent Living, CCRC | 56.69 | NO | N/A |
| 2 | TARPON BAYOU CENTER | Assisted Living, Independent Living | 51.94 | NO | N/A |
| 3 | CLEARWATER CENTER | Assisted Living, Independent Living | 51.75 | NO | N/A |
| 4 | BARTOW CENTER | Assisted Living, Independent Living | 51.75 | NO | N/A |
| 5 | AVANTE AT LEESBURG, INC | Assisted Living, Independent Living | 51.74 | NO | N/A |
| 6 | AVIATA AT THE SEA - PASADENA | Assisted Living, Independent Living | 51.25 | NO | N/A |
| 7 | AVIATA AT EMERALD SHORES | Assisted Living, Independent Living, Memory Care | 47.29 | NO | N/A |
| 8 | ATHENS POST ACUTE LLC | Assisted Living, Independent Living, Memory Care | 46.60 | NO | N/A |
| 9 | RIVER GARDEN HEBREW HOME FOR THE AGED | Assisted Living | 0.00 | NO | N/A |
| 10 | GROVES CENTER | Assisted Living, Skilled Nursing, Independent Living | 0.00 | NO | N/A |
| 11 | EGRET COVE CENTER | Assisted Living, Skilled Nursing, Independent Living | 0.00 | NO | N/A |
| 12 | FAIRWAY OAKS CENTER | Assisted Living, Skilled Nursing, Independent Living | 0.00 | NO | N/A |
| 13 | COMMUNITY CONVALESCENT CENTER | Skilled Nursing, Assisted Living | 0.00 | NO | N/A |
| 14 | EAGLE LAKE NURSING AND REHAB CARE CENTER | Rehabilitation, Assisted Living | 0.00 | NO | N/A |
| 15 | SHORE ACRES CARE CENTER AND REHAB | Rehabilitation, Assisted Living | 0.00 | NO | N/A |
| 16 | SOUTH HERITAGE HEALTH & REHABILITATION CENTER | Rehabilitation, Assisted Living | 0.00 | NO | N/A |
| 17 | Rehabilitation Center of The Palm Beaches, The | Rehabilitation, Assisted Living | 0.00 | NO | N/A |
| 18 | WESTLAKE NURSING AND REHAB CENTER | Rehabilitation, Assisted Living | 0.00 | NO | N/A |
| 19 | MADISON POINTE CARE CENTER | Assisted Living, Skilled Nursing, Rehabilitation | 0.00 | NO | N/A |
| 20 | MIAMI JEWISH HEALTH SYSTEMS, INC | Skilled Nursing, Assisted Living | 0.00 | NO | N/A |

## Failed Facilities and Recommended Fix

| Facility | Failure Reason | Recommended Fix |
| --- | --- | --- |
| TERRACES OF LAKE WORTH CARE CENTER AND REHAB | Required care level is not met for this community. | scoring issue |
| BISCAYNE HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| MORTON PLANT REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| CRESTVIEW REHABILITATION CENTER, LLC | Required care level is not met for this community. | scoring issue |
| Pinecrest Center for Rehabilitation and Healing | Required care level is not met for this community. | scoring issue |
| SERENITY BAY NURSING AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| FORT WALTON REHABILITATION CENTER, LLC | Required care level is not met for this community. | scoring issue |
| PLANTATION NURSING & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| BEACH STREET HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| BROWARD NURSING & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| MARTIN COAST CENTER FOR REHABILITATION AND HEALTHC | Required care level is not met for this community. | scoring issue |
| WHISPERING OAKS | Required care level is not met for this community. | scoring issue |
| CRYSTAL RIVER HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| WILTON MANORS HEALTHCARE & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| BOULEVARD REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | Required care level is not met for this community. | scoring issue |
| PARKVIEW REHABILITATION CENTER AT WINTER PARK | Required care level is not met for this community. | scoring issue |
| STUART REHABILITATION AND HEALTHCARE | Required care level is not met for this community. | scoring issue |
| FT LAUDERDALE HEALTH & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| PINES OF SARASOTA | Required care level is not met for this community. | scoring issue |
| JACKSON MEMORIAL PERDUE MEDICAL CENTER | Required care level is not met for this community. | scoring issue |
| OAK MANOR HEALTHCARE & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| EDEN SPRINGS NURSING AND REHAB CENTER | Required care level is not met for this community. | scoring issue |
| BRADEN RIVER REHABILITATION CENTER LLC | Required care level is not met for this community. | scoring issue |
| SAVOY AT FORT LAUDERDALE REHABILITATION AND NURSIN | Required care level is not met for this community. | scoring issue |
| MEDICANA NURSING AND REHAB CENTER | Required care level is not met for this community. | scoring issue |
| BROWARD OAKS NURSING AND REHABILITATION | Required care level is not met for this community. | scoring issue |
| ROCKLEDGE HEALTHCARE & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| BOCA RATON REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| NORTH HEALTHCARE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| VENTURA HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| PEARL AT FORT LAUDERDALE REHABILITATION AND NURSIN | Required care level is not met for this community. | scoring issue |
| BEACHSIDE CENTER FOR REHABILITATION AND NURSING | Required care level is not met for this community. | scoring issue |
| APOLLO HEALTHCARE & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| DAYTONA BEACH HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| BAYSIDE HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| THE LODGE HEALTHCARE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| LAURELLWOOD POST- ACUTE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| PARKSIDE HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| OAK HAVEN REHAB AND NURSING CENTER | Required care level is not met for this community. | scoring issue |
| SEASIDE HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| GREENBRIAR HEALTHCARE REHABILITATION AND NURSING C | Required care level is not met for this community. | scoring issue |
| LAKE EUSTIS HEALTHCARE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| PALMS AT SEBRING NURSING AND REHABILITATION THE | Required care level is not met for this community. | scoring issue |
| JACKSONVILLE REHABILITATION AND NURSING | Required care level is not met for this community. | scoring issue |
| LEXINGTON HEALTHCARE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| AVIATA AT LAKESIDE OAKS | Required care level is not met for this community. | scoring issue |
| AVANTE AT ORMOND BEACH, INC | Required care level is not met for this community. | scoring issue |
| WINTER HAVEN HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| MELBOURNE HEALTHCARE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| VILLA MARIA NURSING CENTER | Required care level is not met for this community. | scoring issue |
| ST AUGUSTINE HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| AVIATA AT SAINT LUCIE | Required care level is not met for this community. | scoring issue |
| REHABILITATION AND HEALTHCARE CENTER OF TAMPA | Required care level is not met for this community. | scoring issue |
| PARK MEADOWS HEALTHCARE & REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| VALENCIA HILLS HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| WESTSIDE OAKS REHABILITATION & NURSING CENTER | Required care level is not met for this community. | scoring issue |
| SARASOTA HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |
| SUNRISE POINT HEALTH AND REHABILITATION CENTER | Required care level is not met for this community. | scoring issue |