# 21 Repository Structure

## Purpose
Document top-level repository organization and purpose of each area.

## Current Implementation
- Root folders: backend, frontend, docs, scripts, reports, database, data, knowledge.
- Deployment files: render.yaml and environment-driven startup behavior.

## Architecture
- Product code split between frontend and backend.
- Data/report workflows driven by scripts and serialized artifacts.

## Dependencies
- Repository root structure and script catalog.

## Current Status
- Implemented with broad coverage of platform concerns.

## Completed Work
- Script library includes ingestion, validation, audits, and reporting phases.

## Remaining Work
- Reduce overlap among report generators and retire stale assets.

## Known Limitations
- Large report surface can create conflicting state snapshots.

## Next Implementation Steps
- Introduce report ownership map and active-vs-archived tagging.
