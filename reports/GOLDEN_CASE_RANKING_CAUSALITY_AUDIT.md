# Golden Case Ranking Causality Audit

- Generated: 2026-07-20T20:54:34.890118Z
- Targeted parity run id: 20260720T204918Z

## Golden Case Top Lists

- ORIGINAL TOP 5: ['JOHN KNOX VILLAGE OF POMPANO BEACH', 'RIVER GARDEN HEBREW HOME FOR THE AGED', 'BISCAYNE HEALTH AND REHABILITATION CENTER', 'CORAL GABLES NURSING AND REHABILITATION CENTER', 'SANDS AT SOUTH BEACH CARE CENTER, THE']
- ASYMMETRIC ENRICHMENT TOP 5: ['BISCAYNE HEALTH AND REHABILITATION CENTER', 'CORAL GABLES NURSING AND REHABILITATION CENTER', 'Pinecrest Center for Rehabilitation and Healing', 'FOUNTAIN MANOR HEALTH & REHABILITATION CENTER', 'SERENITY BAY NURSING AND REHABILITATION CENTER']
- CORRECTED PROVEN-MATCH TOP 5: ['SANDS AT SOUTH BEACH CARE CENTER, THE', 'BISCAYNE HEALTH AND REHABILITATION CENTER', 'CORAL GABLES NURSING AND REHABILITATION CENTER', 'Pinecrest Center for Rehabilitation and Healing', 'FOUNTAIN MANOR HEALTH & REHABILITATION CENTER']
- EVIDENCE-PARITY TOP 5: ['SANDS AT SOUTH BEACH CARE CENTER, THE', 'BISCAYNE HEALTH AND REHABILITATION CENTER', 'CORAL GABLES NURSING AND REHABILITATION CENTER', 'Pinecrest Center for Rehabilitation and Healing', 'FOUNTAIN MANOR HEALTH & REHABILITATION CENTER']

## High-Potential / Needs-Verification

- None in current corrected top cohort.

## Movement Causality

### JOHN KNOX VILLAGE OF POMPANO BEACH
- Classification: COHORT_SELECTION_ARTIFACT
- In Miami-54 cohort: False
- Fact: No NEW fact persisted for this facility in targeted parity run.

### RIVER GARDEN HEBREW HOME FOR THE AGED
- Classification: COHORT_SELECTION_ARTIFACT
- In Miami-54 cohort: False
- Fact: No NEW fact persisted for this facility in targeted parity run.

### SANDS AT SOUTH BEACH CARE CENTER, THE
- Classification: EVIDENCE_COVERAGE_BIAS
- In Miami-54 cohort: True
- Fact: No NEW fact persisted for this facility in targeted parity run.

### Pinecrest Center for Rehabilitation and Healing
- Classification: EVIDENCE_COVERAGE_BIAS
- In Miami-54 cohort: True
- Fact: No NEW fact persisted for this facility in targeted parity run.

### FOUNTAIN MANOR HEALTH & REHABILITATION CENTER
- Classification: EVIDENCE_COVERAGE_BIAS
- In Miami-54 cohort: True
- Fact: No NEW fact persisted for this facility in targeted parity run.

### SERENITY BAY NURSING AND REHABILITATION CENTER
- Classification: EVIDENCE_COVERAGE_BIAS
- In Miami-54 cohort: True
- Fact: No NEW fact persisted for this facility in targeted parity run.

## Evidence Parity Governance

- Evidence coverage bias found: True
- Scoring bug found: False
- Missing-data penalty found: False
- Evidence parity guard: PASS

## Targeted Parity Enrichment

- Mode: REPLAY_FROM_LATEST_DB_RUN
- Facilities targeted: 12
- Live sources attempted: 0
- Live sources successfully reached: 0
- High-value new facts found: 0
- RAN_CONNECTED_NO_NEW_VALUE: 205
- SOURCE_GEO_BLOCKED_OR_SUSPECTED: 6
- SOURCE_ACCESS_FAILED: 4
- SOURCE_RATE_LIMITED: 3

## Official Website Resolution

- VERIFIED_OFFICIAL: 44/54
- PROBABLE_OFFICIAL: 0/54
- UNRESOLVED: 10/54

## Tier-1 Unknown Resolution Queue

- medicare_medicaid_acceptance: unknown=52 decision_value=5 resolvability=3 source=Provider websites and validated secondary sources authority=GOVERNMENT/OFFICIAL owner=clinical_knowledge cadence=weekly
- ownership_operator: unknown=44 decision_value=4 resolvability=4 source=CMS/official provider websites authority=GOVERNMENT/OFFICIAL owner=provider_intelligence cadence=weekly
- official_website: unknown=42 decision_value=4 resolvability=4 source=CMS/official provider websites authority=GOVERNMENT/OFFICIAL owner=provider_intelligence cadence=weekly
- current_private_pay_price: unknown=52 decision_value=5 resolvability=2 source=CMS/official provider websites authority=OFFICIAL_PROVIDER/REPUTABLE_SECONDARY owner=provider_intelligence cadence=weekly
- admissions_eligibility: unknown=54 decision_value=4 resolvability=2 source=Provider websites and validated secondary sources authority=OFFICIAL_PROVIDER/REPUTABLE_SECONDARY owner=clinical_knowledge cadence=daily
- employee_staff_sentiment: unknown=54 decision_value=3 resolvability=2 source=Provider websites and validated secondary sources authority=OFFICIAL_PROVIDER/REPUTABLE_SECONDARY owner=family_experience cadence=weekly
- family_satisfaction: unknown=53 decision_value=3 resolvability=2 source=Provider websites and validated secondary sources authority=OFFICIAL_PROVIDER/REPUTABLE_SECONDARY owner=family_experience cadence=weekly
- ot: unknown=15 decision_value=5 resolvability=4 source=Provider websites and validated secondary sources authority=OFFICIAL_PROVIDER/REPUTABLE_SECONDARY owner=clinical_knowledge cadence=weekly

## Regression Tests

- Status: PASS
