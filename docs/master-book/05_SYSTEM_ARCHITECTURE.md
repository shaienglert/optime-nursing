# 05 System Architecture

## Purpose
Describe implemented system layers and component boundaries.

## Current Implementation
- Frontend in frontend/src.
- Backend API and services in backend/app.
- Knowledge and data assets in database/, data/, knowledge/, reports/.

## Architecture
- UI consumes API and local scoring logic.
- Backend owns data ingestion, persistence, and report refresh loops.
- Knowledge fabric schema exists in backend/app/models/knowledge_fabric.py.

## Dependencies
- FastAPI, SQLAlchemy, Next.js, script runner stack.

## Current Status
- Partially Implemented: architecture is broad and operational but some surfaces are still transitional.

## Completed Work
- API endpoints detected: 36.
- Model classes detected: 50.

## Remaining Work
- Normalize duplicated report pathways and stale artifacts.

## Known Limitations
- Mixed regional/statewide discovery reporting paths.

## Next Implementation Steps
- Consolidate report-generation pathways by engine ownership.
