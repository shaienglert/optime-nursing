# Live verification follow-up — 22 September 2026

Overall acceptance: NOT PASSED. This supersedes the earlier handoff report’s deployment and permission status.

## Published changes

PRs #342–347 preserve the original authored integration commits and implement B1–B5. All are merged. PR #349 (confirmation navigation) and PR #350 (bounded semantic packet repair) are also merged. Production frontend and Render backend were deployed; backend deployment dep-dap585740ujc73bk5b8g is LIVE at commit 14cda672df8b3015fe13689bdf45a38c7f06b0cc. No direct main push was performed by this agent.

## Validation

- Part A baseline: 798 passed, 2 failed under the same final exclusion policy. Part A: 817 passed, 0 failed; 20 known exclusions.
- B1–B5 combined: 828 passed. With packet-repair regressions: 834 passed, 0 unexpected failures; same 20 exclusions.
- Part A frozen parity: 17 cases; 391 additions, all allowed; 0 unexpected differences.
- Packet-repair frozen parity versus combined B1–B5: all 17 identical; 0 differences. These frozen cases do not prove live model reliability.
- Initial frontend TypeScript passed; Vitest: 12 files, 40 tests passed. Latest PR #350: all 13 reported GitHub checks passed, including full suite, parity, browser E2E and contract guards.
- PR #348 remains open: its synthetic pilot browser suite passed 8 of 10; two recommendation requests returned HTTP 502 after roughly five minutes. This is not a green browser acceptance run.

## Exact live failure evidence

Render logged SEMANTIC_AI_CLARIFICATION_WITHOUT_BLOCKING_QUESTION, SEMANTIC_AI_REPAIR_CLARIFICATION_WITHOUT_QUESTION and SEMANTIC_AI_INVALID_IMPORTANCE. A fresh dialysis API request returned HTTP 200 with semantic_ai.status FAILED, canonical phase SYSTEM_BLOCKED, and dialysis_arrangements REQUIRED. Thus correct dialysis mapping does not imply a working interview.

PR #350 adds one final AI-authored correction attempt for malformed packets, followed by the same validation and minimum-information guards. It does not default to READY. Six focused tests passed. A fresh production browser dialysis intake after deployment reached confirmation showing Dialysis three times a week, medication help and independent transfers. However the confirmation action still did not complete the results journey in that browser session. Additional semantic failure log entries also exist after deployment; their case association was not established. Recovery is not claimed universal.

PR #349 succeeded in a production preview with the live backend, and two production cases reached results. Other confirmation pages remained unresponsive to confirmation, change-answers and some header interactions. The remaining cause (application or browser-control behavior) is unresolved. Direct navigation to Results after dialysis confirmation redirected to intake, so confirmed completion had not persisted. This is an acceptance failure, not a passing zero-result outcome.

## Ten live browser cases

The narratives were reconstructed from the owner’s descriptions, with explicit budgets and some negative facts. The original run_ten.py/ten_cases.py files were unavailable. No AI answer was substituted in these live browser journeys. Original first pass: nine confirmation screens, one semantic error; none reached results. Follow-up outcomes below distinguish successful results from a blocked journey.

| Case | Observed understanding | Furthest verified live outcome | Shown recommendation cards | End-to-end check |
|---|---|---|---:|---|
| Independent/social | Independent, no memory concern; social preference absent from summary | Confirmation; independent preview separately reached evidence-gap result | Not measured on production results | FAIL |
| Bathing/dressing | Bathing shown; transfers No; dressing absent from summary | Results, missing-evidence disclosure | 0 | Reached results; intake completeness not passed |
| Falls/transfers | One-person transfers and repeated falls recognized | Confirmation | Not measured | FAIL |
| Mild forgetfulness/medication | Medication help, independent transfers; added complex medication management | Results, missing-evidence disclosure | 0 | Intake fidelity FAIL |
| Dementia/wandering | Secure setting/wandering in initial summary; later repeat omitted those summary fields | Confirmation | Not measured | FAIL |
| Post-surgery rehab | PT/OT in coordination text; invented permanent equipment, omitted Medicare/timing from summary | Confirmation | Not measured | FAIL |
| Dialysis | Initial semantic failure; fresh post-deploy run correctly showed dialysis, medication help, independent transfers | Confirmation after repair | Not measured | FAIL until results/report complete |
| Oxygen/wound | Wound care and daily dressing frequency recognized; complex medication management added | Confirmation | Not measured | FAIL |
| Low budget/Medicaid | 3000/month and application pending recognized | Confirmation | Not measured | FAIL |
| Couple/different needs | Couple recognized; nursing supervision added; asymmetric needs not clear in summary | Confirmation | Not measured | FAIL |

The browser DOM did not expose canonical MUST records or phase on blocked confirmation pages. Those values cannot be inferred from a summary screen. The next table is the separate local reconstructed API verification with interview READY mocked, not live-AI evidence. Full need and MUST records are in the prior reconstructed-ten-results.json.

| Case | Local needs | Local MUST keys | Local phase | Shown | Checks |
|---|---|---|---|---:|---|
| independent_social | current_price:MEDIUM, memory_care:PREFERENCE, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS |
| bathing_dressing | adl_support:HIGH, current_price:MEDIUM, memory_care:PREFERENCE, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, no_invented_transfers:PASS |
| falls_transfers | adl_support:HIGH, transfer_assistance:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, transfer_high:PASS |
| mild_forgetfulness | medication_support:HIGH, current_price:MEDIUM, memory_care:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, MEDICATION_SUPPORT_AVAILABLE, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, no_invented_transfers:PASS, medication_without_adl:PASS |
| dementia_wandering | memory_care:REQUIRED, adl_support:HIGH, dementia_alz_programs:HIGH, current_price:MEDIUM, transfer_assistance:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, SECURE_MEMORY_CARE_CONFIRMED, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, memory_need:PASS |
| post_surgery_rehab | adl_support:HIGH, ot:HIGH, pt:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, REHAB_PATH_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT | CLIENT_INPUT_REQUIRED | 0 | all_http_200:PASS, no_pending_recommendations:PASS, pt_and_ot:PASS |
| dialysis | dialysis_arrangements:REQUIRED, medication_support:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, MEDICATION_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, no_invented_transfers:PASS, medication_without_adl:PASS, dialysis_required:PASS |
| oxygen_wound | adl_support:HIGH, medication_support:HIGH, respiratory_trach_vent:HIGH, wound_care:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, wound_high:PASS |
| low_budget_medicaid | adl_support:HIGH, current_price:MEDIUM, medicaid_attributes:PREFERENCE, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS |
| couple_different_needs | adl_support:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, COUPLE_CORESIDENCE, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200:PASS, no_pending_recommendations:PASS, couple:PASS |

## Remaining work and limitations

Production acceptance is still blocked by confirmation persistence/navigation and intermittent malformed live AI output. Resolve the browser/application distinction, then repeat the full ten journeys and personal reports. Supplemental terminal API checks were interrupted by an explicit network-policy block; only the first two profile calls and one complete recommendation response were saved. No claim of ten successful live API cases is made. Continuous-oxygen mapping, URL personal data, provider authentication, licensing expiry and ranking weights/tie-breakers remain outside this task. Empty results do not establish ranking determinism.

## Principle Impact Check

PR-001, PR-002, PR-003, PR-005, PR-008. Documentation and implementation recovery under existing principles; no principle change. Owner approval required: NO. Original B1–B4 semantic changes were explicitly owner-approved.
