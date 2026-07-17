# Inventory Mix Report

## Goal

Expand support across the full senior living journey categories.

## Inventory Summary

- Total facilities analyzed: **100**
- Categories requested: **7**

| Category | Facility Count | Inventory Share | States Covered | Cities Covered |
| --- | --- | --- | --- | --- |
| Active Adult 55+ | 3 | 3% | 1 | 3 |
| Independent Living | 10 | 10% | 1 | 8 |
| Assisted Living | 54 | 54% | 1 | 38 |
| Memory Care | 4 | 4% | 1 | 4 |
| Skilled Nursing | 50 | 50% | 1 | 38 |
| Rehabilitation | 59 | 59% | 1 | 39 |
| CCRC | 1 | 1% | 1 | 1 |

## Missing Categories

- None. All requested categories are represented.

## Geographic Coverage

### Top States by Facility Count

| State | Facility Count | Share |
| --- | --- | --- |
| FL | 100 | 100% |

### Top Cities by Facility Count

| City | Facility Count | Share |
| --- | --- | --- |
| SAINT PETERSBURG | 9 | 9% |
| NORTH MIAMI | 4 | 4% |
| JACKSONVILLE | 4 | 4% |
| FORT LAUDERDALE | 4 | 4% |
| TAMPA | 4 | 4% |
| MIAMI | 3 | 3% |
| DAYTONA BEACH | 3 | 3% |
| DELAND | 3 | 3% |
| LAKE WORTH | 2 | 2% |
| NORTH MIAMI BEACH | 2 | 2% |
| FORT WALTON BEACH | 2 | 2% |
| PLANTATION | 2 | 2% |
| WEST PALM BEACH | 2 | 2% |
| MELBOURNE | 2 | 2% |
| POMPANO BEACH | 2 | 2% |

## Success Criteria Validation

- No single care category exceeds 40% of total inventory: **FAIL**
  - Highest category: Rehabilitation (59%)
- Independent Living + Assisted Living + Active Adult >= 50%: **PASS**
  - Combined share: 67%

## Notes

- Facilities may belong to multiple categories; percentages are per-category coverage over total facilities and are not mutually exclusive.
- Category assignment uses the post-taxonomy inference pipeline (`toSearchFacility(..., "post")`).