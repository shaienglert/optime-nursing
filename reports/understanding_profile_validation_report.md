# Understanding Profile Validation Report

Overall Status: **FAIL**

## Validation Summary

- Build PASS: **FAIL**
- Simulation PASS: **PASS**
- No regression in ranking engine: **PASS**

## Understanding Simulation Checks

| Check | Verdict | Note |
| --- | --- | --- |
| Critical-domain penalty check | PASS | Care-complete score 42% vs missing-care score 34% |
| Status text range mapping | PASS | Low=Getting to know you; High=Ready for advisor-level recommendations |
| Color progression mapping | PASS | Low=Red; High=Blue-green |
| Journey icon and couple visualization | PASS | Person=👵👴; Active journey icons=6 |
| Recommendation confidence separated from understanding score | PASS | Understanding=87%; Confidence=93% |

## Regression Guard Checks

| Command | Exit Code | Detected Status | Verdict |
| --- | --- | --- | --- |
| node scripts/run_dynamic_persona_simulation_audit.cjs | 0 | PASS | PASS |
| node scripts/run_human_advisor_benchmark.cjs | 0 | PASS | PASS |
