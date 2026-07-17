# UI vs Simulation Discrepancy Investigation

## Persona
- Age: 60-64
- Care: Fully Independent
- Activities: Social activities
- Budget: 11600

1. Engine result count before UI filtering
- 9

2. Result count after UI filtering
- 9

3. Result count after quality gate filtering
- Pre-fix behavior: 9
- Post-fix behavior: 9 (best available matches still displayed)

4. Exact code path that converts non-empty results into an empty list
- results-page-client.tsx:
- - Non-empty recommendations are hidden when this condition fails: `engineOutput.qualityCheck.passed && engineOutput.accepted.length > 0`.
- - Pre-fix empty-state path: quality gate failure branch rendered warning only and suppressed recommendation sections.
- - Post-fix behavior: warning banner is shown, and best available matches still render with badge "Below confidence threshold".

5. Is the live UI using the same engine version as run_dynamic_persona_simulation_audit.cjs?
- YES. Both import frontend/src/lib/optime-v2-engine.ts (hash: 5c604c3a554d).

6. Compare simulation top result vs live UI top result vs engine hash/version

| Path | Top Result | Score | Engine Hash |
| --- | --- | --- | --- |
| Simulation mode | JOHN KNOX VILLAGE OF POMPANO BEACH | 80.91 | 5c604c3a554d |
| Live UI path (production mode) | JOHN KNOX VILLAGE OF POMPANO BEACH | 80.01 | 5c604c3a554d |

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
| 10 | AVIATA AT THE SEA - POMPANO BEACH | Assisted Living, Skilled Nursing, Independent Living | 19.14 | YES | Fully independent profile excludes communities that require skilled nursing care. |
| 11 | EGRET COVE CENTER | Assisted Living, Skilled Nursing, Independent Living | 17.97 | YES | Fully independent profile excludes communities that require skilled nursing care. |
| 12 | GROVES CENTER | Assisted Living, Skilled Nursing, Independent Living | 17.72 | YES | Fully independent profile excludes communities that require skilled nursing care. |
| 13 | FAIRWAY OAKS CENTER | Assisted Living, Skilled Nursing, Independent Living | 17.64 | YES | Fully independent profile excludes communities that require skilled nursing care. |
| 14 | COMMUNITY CONVALESCENT CENTER | Skilled Nursing, Assisted Living | 14.30 | YES | Fully independent profile excludes communities that require skilled nursing care. |
| 15 | BISCAYNE HEALTH AND REHABILITATION CENTER | Rehabilitation | 6.61 | YES | Fully independent profile excludes rehabilitation-focused communities. |
| 16 | CORAL GABLES NURSING AND REHABILITATION CENTER | Rehabilitation, Assisted Living | 6.28 | YES | Fully independent profile excludes rehabilitation-focused communities. |
| 17 | TERRACES OF LAKE WORTH CARE CENTER AND REHAB | Rehabilitation | 6.16 | YES | Fully independent profile excludes rehabilitation-focused communities. |
| 18 | Rehabilitation Center of The Palm Beaches, The | Rehabilitation, Assisted Living | 6.11 | YES | Fully independent profile excludes rehabilitation-focused communities. |
| 19 | NORTH HEALTHCARE AND REHABILITATION CENTER | Rehabilitation | 5.81 | YES | Fully independent profile excludes rehabilitation-focused communities. |
| 20 | WESTLAKE NURSING AND REHAB CENTER | Rehabilitation, Assisted Living | 5.64 | YES | Fully independent profile excludes rehabilitation-focused communities. |

## Failed Facilities and Recommended Fix

| Facility | Failure Reason | Recommended Fix |
| --- | --- | --- |
| TERRACES OF LAKE WORTH CARE CENTER AND REHAB | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BISCAYNE HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| MORTON PLANT REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| CRESTVIEW REHABILITATION CENTER, LLC | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| Pinecrest Center for Rehabilitation and Healing | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SERENITY BAY NURSING AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| FORT WALTON REHABILITATION CENTER, LLC | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| CORAL GABLES NURSING AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| PLANTATION NURSING & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BEACH STREET HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| Rehabilitation Center of The Palm Beaches, The | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BROWARD NURSING & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LIFE CARE CENTER OF MELBOURNE | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SANDS AT SOUTH BEACH CARE CENTER, THE | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| WESTLAKE NURSING AND REHAB CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| MARTIN COAST CENTER FOR REHABILITATION AND HEALTHC | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| WHISPERING OAKS | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| GOLFCREST NURSING CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| CRYSTAL RIVER HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| WILTON MANORS HEALTHCARE & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BOULEVARD REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| TALLAHASSEE MEMORIAL HOSPITAL EXTENDED CARE | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| PINES NURSING HOME | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| PARKVIEW REHABILITATION CENTER AT WINTER PARK | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| STUART REHABILITATION AND HEALTHCARE | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| FT LAUDERDALE HEALTH & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LAKESIDE HEALTH CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| PINES OF SARASOTA | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| JACKSON MEMORIAL PERDUE MEDICAL CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| OAK MANOR HEALTHCARE & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| EDEN SPRINGS NURSING AND REHAB CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BRADEN RIVER REHABILITATION CENTER LLC | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SAVOY AT FORT LAUDERDALE REHABILITATION AND NURSIN | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| MEDICANA NURSING AND REHAB CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| AVANTE AT INVERNESS INC | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BROWARD OAKS NURSING AND REHABILITATION | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BAYSIDE CARE CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| ROCKLEDGE HEALTHCARE & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BOCA RATON REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LIFE CARE CENTER OF PUNTA GORDA | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| NORTH HEALTHCARE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| MIAMI JEWISH HEALTH SYSTEMS, INC | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| VENTURA HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| PEARL AT FORT LAUDERDALE REHABILITATION AND NURSIN | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BEACHSIDE CENTER FOR REHABILITATION AND NURSING | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| AVIATA AT THE SEA - POMPANO BEACH | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| APOLLO HEALTHCARE & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| MADISON POINTE CARE CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| DAYTONA BEACH HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BAYSIDE HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| THE LODGE HEALTHCARE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LAURELLWOOD POST- ACUTE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| PARKSIDE HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| OAK HAVEN REHAB AND NURSING CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SEASIDE HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| GREENBRIAR HEALTHCARE REHABILITATION AND NURSING C | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LAKE EUSTIS HEALTHCARE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| PALMS AT SEBRING NURSING AND REHABILITATION THE | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| JACKSONVILLE REHABILITATION AND NURSING | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LEXINGTON HEALTHCARE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| AVIATA AT LAKESIDE OAKS | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BOCA CIEGA CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| AVANTE AT ORMOND BEACH, INC | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| WINTER HAVEN HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| MELBOURNE HEALTHCARE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| VILLA MARIA NURSING CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| FAIRWAY OAKS CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| EMERALD COAST CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| ST AUGUSTINE HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SOUTHERN PINES NURSING CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| RIVERWOOD CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| EGRET COVE CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| W FRANK WELLS NURSING HOME | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| AVIATA AT SAINT LUCIE | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| REHABILITATION AND HEALTHCARE CENTER OF TAMPA | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| PARK MEADOWS HEALTHCARE & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| Blue Lake Post Acute | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SHORE ACRES CARE CENTER AND REHAB | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| BROOKSVILLE HEALTHCARE CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| VALENCIA HILLS HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| THE BRISTOL CARE CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| WESTSIDE OAKS REHABILITATION & NURSING CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SARASOTA HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| COMMUNITY CONVALESCENT CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| SUNRISE POINT HEALTH AND REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| LAKELAND HILLS CENTER | Fully independent profile excludes communities that require skilled nursing care. \| Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| SOUTH HERITAGE HEALTH & REHABILITATION CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |
| GROVES CENTER | Fully independent profile excludes communities that require skilled nursing care. | scoring issue |
| EAGLE LAKE NURSING AND REHAB CARE CENTER | Fully independent profile excludes rehabilitation-focused communities. | scoring issue |