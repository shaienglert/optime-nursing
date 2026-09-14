---
name: supplier-intelligence
description: Discover, verify, compare, and monitor Las Vegas Valley suppliers that support senior-living moves or residents' ongoing quality of life.
---

# Supplier Intelligence

Build prepared supplier intelligence for Oomnik. Cover only suppliers serving Las Vegas Valley that materially support a move into senior living or ongoing quality of life after move-in.

## Boundaries

- Do not research senior-living facilities with this skill; Provider Intelligence owns facility identity and capabilities.
- Do not perform live supplier research during a resident recommendation request. Recommendations consume prepared snapshots only.
- Do not treat advertising, referral compensation, partner status, or popularity alone as evidence of fit.
- Do not call a supplier "best" without sufficient comparable evidence.
- Missing information is `UNKNOWN`, never negative evidence and never an inferred fact.
- Oomnik only links to general retailers and is not part of their transaction.
- A supplier that is necessary to make a facility-plus-service plan safe or workable is `OUTCOME_CRITICAL`; track its readiness and service continuity separately from public reputation.

## Workflow

1. Read [sector-registry.md](references/sector-registry.md) and select the relevant sector.
2. Read [source-routing.md](references/source-routing.md) for that sector's official, professional, review, and first-party sources.
3. Discover every plausible supplier serving the target geography; do not stop at sponsored or first-page results.
4. Resolve the legal entity, brand, location, branch, and service area before merging evidence.
5. Verify mandatory licenses or registrations with the governing source when applicable.
6. Capture each rating independently with source, branch, rating, review count, observed date, and URL. Do not average unlike sources into a fabricated star rating.
7. Separate facts, public opinions, facility referrals, and future verified Oomnik-client feedback.
8. Normalize the record using [record-contract.md](references/record-contract.md).
9. Validate records with `scripts/validate_supplier_record.py` before publication.
10. Publish only records that pass the sector gate. Preserve rejected candidates and prior values as historical evidence.

## Geographic gate

The launch market is Las Vegas Valley: Las Vegas, North Las Vegas, Henderson, Boulder City, Paradise, Spring Valley, Enterprise, Summerlin, and directly relevant Clark County communities. A Nevada address alone does not establish service coverage.

## Ranking and display

- Display source-specific ratings and review counts separately.
- Keep license/safety, reputation, service fit, operational reliability, facility referrals, and verified Oomnik feedback as distinct dimensions.
- Facility referrals are useful evidence of working relationships, not proof of quality.
- Commercial relationships must be disclosed and must never change organic ordering.
- Until Oomnik has verified client feedback, show that dimension as `NOT_YET_AVAILABLE`; do not redistribute it into a hidden score.

## Outputs

Return canonical supplier records, evidence records, unresolved conflicts, coverage gaps, freshness status, and a publication decision with explicit reasons. For outcome-critical suppliers, also return readiness and continuity fields required by the record contract.

