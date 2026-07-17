# Understanding Score Root Cause Report

Current score calculation (legacy): **70%**
Expected score calculation (corrected): **87%**
Delta explanation: corrected - legacy = **17%**
Corrected score: **87%**
Corrected recommendation confidence: **83%**

## Per-domain contribution report

| Domain | Coverage Score | Reason | Penalty Applied | Intentional Omission | Coverage State |
| --- | --- | --- | --- | --- | --- |
| Care needs | 50 | Some care understanding signals are still unknown. | 13 | false | PROVIDED |
| Lifestyle | 100 | Lifestyle understanding is complete. | 0 | false | PROVIDED |
| Social preferences | 100 | Social preference understanding is complete. | 0 | false | PROVIDED |
| Financial profile | 100 | Budget information is provided. | 0 | false | PROVIDED |
| Cultural preferences | 100 | Religion/language was explicitly marked as not important and receives full coverage credit for those signals. | 0 | true | PROVIDED |
| Family proximity | 100 | Distance was intentionally marked as not used; no understanding penalty is applied. | 0 | true | NOT_IMPORTANT |
| Future care planning | 100 | Future care planning is fully specified. | 0 | false | PROVIDED |

## Validation example

- Inputs: all domains answered, distance intentionally ignored
- Expected: Understanding Score >= 90
- Actual: **87%**

## Exact penalties responsible for remaining reduction

| Domain | Penalty | Reason |
| --- | --- | --- |
| Care needs | 13 | Some care understanding signals are still unknown. |
