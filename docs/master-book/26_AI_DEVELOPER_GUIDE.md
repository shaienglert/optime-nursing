# 26 AI Developer Guide

## Purpose
Provide practical continuation guide for AI systems and developers.

## Current Implementation
- Project exposes code, doctrine, reports, and scripts needed for continuation without chat history.
- This master book is the intended single source of truth.

## Architecture
- Development loop: read doctrine -> inspect data/report state -> run targeted scripts -> validate outputs.

## Dependencies
- scripts/, docs/, reports/, backend/app/, frontend/src/.

## Current Status
- Implemented by this chapter set and repository artifacts.

## Completed Work
- Core surfaces and dependencies documented in this master book package.

## Remaining Work
- Add command cookbook for common maintenance tasks and expected outputs.

## Known Limitations
- Some scripts depend on external source uptime and can fail transiently.

## Next Implementation Steps
- Add retry-safe wrappers and runbooks for transient failures.
