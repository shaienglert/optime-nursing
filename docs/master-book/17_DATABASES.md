# 17 Databases

## Purpose
Catalog databases, JSON stores, and their operational roles.

## Current Implementation
- Primary relational store: SQLite file optime_nursing.db.
- Structured JSON repositories in database/, data/, knowledge/.

## Architecture
- ORM models in backend/app/models define facility, agent execution, clinical evidence, and knowledge fabric domains.

## Dependencies
- backend/app/models/*.py
- database/*.json
- data/*.json
- knowledge/*.json

## Current Status
- Partially Implemented: broad schema exists; coverage completeness varies by domain.

## Completed Work
- Knowledge fabric and agent telemetry models implemented.

## Remaining Work
- Expand verified coverage and enforce consistency across JSON and relational projections.

## Known Limitations
- Mixed snapshots can diverge between report outputs and underlying stores.

## Next Implementation Steps
- Add cross-store reconciliation checks in daily execution.
