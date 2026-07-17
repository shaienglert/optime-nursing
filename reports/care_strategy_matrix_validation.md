# Care Strategy Matrix Validation

CARE_STRATEGY_MATRIX: **PASS**

| Scenario | Expected allowedCareTypes | Actual allowedCareTypes | Mapping | Accepted count | Accepted rule violations | Accepted rule | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fully Independent + Independent only | Independent Living, Active Adult 55+ | Independent Living, Active Adult 55+ | PASS | 6 | 0 | PASS | PASS |
| Fully Independent + Support available later | Independent Living, Active Adult 55+, Assisted Living, CCRC | Independent Living, Active Adult 55+, Assisted Living, CCRC | PASS | 8 | 0 | PASS | PASS |
| Fully Independent + Full continuum | Independent Living, Assisted Living, Memory Care, CCRC | Independent Living, Assisted Living, Memory Care, CCRC | PASS | 8 | 0 | PASS | PASS |
| Light Assistance | Assisted Living, CCRC | Assisted Living, CCRC | PASS | 3 | 0 | PASS | PASS |
| Memory Support | Memory Care, CCRC | Memory Care, CCRC | PASS | 0 | 0 | PASS | PASS |
| Complex Medical Needs | Skilled Nursing, Rehabilitation | Skilled Nursing, Rehabilitation | PASS | 32 | 0 | PASS | PASS |