# Candidate Governance Report

Generated At (UTC): 2026-07-20T01:39:00Z
Phase: 5

## Executive Truth

- Candidate lifecycle is now explicitly governed from generation to display.
- Accepted, rejected, and fallback classes are formally defined.
- UNKNOWN handling is bound to confidence impact, not forced negative scoring.
- Rejection taxonomy and summary buckets are enforced for traceability.

## Artifacts

- database/candidate_governance_policy.json
- scripts/validate_candidate_governance.py

## Candidate Lifecycle

- GENERATED
- EVALUATED
- ACCEPTED_OR_REJECTED
- RANKED
- DISPLAYED

## Candidate Classes

- accepted: no hard rejection reasons
- rejected: at least one hard rejection reason
- fallback: contingency display path when no accepted candidates

## Governance Boundaries

- Accepted filter uses hard rejection count equality to zero.
- Fallback display path exists and is gated by accepted list emptiness.
- Unknown checklist items are treated as confidence degradation only.
- Completeness tie-break is used after fit equivalence, not before.

## Rejection Taxonomy

- BUDGET
- CARE_LEVEL
- ACTIVITY_OR_LIFESTYLE
- FUTURE_CARE_PATH
- DISTANCE
- VERIFICATION
- UNKNOWN

## Mechanical Validation Result

Validator:

- scripts/validate_candidate_governance.py

Current result:

- PASS

## Known Limit

- This phase validates structural and rule-presence alignment in runtime source text.
- It does not independently benchmark recommendation quality outcomes.
