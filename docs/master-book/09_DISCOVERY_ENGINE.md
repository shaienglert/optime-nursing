# 09 Discovery Engine

## Purpose
Document how Florida community discovery is implemented and measured.

## Current Implementation
- Statewide builder: scripts/build_florida_senior_living_inventory.py.
- Latest statewide inventory report: 64 / 67, records 713.
- Legacy discovery report currently references 3/67 counties.

## Architecture
- Source ingestion from Seniorly county pages and CMS provider dataset.
- Merge and dedup strategy across source families into JSON inventory artifacts.

## Dependencies
- scripts/build_florida_senior_living_inventory.py
- database/florida_senior_living_inventory.json
- reports/florida_discovery_inventory.md

## Current Status
- Partially Implemented: statewide run exists but not yet 67/67 coverage.

## Completed Work
- Full-county crawler implemented with merge and dedup flow.

## Remaining Work
- Close county gaps and unify report path to statewide snapshot only.

## Known Limitations
- Transient source failures can interrupt complete runs if retries are insufficient.

## Next Implementation Steps
- Execute repeated cycles until 67/67 or documented terminal gaps.
