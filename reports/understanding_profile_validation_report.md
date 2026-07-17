# Understanding Profile Validation Report

Overall Status: **PASS**

## Validation Summary

- Build PASS: **PASS**
- Simulation PASS: **PASS**
- No regression in ranking engine: **PASS**

## Understanding Simulation Checks

| Check | Verdict | Note |
| --- | --- | --- |
| Understanding score reflects answered domains over volume | PASS | Rich-profile score 66% vs sparse-profile score 38% |
| Status text range mapping | PASS | Low=Getting to know you; High=Ready for advisor-level recommendations |
| Color progression mapping | PASS | Low=Red; High=Blue-green |
| Journey icon and couple visualization | PASS | Person=👵👴; Active journey icons=6 |
| Recommendation confidence is computed and bounded | PASS | Understanding=100%; Confidence=100% |
| Validation example: all domains answered with distance intentionally ignored | PASS | Corrected understanding score=100% |
| Distance not used does not reduce understanding score | PASS | Family proximity coverage=100; intentional_omission=true |
| Distance not used does not reduce recommendation confidence | PASS | Ignored distance confidence=100% vs explicit distance=100% |
| No religion preference gets full understanding credit | PASS | Cultural coverage=100; state=PROVIDED |
| No language preference gets full understanding credit | PASS | Cultural coverage=100; language no-preference counted as NOT_IMPORTANT |
| No pet preference gets full understanding credit | PASS | Lifestyle coverage=100; state=PROVIDED |

## Regression Guard Checks

| Command | Exit Code | Detected Status | Verdict |
| --- | --- | --- | --- |
| node scripts/run_dynamic_persona_simulation_audit.cjs | 0 | PASS | PASS |
| node scripts/run_human_advisor_benchmark.cjs | 0 | PASS | PASS |
