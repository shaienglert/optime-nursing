# CMS Matching Analysis

Generated: 2026-07-15

## Inputs Compared
- CMS dataset: `database/market_communities_south_florida.json`
  - `records`: 141
  - Source: CMS Nursing Home Provider Information (CCN-based skilled nursing facilities)
- Inventory dataset: `database/south_florida_senior_living_inventory.json`
  - `records`: 784
  - Source: Seniorly public assisted living / independent living / memory care pages

## Observed Counts
- Expected CMS communities: 141
- Current exact matched communities: 4

### Match counts by key
- Exact match by CMS Provider ID: 0
- License number match: 0
- Address match: 0
- ZIP code match: 0
- Exact name + county match: 4
- Fuzzy name + county match (>= 0.82): 7

## Why Matching Fails

### 1. CMS Provider ID mismatch
- CMS `community_id` is CCN (CMS Certification Number).
- Inventory does not store CCN.
- Inventory `state_license_number` comes from Florida HealthFinder `LID` references extracted from Seniorly pages.
- Result: ID-based joins fail (0 matches).

### 2. License number mismatch
- CMS CCN is not equivalent to Florida AHCA/HealthFinder `LID`.
- Join attempt `inventory.state_license_number == cms.community_id` fails by design.
- Result: license joins fail (0 matches).

### 3. Address and ZIP mismatch
- Inventory primarily contains non-SNF communities (assisted living/independent/memory care).
- CMS file is SNF-focused provider list.
- Even in overlapping geographies, addresses and ZIP entries rarely refer to the same facilities.
- Result: address/ZIP joins fail (0 matches).

### 4. Name mismatch from facility-class overlap
- Datasets overlap only for a small subset of SNF providers present on Seniorly.
- Exact normalized name + county yields only 4 communities.
- Fuzzy matching identifies 3 additional likely alignments, but still far from 141 because population overlap is limited.

## Exact Matches (4)
1. Miami Springs Nursing and Rehabilitation Center (Miami-Dade)
2. Nspire Healthcare Kendall (Miami-Dade)
3. Finnish-American Village (Palm Beach)
4. Health Center at Sinai Residences (Palm Beach)

## Fuzzy Name Matches (additional likely)
1. St. Anne's Nursing Center & Residence -> ST ANNES NURSING CENTER, ST ANNES RESIDENCE INC (0.868)
2. Colonial Skilled Nursing Facility -> COLONIAL SKILLED NURSING FACILITY LLC (1.000)
3. Stratford Court of Boca Pointe -> STRATFORD COURT OF BOCA RATON (0.881)

## Failed Matches Summary
- Failed by CMS Provider ID: 784 inventory rows (no CCN field available in inventory)
- Failed by license number: 784 inventory rows (incompatible identifier systems)
- Failed by address: 784 inventory rows (minimal direct overlap in facility universe)
- Failed by ZIP: 784 inventory rows (same root cause as address)

## Root Cause
The two datasets do not represent the same full facility universe:
- CMS file (141 rows) is SNF provider-centric and keyed by CCN.
- Inventory file (784 rows) is broader senior-living inventory (assisted living/independent/memory care) keyed by Seniorly URL and HealthFinder `LID` where visible.

Therefore, current direct matching logic cannot reach 141 CMS matches from the 784 inventory dataset.

## Path To Increase CMS Coverage (without modifying source data)
1. Build CMS-anchored recommendation mode for SNF communities directly from `market_communities_south_florida.json`.
   - This yields full 141 CMS communities available by definition.
2. Keep mixed inventory mode separate (AL/IL/MC) and do not force CCN joins where identifiers are incompatible.
3. Add a crosswalk table generated from deterministic rules only:
   - county-constrained exact normalized name match
   - county-constrained fuzzy match above strict threshold
   - manual review flag for unresolved near-matches
4. Treat fuzzy-only links as provisional until independently confirmed by an authoritative ID source.

## Conclusion
The 4-match outcome is expected under current datasets and join keys. Achieving 141 CMS coverage requires using the CMS dataset as the primary community list for CMS-backed recommendations, not trying to project all 784 inventory communities onto CCN IDs.