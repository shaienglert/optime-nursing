# Recommendation Traceability Report

Generated At (UTC): 2026-07-20T01:52:00Z
Phase: 7

## Executive Truth

- End-to-end recommendation traceability matrix is generated for Top-5 accepted recommendations.
- Each recommendation now includes linked decision class, score, evidence counters, explanation text, and governance references.
- UNKNOWN evidence is explicitly retained in every trace row and mapped to clarify/investigate handling.

## Artifacts

- database/recommendation_traceability_matrix.json
- scripts/build_recommendation_traceability_matrix.py
- scripts/validate_recommendation_traceability.py

## Matrix Scope

- Scenario: PHASE6_TOP5_BASELINE
- Persona: Skilled Nursing
- Trace entries: 5
- Governed rules referenced: 23

## Trace Record Structure

Each recommendation trace row includes:

- recommendation_id, rank, facility identity
- decision classification and status
- score block (total/final/confidence)
- evidence block (verified/unknown counts + unknown handling rule)
- explanation block (rank reason + trace lines)
- governance block (policy + registry + authority inventory)

## Governance Alignment

- Classification for this output: OUR_RECOMMENDATION
- Status for this output: ACCEPTED
- hard_rejection_reasons in trace rows: empty by construction
- Candidate lifecycle carried from policy: GENERATED -> EVALUATED -> ACCEPTED_OR_REJECTED -> RANKED -> DISPLAYED

## Mechanical Validation Result

Validator:

- scripts/validate_recommendation_traceability.py

Result:

- PASS
- TRACE_ENTRIES = 5
- UNKNOWN_POSITIVE_ENTRIES = 5

## Operational Limit

- This phase establishes traceability wiring and matrix integrity.
- It does not independently attest to external clinical/professional outcome quality.
