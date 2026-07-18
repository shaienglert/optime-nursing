# 11 Provider Intelligence

## Purpose
Document provider intelligence collection and profile enrichment status.

## Current Implementation
- Provider Intelligence Agent spec exists and defines source/verification strategies.
- Provider-related profile fields and intelligence snapshot models exist in backend models.

## Architecture
- Provider profile enrichment combines CMS, inspections, intelligence signals, and portal verification.
- FacilityIntelligenceProfile stores confidence, signals, and summaries.

## Dependencies
- docs/agent_specs/provider_agent_spec.md
- backend/app/models/facility.py
- scripts/run_intelligence_trace_reports.cjs

## Current Status
- Partially Implemented: enrichment exists; statewide profile completion remains in progress.

## Completed Work
- Provider intelligence reports and dashboards are present.

## Remaining Work
- Expand verified fields per community and close pending verification backlog.

## Known Limitations
- Pricing/floor-plan coverage is not uniformly represented in current surfaces.

## Next Implementation Steps
- Add explicit per-field completeness and verification counters for provider intelligence.
