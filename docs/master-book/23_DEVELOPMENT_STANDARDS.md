# 23 Development Standards

## Purpose
Capture coding, safety, and operational standards visible in repository behavior.

## Current Implementation
- Doctrine enforces evidence-first and no-guess constraints.
- Report conventions favor explicit UNPROVEN markers when evidence is missing.

## Architecture
- Standards span docs doctrine, agent specs, and verification gates.

## Dependencies
- docs/OPTIME_PRINCIPLES.md
- reports/*validation*.md

## Current Status
- Partially Implemented: standards are documented; automated compliance checks are partial.

## Completed Work
- Verified information and recommendation gate artifacts are present.

## Remaining Work
- Increase automated policy checks in CI/test flows.

## Known Limitations
- Some standards are enforced by convention rather than hard gates.

## Next Implementation Steps
- Add machine-checkable standards scorecard generated per run.
