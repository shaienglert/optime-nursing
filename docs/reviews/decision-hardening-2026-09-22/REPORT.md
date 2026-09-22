# Decision authority hardening — 2026-09-22

Committed locally; no new PR was opened. Terminal Git cannot authenticate: `could not read Username for 'https://github.com'`. The connected GitHub commit API does not accept author metadata; recreating the commits with it would violate the requested authorship preservation. No main push, merge, or deployment was performed.

## Principle Impact Check

AGENTS.md and the canonical principles were read. RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-008, PR-009. DOES THIS CHANGE ALTER ANY PRINCIPLE? NO. Classification: implementation bugs/completion. OWNER APPROVAL REQUIRED? NO for Part A/B5; explicit owner authorization for the B1–B4 semantic corrections is recorded in the task. Prohibited URL, provider-authentication, oxygen-mapping, license-semantics, ranking-weight and tie-breaker changes were not made.

## Part A

Base: 74428ba063aaf193e7015fe365bd60910b2c0493. The original audit commit 73645f48 was cherry-picked with both conflicts resolved, then all six patches applied preserving authorship. Patch SHA256: 39f67c271a300bf49894ef3f451b3d5c9787dbdec5107b5c0255fc8ab37f3e2c.

Two additional integration commits provide xdist database isolation, current HTTP test dependencies, frontend type correction, removal of passing exclusions, and the precise allowance for the three approved field additions in the parity gate. #338/#339 behavior and #340 scorer-import intent are retained.

Python 3.12.14 with backend/requirements.txt; PYTHONHASHSEED=0, OPTIME_CANONICAL_MARKET=las-vegas, PYTHONPATH=backend:.:scripts. The repository resolver selected Python. Dependencies were installed into an isolated target directory; no new virtual environment was created.

| Check | Before | After |
|---|---:|---:|
| Backend, final identical 20-test exclusion policy | 798 passed / 2 failed | 817 passed / 0 failed |
| Backend, original supplied exclusion policy | 778 passed / 1 failed | 796 passed / 0 failed |
| Frozen parity cases | 17 | 17 completed |
| Raw parity differences | — | 391 |
| Allowed additive differences | — | 391 |
| Unexpected differences | — | 0 |
| Frontend TypeScript | — | exit 0 |
| Frontend Vitest, browser tests excluded | — | 12 files / 40 tests passed |

The two baseline failures under the final policy were the repaired recommendation-leak test and competitive-intelligence changed-content persistence. Rechecking original exclusions produced 21 passes and 20 failures; the passing tests were restored to the full suite. The 20 remaining failures are still documented in known_failures.txt.

Parity: TOTAL_DIFFERENCES=391; ALLOWED_ADDITIONS=391; UNEXPECTED_DIFFERENCES=0. All additions are HTTP recommendations decision_id, intake_resolution, or source_backed_conflict_keys. Normalized rankings and database writes otherwise match.

## Separate semantic changes

| Item | Fixed-case differences | Cases changed / 17 | Additional reproducer differences | Focused result |
|---|---:|---:|---:|---|
| B1 medication/bathing mapping | 7879 | 14 | covered by fixed cases | 14 passed |
| B2 present-tense couple | 0 | 0 | 16642 | 7 passed |
| B3 pressure wound | 0 | 0 | 11792 | 3 passed |
| B4 bed/shower transfers | 0 | 0 | 661 | 3 passed |
| B5 pending MUST visibility | 1358 | 10 | covered by fixed cases | 32 initial focused tests passed |

Counts are structural JSON differences, not numbers of decisions or facilities. Exact diffs are included as diff-b*.json. B1 changes extracted needs and derived audit/DB payloads without changing facility ID lists in the 17 cases. B2 changes SINGLE_OR_UNKNOWN to COUPLE and adds co-residence constraints. B3 adds wound_care HIGH. B4 raises the reproduced transfer need from legacy-inferred MEDIUM to stated HIGH. B5 retains pending MUST candidates for research but excludes them from ranking and recommendations. In the frozen skilled-nursing case, five displayed facilities become zero and PROVISIONAL_RECOMMENDATION becomes EVIDENCE_COLLECTION.

**Merge B5 before B3.** The isolated B3 reproducer reaches the existing pending-MUST recommendation bug (five displayed SNFs); the combined B1–B5 run correctly keeps it in EVIDENCE_COLLECTION. The B3 review must remain blocked until B5 is integrated. The isolated B3 branch is not safe to deploy independently.

Combined full suite: **828 passed, zero failures outside the 20 exclusions**. Six old tests initially failed because they assumed pending candidates could be recommendations. Strategy goldens now explicitly provide verified budget and medication evidence; the low-budget test requires withheld recommendations and disclosure. These failures were fixed, not excluded.

## Ten reconstructed API cases

The original claude-ten-case-run/run_ten.py and ten_cases.py were not attached or found. These fixtures are reconstructed from the owner's descriptions, not an exact rerun of the missing files. Each ran twice against the real Las Vegas catalog with fresh SQLite, interview AI fixed to READY, no AI key, actual downstream ranking fallback, and named background workers paused. This is not live-AI/browser acceptance.

All 60 profile/recommendation/personal-report requests returned HTTP 200. Each listed check passed in both repetitions. Displayed IDs were identical between repetitions: empty in every case. This does not establish ranking determinism for future verified candidates. Full need records, desired values, MUSTs and counts are in reconstructed-ten-results.json.

A memory_care PREFERENCE can mean desired NO and is not a requirement for memory placement. The rehab case remains CLIENT_INPUT_REQUIRED before semantic MUST evaluation.

| Case | Needs:level | Client + semantic MUST keys | Phase | Shown | Checks |
|---|---|---|---|---:|---|
| independent_social | current_price:MEDIUM, memory_care:PREFERENCE, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations: PASS ×2 |
| bathing_dressing | adl_support:HIGH, current_price:MEDIUM, memory_care:PREFERENCE, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, no_invented_transfers: PASS ×2 |
| falls_transfers | adl_support:HIGH, transfer_assistance:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, transfer_high: PASS ×2 |
| mild_forgetfulness | medication_support:HIGH, current_price:MEDIUM, memory_care:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, MEDICATION_SUPPORT_AVAILABLE, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, no_invented_transfers, medication_without_adl: PASS ×2 |
| dementia_wandering | memory_care:REQUIRED, adl_support:HIGH, dementia_alz_programs:HIGH, current_price:MEDIUM, transfer_assistance:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, SECURE_MEMORY_CARE_CONFIRMED, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, memory_need: PASS ×2 |
| post_surgery_rehab | adl_support:HIGH, ot:HIGH, pt:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, REHAB_PATH_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT | CLIENT_INPUT_REQUIRED | 0 | all_http_200, no_pending_recommendations, pt_and_ot: PASS ×2 |
| dialysis | dialysis_arrangements:REQUIRED, medication_support:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, MEDICATION_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, no_invented_transfers, medication_without_adl, dialysis_required: PASS ×2 |
| oxygen_wound | adl_support:HIGH, medication_support:HIGH, respiratory_trach_vent:HIGH, wound_care:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, wound_high: PASS ×2 |
| low_budget_medicaid | adl_support:HIGH, current_price:MEDIUM, medicaid_attributes:PREFERENCE, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations: PASS ×2 |
| couple_different_needs | adl_support:HIGH, current_price:MEDIUM, published_rates:PREFERENCE, transportation:PREFERENCE | LICENSE_CURRENTLY_VALID, LAS_VEGAS, COUPLE_CORESIDENCE, ADL_SUPPORT_AVAILABLE, NO_FORCED_MEMORY_PLACEMENT, SEMANTIC_BUDGET_VERIFICATION | EVIDENCE_COLLECTION | 0 | all_http_200, no_pending_recommendations, couple: PASS ×2 |

## Remaining limitations

- No new PR links: authenticated Git push preserving authorship is unavailable. All branches and review-ready PR bodies are included.
- The original acceptance files and live AI/browser acceptance remain unavailable.
- Mild forgetfulness still produces memory_care MEDIUM. Wound dressing text also triggers ADL HIGH. Continuous oxygen still maps to respiratory_trach_vent, as instructed. Passing these B1–B5 checks is not a blanket clinical-intake acceptance verdict.
- Existing PR #341 overlaps Part A/B1 and was not merged or modified.

## Branch heads

- claude/decision-authority-hardening: ca123698aa8d7bb0d9145d45e75b08a609a6870d
- fix/medication-intake-contract: b8c5b120d78e0aae062bef433995b3ba58fdc6f8
- fix/current-couple-household: 938a1583a98a00d2a4f7ba6ea76abff9c41f13c1
- fix/pressure-wound-intake: 6d8cd8503d0f44ab51c3319aacf1454f8d3929b2
- fix/bed-shower-transfers: 1c8d0c7db6fdbb81e5ad9d7c8f5c0f207e673e4e
- fix/pending-must-visibility: b6e9c9307b2c308706e7855d28e3ee4b3b1ad3b9
