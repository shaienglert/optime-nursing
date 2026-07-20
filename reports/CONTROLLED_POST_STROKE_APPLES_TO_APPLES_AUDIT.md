# Controlled Post-Stroke Apples-to-Apples Audit

- Generated: 2026-07-20T21:43:42.544Z
- Benchmark validity: VALID APPLES-TO-APPLES
- Engine commit: b97382f0dfdb94ae2cce2dd6f2d3a58676e03844
- Scoring version: SCORING_SHA256_fdedca1dbdc86614
- Ranking version: RANKING_SHA256_323005da543f5cdd
- Case ID: POST_STROKE_MIAMI_001
- Case fingerprint: 99ad8716065c3d2925eaf650d8711bdee14db8cf4cb657adb02eed5d7673d016

## Validity Gate

- Same exact case contract: PASS
- Same case fingerprint: PASS
- Same engine commit/version: PASS
- Same candidate universe rules: PASS
- Same evidence checklist: PASS
- Same source authority rules: PASS
- Same ranking run: PASS
- Full traces exist for all key facilities: PASS
- No silent removal by enrichment cohort: PASS
- Unknown/access failures preserved: PASS

## Candidate Universe

- Discovered: 100
- Ranked: 10
- Rejected: 90

## Critical Tests

### JOHN KNOX VILLAGE OF POMPANO BEACH
- Eligible under exact frozen case: NO
- Exclusion rule: This community does not provide the required level of daily support.
- Verified negative case-relevant evidence: NO
- What prevents higher rank: This community does not provide the required level of daily support.

### RIVER GARDEN HEBREW HOME FOR THE AGED
- Eligible under exact frozen case: NO
- Exclusion rule: This community does not provide the required level of daily support.
- Verified negative case-relevant evidence: NO
- What prevents higher rank: This community does not provide the required level of daily support.

### SANDS AT SOUTH BEACH CARE CENTER, THE
- Eligible under exact frozen case: YES
- Rank under same run: 1
- Verified negative case-relevant evidence: NO
- What prevents higher rank: Already rank #1 in this controlled run.

### BISCAYNE HEALTH AND REHABILITATION CENTER
- Eligible under exact frozen case: YES
- Rank under same run: 2
- Verified negative case-relevant evidence: NO
- What prevents higher rank: Lower governed/proven/coverage comparator outcome than higher-ranked facility.

### CORAL GABLES NURSING AND REHABILITATION CENTER
- Eligible under exact frozen case: YES
- Rank under same run: 3
- Verified negative case-relevant evidence: NO
- What prevents higher rank: Lower governed/proven/coverage comparator outcome than higher-ranked facility.

### PINECREST CENTER FOR REHABILITATION AND HEALING
- Eligible under exact frozen case: YES
- Rank under same run: 4
- Verified negative case-relevant evidence: NO
- What prevents higher rank: Lower governed/proven/coverage comparator outcome than higher-ranked facility.

### FOUNTAIN MANOR HEALTH & REHABILITATION CENTER
- Eligible under exact frozen case: YES
- Rank under same run: 5
- Verified negative case-relevant evidence: NO
- What prevents higher rank: Lower governed/proven/coverage comparator outcome than higher-ranked facility.

## Sands Verification

- Current rank: 1
- Evidence confidence: LOW
- Case-relevant coverage: 14%
- Critical coverage: 25%
- Critical unknown count: 6
- #1 reason: {"decisive_rule":"GOVERNED_ALIGNMENT","reason":"Ordered above next by GOVERNED_ALIGNMENT.","comparator_deltas":{"governed_fit_delta":1,"proven_match_delta":0,"evidence_coverage_delta":7,"final_match_delta":0},"tie_break_deltas":{"preference_bonus_delta":1,"clinical_quality_delta":0,"family_fit_delta":-1.5210000000000008}}
- Strongest proven fit vs tie-break: TIE_BREAK_OR_OTHER

## Decision Table (Sorted by Current Controlled Rank)

| FACILITY | ELIGIBLE | RANK | QUALITY | PERSONALIZED MATCH | PROVEN MATCH | POTENTIAL MATCH | EVIDENCE CONFIDENCE | CASE-RELEVANT COVERAGE | CRITICAL COVERAGE | CRITICAL UNKNOWNS | VERIFIED POSITIVES | VERIFIED NEGATIVES | SOURCE ACCESS FAILURES | LEGACY HEURISTIC EFFECT | WHY THIS RANK |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SANDS AT SOUTH BEACH CARE CENTER, THE | YES | 1 | 100 | 100 | 100 | NOT_CALCULABLE | LOW | 14% | 25% | 6 | 2 | 0 | RAN_CONNECTED_NO_NEW_VALUE:3, SOURCE_GEO_BLOCKED_OR_SUSPECTED:1 | value=100; affected=false | GOVERNED_ALIGNMENT: Ordered above next by GOVERNED_ALIGNMENT. |
| BISCAYNE HEALTH AND REHABILITATION CENTER | YES | 2 | 100 | 100 | 100 | 100 | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:4 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| CORAL GABLES NURSING AND REHABILITATION CENTER | YES | 3 | 100 | 100 | 100 | 100 | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:3, SOURCE_RATE_LIMITED:1 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| Pinecrest Center for Rehabilitation and Healing | YES | 4 | 92.99472 | 100 | 100 | 100 | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:3, SOURCE_GEO_BLOCKED_OR_SUSPECTED:1 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | YES | 5 | 92.95168 | 100 | 100 | 100 | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:4 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| MIAMI JEWISH HEALTH SYSTEMS, INC | YES | 6 | 85.32368 | 100 | 100 | NOT_CALCULABLE | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:3, SOURCE_GEO_BLOCKED_OR_SUSPECTED:1 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| PINES NURSING HOME | YES | 7 | 76.6152 | 100 | 100 | NOT_CALCULABLE | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:4 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| SERENITY BAY NURSING AND REHABILITATION CENTER | YES | 8 | 74.00906666666667 | 100 | 100 | 100 | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:4 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| VILLA MARIA NURSING CENTER | YES | 9 | 65.72576 | 100 | 100 | NOT_CALCULABLE | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:3, SOURCE_ACCESS_FAILED:1 | value=100; affected=false | TIE_BREAK: Ordered above next by TIE_BREAK. |
| NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | YES | 10 | 55.012 | 100 | 100 | 100 | LOW | 7% | 13% | 7 | 1 | 0 | RAN_CONNECTED_NO_NEW_VALUE:4 | value=100; affected=false | LAST_RANKED: No next facility. |

## Connectivity Status Snapshot

- Lookup mode: REUSE_EXISTING_EVIDENCE_WITH_LOCAL_DB_STATUS
- Latest run id: 20260720T214443Z
- RAN_CONNECTED_NO_NEW_VALUE: 205
- SOURCE_ACCESS_FAILED: 4
- SOURCE_GEO_BLOCKED_OR_SUSPECTED: 6
- SOURCE_RATE_LIMITED: 3
