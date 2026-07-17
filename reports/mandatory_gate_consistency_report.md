# Mandatory Gate Consistency Report

Consistency Status: **PASS**

Business rule: accepted facility => finalScore > 0

## Scenario Summary

| Scenario | Accepted | Rejected | Accepted with finalScore <= 0 | Accepted with mandatory mismatch | Status |
| --- | --- | --- | --- | --- | --- |
| S1 - Known zero-score reproduction profile | 0 | 100 | 0 | 0 | PASS |
| S2 - Independent social profile | 8 | 92 | 0 | 0 | PASS |
| S3 - Memory support profile | 26 | 74 | 0 | 0 | PASS |
| S4 - Skilled nursing profile | 6 | 94 | 0 | 0 | PASS |

## S1 - Known zero-score reproduction profile

Top accepted sample:

| Rank | Facility | Final Score | Confidence | Mandatory mismatch |
| --- | --- | --- | --- | --- |

## S2 - Independent social profile

Top accepted sample:

| Rank | Facility | Final Score | Confidence | Mandatory mismatch |
| --- | --- | --- | --- | --- |
| 1 | JOHN KNOX VILLAGE OF POMPANO BEACH | 60.63 | 12 | NO |
| 2 | CLEARWATER CENTER | 55.62 | 12 | NO |
| 3 | BARTOW CENTER | 54.97 | 9 | NO |
| 4 | TARPON BAYOU CENTER | 54.86 | 15 | NO |
| 5 | AVANTE AT LEESBURG, INC | 54.65 | 15 | NO |

## S3 - Memory support profile

Top accepted sample:

| Rank | Facility | Final Score | Confidence | Mandatory mismatch |
| --- | --- | --- | --- | --- |
| 1 | AVIATA AT EMERALD SHORES | 87.17 | 15 | NO |
| 2 | ATHENS POST ACUTE LLC | 87.17 | 15 | NO |
| 3 | RIVER GARDEN HEBREW HOME FOR THE AGED | 81.87 | 11 | NO |
| 4 | LAKESIDE HEALTH CENTER | 80.10 | 15 | NO |
| 5 | MIAMI JEWISH HEALTH SYSTEMS, INC | 79.46 | 15 | NO |

## S4 - Skilled nursing profile

Top accepted sample:

| Rank | Facility | Final Score | Confidence | Mandatory mismatch |
| --- | --- | --- | --- | --- |
| 1 | WESTSIDE OAKS REHABILITATION & NURSING CENTER | 79.52 | 14 | NO |
| 2 | OAK HAVEN REHAB AND NURSING CENTER | 79.42 | 8 | NO |
| 3 | PEARL AT FORT LAUDERDALE REHABILITATION AND NURSIN | 78.89 | 8 | NO |
| 4 | VILLA MARIA NURSING CENTER | 77.75 | 11 | NO |
| 5 | JACKSON MEMORIAL PERDUE MEDICAL CENTER | 77.13 | 15 | NO |

## Decision

- CONSISTENCY PASS: YES
- Option A implemented: mandatory mismatch is treated as hard rejection before accepted list filtering.