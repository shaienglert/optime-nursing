# Persona Quality-Gate Failure Investigation

## Persona

- Age: 60-64
- Care level: Fully Independent
- Budget: 11600
- Preference: Social activities

## Investigation Output

1. Total facilities evaluated: **100**

2. Care type distribution after taxonomy classification:

| Care Type | Count | Share |
| --- | --- | --- |
| Independent Living | 12 | 12% |
| Active Adult 55+ | 0 | 0% |
| Assisted Living | 38 | 38% |
| Memory Care | 2 | 2% |
| Skilled Nursing | 35 | 35% |
| Rehabilitation | 74 | 74% |
| CCRC | 1 | 1% |
| Continuing Care | 0 | 0% |
| Hospice | 0 | 0% |
| UNKNOWN | 0 | 0% |

3. Number of Independent Living communities found: **12**
4. Number of Active Adult 55+ communities found: **0**

5. Top 20 facilities before quality gate filtering:

| Rank | Facility | Care Types | Score | Failed Gate? | Failure Reason |
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

6. Exact reason each facility failed the quality gate:

No facilities failed hard requirement filtering for this persona.

7. Recommended fix summary:

- No immediate classifier/dataset/threshold/scoring fix required for this persona.

Quality Gate Status: **PASS**