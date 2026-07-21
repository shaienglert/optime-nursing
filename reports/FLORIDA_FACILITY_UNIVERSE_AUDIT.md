# Florida Facility Universe Audit

Generated At (UTC): 2026-07-21T12:24:55.934Z
Run Status: PARTIAL

## Principle Impact Check

- RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-004, PR-005, PR-007, PR-008
- DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
- OWNER APPROVAL REQUIRED? NO
- CLASSIFICATION: B. Implementation Completion

## Counts

- Total authoritative Florida records ingested: 694
- Active licensed facilities: NOT VERIFIED - SOURCE ACCESS FAILED
- Inactive facilities: NOT VERIFIED - SOURCE ACCESS FAILED
- CMS-linked facilities: 694
- AHCA-only facilities: NOT VERIFIED - SOURCE ACCESS FAILED

### Breakdown By Raw Facility/Provider Type

| Type | Count |
| --- | --- |
| Nursing Home (CMS Provider Information 4pq5-n9py) | 694 |

### Breakdown By Provider Role

| Role | Count |
| --- | --- |
| RESIDENTIAL_CANDIDATE | 694 |

## Required Residential Category Counts

- Nursing Homes: 694
- Assisted Living: NOT VERIFIED - SOURCE ACCESS FAILED
- Adult Family Care Homes: NOT VERIFIED - SOURCE ACCESS FAILED

## CMS Crosswalk

- exact_matched_count: 694
- unmatched_count: 0
- ambiguous_matches: 0
- duplicate_conflicts: 0

## Source Access Failures

| Source | URL | Reason |
| --- | --- | --- |
| FloridaHealthFinder Root | https://quality.healthfinder.fl.gov/ | HTTP 403 bot/challenge blocked |
| FloridaHealthFinder Facility Search | https://quality.healthfinder.fl.gov/Facility-Provider/ | HTTP 403 bot/challenge blocked |
| FloridaHealthFinder County Search | https://quality.healthfinder.fl.gov/Facility-Provider/CountySearch/ | HTTP 403 bot/challenge blocked |
| AHCA Root | https://ahca.myflorida.com/ | HTTP 403 bot/challenge blocked |
| AHCA Bureau of Health Facility Regulation | https://ahca.myflorida.com/health-care-policy-and-oversight/bureau-of-health-facility-regulation/ | HTTP 403 bot/challenge blocked |
| FloridaHealthFinder robots | https://quality.healthfinder.fl.gov/robots.txt | HTTP 403 bot/challenge blocked |

## Top-10 Verification Readiness Contract

```json
{
  "version": "1.0.0",
  "sections": {
    "case_summary_template": "We are looking for the best match for our client based on verified needs and constraints.",
    "unknown_questions_required": true,
    "known_fact_confirmation_required": true,
    "availability_questions_required": [
      "appropriate unit/bed availability",
      "earliest admission",
      "room/bed type",
      "waiting list",
      "current price/fees",
      "promotions"
    ]
  },
  "payload_fields": [
    "facility_id",
    "facility_name",
    "case_id",
    "case_summary",
    "unknown_parameters",
    "known_parameters_to_confirm",
    "availability_questions",
    "response_timestamp",
    "respondent_role",
    "evidence_source"
  ]
}
```

## Customer Disclosure Requirement

Recommendations are based on the information you provided and the data currently available to OPTIME at the time of analysis. Some important details may still need verification before a final decision is made. Current bed availability and admission timing must always be confirmed directly with each facility. OPTIME can contact the most relevant facilities to verify missing details and real-time availability for your case. If new verified information is received, the recommendation table and ordering may change to reflect the stronger evidence.

## Validation

| Check | Status | Detail |
| --- | --- | --- |
| UNKNOWN never became NO | PASS | No UNKNOWN mapped to VERIFIED_NO |
| Facility Type did not become a blanket exclusion rule | PASS | Records retained across available provider types |
| Unit/program capabilities are preserved | PASS | Scope field preserved on every parameter evidence row |
| Generic completeness does not improve ranking | PASS | No ranking computation changed in this pipeline |
| No commercial field affects organic ranking | PASS | No commercial fields read or written to ranking logic |
| Availability is not inferred | PASS | All dynamic availability fields remain UNKNOWN |
| Counts come from authoritative ingested records | PASS | Counts derived from ingested CMS authoritative datasets |
| No duplicate canonical facilities were silently created | PASS | Canonical IDs unique |
| No existing PASS artifacts were falsely overwritten | PASS | Only Florida-specific new audit files were written |
| No product ranking/scoring semantics changed | PASS | No ranking/scoring implementation files changed |
