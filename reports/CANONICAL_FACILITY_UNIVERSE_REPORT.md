# Phase 1 - Canonical Facility Universe Report

Generated At (UTC): 2026-07-19T17:28:35Z
Phase Status: COMPLETE
Canonical Dataset: database/florida_senior_living_inventory.json

## Executive Truth

- Canonical universe total facilities: 713
- Canonical statewide coverage: 64 / 67 counties
- Canonical missing counties: Glades, Liberty, Union
- Canonical CMS-linked facilities: 694
- Legacy conflicting active reports (historical scope): reports/discovery_report.md and reports/executive_dashboard.md previously showed 3/67 and are now explicitly marked legacy scope.

## Canonical Source of Truth

- Canonical dataset file: database/florida_senior_living_inventory.json
- Dataset generated at (UTC): 2026-07-18T05:39:28+00:00
- Canonical record_count metadata: 713
- Canonical records array length: 713
- Canonical counties_covered metadata: 64
- Canonical counties_total metadata: 67
- Canonical duplicate_merges metadata: 1

## Canonical Identity Policy

Authoritative identifiers are resolved in this order:

1. cms_certification_number
2. state_license_number
3. Synthetic fallback key: normalized community_name + address + city + zip_code

Validation result on canonical dataset:

- Duplicate canonical IDs on authoritative identifiers: 0
- Conflicting merges on authoritative identifiers: 0

## Coverage and Linkage Metrics

- Total records: 713
- Counties covered: 64/67
- Counties missing: 3
- CMS-linked: 694
- State-license-linked: 9
- Both CMS+license present: 0
- Neither CMS nor state license present: 10
- Provenance gaps (missing source_refs or source_urls): 0

## Official-Source Verification

Verified against canonical dataset evidence markers:

- Records with CMS official source marker (`CMS Provider Information` or `data.cms.gov`): 694
- Records with Medicare official source marker (`Medicare Care Compare` or `medicare.gov`): 694
- CMS-linked records missing official CMS/Medicare marker: 0
- Florida official marker occurrences (`Florida HealthFinder`, `AHCA`, `flhealthsource`) in source evidence: 0

Conclusion:

- Official-source verification for CMS-linked records: VERIFIED
- Florida-official lineage is not currently a primary marker in canonical evidence fields and remains a known enrichment gap.

## Provenance and Freshness

- Canonical snapshot generated_at_utc: 2026-07-18T05:39:28+00:00
- Snapshot age at Phase 1 completion: 1.49 days
- Records missing `last_source_date`: 19
- `last_source_date` range in canonical records: 2026-06-01 to 2026-06-01
- Oldest source age at Phase 1 completion: 48.73 days

Freshness gate policy used in validation:

- Max snapshot age: 7 days
- Min `last_source_date` presence ratio: 0.95
- Max oldest source age: 120 days

Current freshness result: PASS

## Legacy Dataset Reconciliation Classification

Canonical comparison classes used:

- CONFIRMED_SAME: authoritative ID overlap with canonical
- PROBABLE_MATCH_REVIEW_REQUIRED: normalized name+county overlap only
- DISTINCT: authoritative IDs present but not in canonical
- UNRESOLVED: no authoritative ID and no canonical name+county overlap

Per-dataset reconciliation:

| Dataset | Record Count | CONFIRMED_SAME | PROBABLE_MATCH_REVIEW_REQUIRED | DISTINCT | UNRESOLVED | Canonical Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| database/south_florida_senior_living_inventory.json | 784 | 0 | 4 | 490 | 290 | LEGACY_NOT_CANONICAL |
| database/market_communities_south_florida.json | 141 | 0 | 141 | 0 | 0 | LEGACY_NOT_CANONICAL |
| database/market_communities_palm_beach.json | 54 | 0 | 54 | 0 | 0 | LEGACY_NOT_CANONICAL |

Aggregate reconciliation totals:

- CONFIRMED_SAME: 0
- PROBABLE_MATCH_REVIEW_REQUIRED: 199
- DISTINCT: 490
- UNRESOLVED: 290

## Active Reporting Reconciliation

- reports/discovery_report.md remains preserved as historical South Florida discovery snapshot and is explicitly labeled legacy scope.
- reports/executive_dashboard.md remains preserved as historical operational dashboard and now explicitly distinguishes legacy 3/67 from canonical 64/67 statewide truth.
- No historical report files under reports/versions were deleted or rewritten.

## Legacy Source Retirement

Retirement policy applied:

- Legacy inventories are retained as historical evidence artifacts only.
- Runtime current-truth reporting is canonicalized to statewide source and must not present legacy 3/67 as current truth.

Runtime retirement verification:

- No `backend/app` runtime references found to legacy source files:
	- `database/south_florida_senior_living_inventory.json`
	- `database/market_communities_south_florida.json`
	- `database/market_communities_palm_beach.json`
- Legacy references remain in historical/data-build scripts under `scripts/` and are classified non-runtime.

## Runtime Wiring Audit

- Backend runtime dataset reference audit (`backend/app`): no direct JSON path references to legacy or canonical inventory files.
- Canonical governance in this phase is enforced through report/manifest/validation layer.
- Runtime policy outcome: no evidence of active runtime consuming legacy inventory files as current canonical truth.

## Validation Gates and Results

Validation script: scripts/validate_canonical_facility_universe.py

Required failure gates implemented:

- Canonical ID duplicates
- Conflicting ID merges
- Coverage disagreement for canonical metadata and active current-truth surfaces
- Provenance gaps
- Totals mismatch
- Official-source verification mismatch for CMS-linked records
- Freshness policy violations
- Legacy-source runtime reference violations

Current run result: PASS

## Deliverables Produced

- reports/CANONICAL_FACILITY_UNIVERSE_REPORT.md
- reports/canonical_facility_universe_manifest.json
- scripts/validate_canonical_facility_universe.py
- updates to reports/discovery_report.md and reports/executive_dashboard.md to deprecate legacy 3/67 as current truth

## Completion Block

PHASE: 1
TITLE: establish canonical facility universe
STATUS: COMPLETE
CANONICAL_TRUTH: 713 facilities, 64/67 counties, 694 CMS-linked
VALIDATION: PASS
NEXT_PHASE_ALLOWED: YES
