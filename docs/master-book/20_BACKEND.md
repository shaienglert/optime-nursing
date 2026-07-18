# 20 Backend

## Purpose
Describe backend services, models, and deployment wiring.

## Current Implementation
- FastAPI app in backend/app/main.py.
- SQLAlchemy models for facilities, agent execution, and knowledge fabric.
- Render deployment config in render.yaml.

## Architecture
- Startup initializes schema, optional ingestion, and background refresh loops.
- Services layer handles ingestion, intelligence, supervisor, and verification logic.

## Dependencies
- backend/requirements.txt
- backend/app/services
- render.yaml

## Current Status
- Implemented and deployable on Render.

## Completed Work
- Health endpoint, import summary, and domain endpoints are present.

## Remaining Work
- Improve module decomposition and reduce main.py concentration.

## Known Limitations
- Single-file route concentration increases maintenance complexity.

## Next Implementation Steps
- Move route groups into backend/app/api modules with tests.
