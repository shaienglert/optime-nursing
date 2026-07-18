# 13 Decision Engine

## Purpose
Document decision logic beyond raw recommendation scoring.

## Current Implementation
- Decision framework artifacts in reports/decision_framework.md and related validation reports.
- Human intelligence and adaptive-response APIs implemented in backend.

## Architecture
- Decision layer combines resident profiles, constraints, and verified knowledge guards.
- Policy and confidence checks gate recommendation usage.

## Dependencies
- backend/app/main.py decision and human-intelligence routes
- reports/decision_framework.md

## Current Status
- Partially Implemented: core path exists, deeper decision-psychology loops are still expanding.

## Completed Work
- Human intelligence scoring endpoints and outcome feedback pipeline exist.

## Remaining Work
- Integrate more decision-psychology research outputs into runtime decision traces.

## Known Limitations
- Direct mapping from psychology findings to production variables is partial.

## Next Implementation Steps
- Add variable lineage from research finding to decision feature.
