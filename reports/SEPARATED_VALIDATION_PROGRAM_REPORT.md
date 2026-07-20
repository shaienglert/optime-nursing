# Separated Validation Program Report

Generated At (UTC): 2026-07-20T02:08:00Z
Phase: 8

## Executive Truth

- Validation program is explicitly separated into two tracks:
  - Mechanical runtime validation (code/data contract checks)
  - External professional validation (independent review and outcome verification)
- Mechanical track is executable and currently PASS.
- External track is explicitly tracked as PARTIAL and not silently treated as complete.

## Artifacts

- database/validation_program_registry.json
- reports/VALIDATION_PROGRAM_STATUS.json
- scripts/run_separated_validation_program.py
- scripts/validate_separated_validation_program.py

## Mechanical Track

Mechanical validators executed:

- PHASE2_RULE_GOVERNANCE
- PHASE3_THREE_LAYER_MODEL
- PHASE4_EVIDENCE_MATRIX
- PHASE5_CANDIDATE_GOVERNANCE
- PHASE6_TOP5_DECISION_TABLE
- PHASE7_TRACEABILITY

Current overall status:

- PASS

## External Track

Tracked requirements:

- EXT-001: Independent professional review of MUST and recommendation boundaries (PENDING)
- EXT-002: Externally defined case-pack outcome comparison (NOT_AVAILABLE)
- EXT-003: Real-world longitudinal outcome verification (PENDING)

Current overall status:

- PARTIAL

## Mechanical Validation Result

Validator:

- scripts/validate_separated_validation_program.py

Result:

- PASS
- External complete count: 0/3

## Governance Boundary

- Mechanical PASS does not imply external/professional outcome validation completion.
- External status is required for any strong real-world performance claim.
