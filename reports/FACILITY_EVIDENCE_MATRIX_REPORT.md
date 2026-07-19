# Facility Evidence Matrix Report

Generated At (UTC): 2026-07-20T01:28:00Z
Phase: 4

## Executive Truth

- A canonical evidence matrix schema is established.
- A runtime evidence snapshot is generated from the operational SQLite database.
- UNKNOWN is preserved as UNKNOWN and is never converted to NO.
- Source hierarchy is explicit: SOURCE_OF_TRUTH > PROVIDER_VERIFIED > INTELLIGENCE_SIGNAL > UNVERIFIED.

## Artifacts

- database/facility_evidence_matrix_schema.json
- database/facility_evidence_matrix_snapshot.json
- scripts/build_facility_evidence_matrix_snapshot.py
- scripts/validate_facility_evidence_matrix.py

## Scope and Coverage

From current generated snapshot:

- Runtime FL facilities: 100
- Canonical statewide facilities: 713
- Canonical county coverage: 64/67
- Missing counties: Glades, Liberty, Union

## Verification State Distribution

- UNKNOWN: 99
- CONFLICTED: 1

Interpretation:

- The current runtime sample is mostly unresolved in verification memory terms.
- A small conflict signal exists and must stay under review.

## Source Hierarchy Distribution

- SOURCE_OF_TRUTH: 100

Interpretation:

- Runtime set currently maps to authoritative CMS-linked identity coverage.

## Unknown Handling Policy

Required behavior is enforced in schema and snapshot policy:

- unknown_is_not_no = true
- insufficient_evidence_actions = [CLARIFY, INVESTIGATE, UNKNOWN]

## Mechanical Validation Result

Validator:

- scripts/validate_facility_evidence_matrix.py

Result:

- PASS

Warning:

- All runtime facilities currently have unknown confidence_level.

## Operational Boundary

- This phase provides data contract and current-state evidence metrics.
- It does not claim completion of provider outreach or manual conflict resolution.
