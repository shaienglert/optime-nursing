# Targeted Research Zero-Resolution Root Cause

## Executive Conclusion

WHY DID 35 SUCCESSFUL REQUESTS RESOLVE 0 UNKNOWNS? All 35 were source-level successes but none produced UNKNOWN->VERIFIED_* transitions for canonical decision fields; extracted facts were already known (UNCHANGED/STALE_REFRESHED).

## Root Causes

- PRIMARY: Telemetry bug: unknown_resolved previously used a heuristic before/after state counter (activity+capability+license+domain side effects), not canonical field transition evidence.
- SECONDARY: Run-level provenance bug: claim rows were stored under per-claim timestamp run_id, not the discovery run_id.
- SECONDARY: Success semantics conflation: source connectivity success was conflated with research/intelligence success.
- SECONDARY: Extractor capability limits for several decision fields (mobility_transfer_assistance, medication_management, availability).

## Counts By Failure Stage

- RESOLVED: 0
- NO_RELEVANT_INFORMATION: 0
- EXTRACTION_FAILURE: 0
- IDENTITY_FAILURE: 0
- FIELD_MAPPING_FAILURE: 0
- VERIFICATION_FAILURE: 0
- PERSISTENCE_FAILURE: 0
- SOURCE_ACCESS_FAILURE: 5
- OTHER: 35

## 59 False-Resolution Cause

- unknown_resolved incremented via before-after heuristic deltas and STALE_REFRESHED path, even without canonical UNKNOWN->VERIFIED_* transitions.

## Fixes Made

- Persist claim logs with the parent discovery run_id.
- Count unknown_resolved only for canonical UNKNOWN->VERIFIED_YES/VERIFIED_NO/VERIFIED_VALUE/LIMITED transitions with evidence-backed persisted claims.
- Separate telemetry: source_access_successes, content_retrieval_successes, relevant_evidence_found, verified_fact_created, unknown_resolved.
- Map extracted clinical_services into capability fields used by decision coverage.

## Small Proof Set Results

- Targeted questions: 20
- Source access successes: 13
- Content retrieval successes: 16
- Relevant evidence found: 13
- Verified facts created: 0
- Unknowns actually resolved: 0
- No information found: 20
- Technical failures: 3

## Regression Tests

- unknown_resolved_matches_transition_counter: PASS
- claims_linked_to_same_run_id: PASS
- source_access_alone_not_counted_as_resolution: PASS

## What Engine Can Do Today

- Targeted field discovery: PARTIAL
- Can do:
  - Fetch authoritative CMS datasets and persist summaries with provenance.
  - Parse selected official website keywords for services/activities/nutrition/pricing.
  - Persist evidence and knowledge objects with verification metadata.
- Cannot yet do:
  - Reliable deep extraction for mobility transfer assistance and medication management from varied site language.
  - Guaranteed extraction when official websites are blocked/rate-limited.
  - Broad semantic inference beyond current keyword and fixed-claim extractors.

## Next 5 Highest-Value Improvements

- Field-specific extractors for mobility transfer, medication management, availability, language/cultural support.
- Persist extractor diagnostics per request (matched phrases, rejected candidates, mapping reasons).
- Add identity alias matching diagnostics for provider/operator name variants.
- Add parser fallback for blocked official websites to governed alternates where permitted.
- Regression tests for run_id provenance and unknown_resolved strict counting.
