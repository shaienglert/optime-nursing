# Booking x Tinder Facility Experience Report

## Product Principle

OPTIME is a Booking-style decision depth product with Tinder-style discovery efficiency and OPTIME-specific evidence intelligence.

That means:
- fast visual scanning and shortlist behavior in Results
- deep facility decision support in the Facility Intelligence Profile
- no invented facts, no invented pricing, no invented images, and no collapse of UNKNOWN into YES/NO

## Before Architecture

- Results page rendered large vertically stacked recommendation cards.
- The card surface mixed discovery, evidence, verification, and explanation into one oversized block.
- Facility details existed only as a generic detail page under `/facilities/[id]`.
- The old route was not the canonical decision surface.
- Price disclosure still needed explicit truth labeling.

## After Architecture

- Results now renders compact recommendation rows/cards for rapid scanning.
- Each result shows only:
  - thumbnail image
  - facility name and location
  - primary care type
  - OPTIME fit and confidence
  - strongest person-specific reasons
  - unresolved concern count
  - estimated price label
  - actions for view, save, skip, compare, and map
- Facility detail now resolves through the canonical `/facility/[id]` route.
- The legacy `/facilities/[id]` route redirects to the canonical profile route.
- The facility profile page now carries the deeper evidence and explanation model.

## Results Discovery Model

Results is now optimized for quick comparison rather than exhaustive reading.

The compact card surface answers:
- What is this place?
- Why is OPTIME showing it to me?
- What is the biggest reason to consider it?
- What is the biggest unresolved concern?
- Should I open it?

The compact card keeps the governed engine intact and only changes presentation.

## Facility Profile Model

The Facility Intelligence Profile is now the deep decision page.

It includes:
- governed facility image or compact placeholder
- canonical identity and CMS identity
- location and map action
- website and phone only when present in the data
- personalized explanation for the current person
- strong matches
- potential concerns
- still unknown
- questions to ask this facility
- care and service sections only when supported by the data model
- quality, safety, pricing, location, and evidence sections

The profile is driven by the same governed recommendation output used in Results.

## Personalized Intelligence Model

The profile now explicitly answers:
- why OPTIME selected this facility
- what the facility means for the current person
- what is verified
- what is still unknown
- what question should be asked next

Unknowns remain unknown. They are not converted into positive claims.

## Image Governance

Implemented a governed thumbnail rule set:
- use existing public/verified image when available
- otherwise use a compact neutral placeholder
- never invent an image
- never let a placeholder dominate the card

Image state is now surfaced as:
- source label
- placeholder flag

## Data / Evidence Governance

The profile surfaces the governed evidence available in the current data model:
- governed recommendation summary
- verification checklist
- governed MUST status
- signal details where present
- score breakdown categories
- facility snapshot evidence

No source claims were added beyond the data already present in the app.

## Price Semantics

Pricing is explicitly disclosed as non-authoritative unless verified by the backend.

Current behavior:
- Results shows `Estimated monthly range`
- Missing pricing shows `Current pricing not verified — contact facility`
- Synthetic price logic remains marked as derived

This preserves the Production Recommendation Truth Audit fix.

## Save / Skip / Compare Architecture

Implemented local interaction semantics in Results:
- SAVE
- NOT FOR ME
- COMPARE

These are local state interactions only.
They do not pretend to persist analytics or learning infrastructure that does not exist.

A lightweight compare tray is visible when facilities are selected.

## Test Results

Passed:
- `tests/budget-utils.test.ts`
- `tests/facility-experience.test.ts`

Validated by build:
- `npm run build`

Build also confirmed the new canonical route manifest:
- `/facility/[id]`
- `/facilities/[id]` redirect alias

## Visual Validation

Validated in local render:
- Results page is materially shorter and easier to scan.
- Compact recommendation cards render with small thumbnails and short decision-critical summaries.
- The placeholder is compact rather than dominating the page.
- The card actions are visible.

The canonical profile route is present in the build manifest and wired in code.
The local dev server required a restart to reflect the new route cleanly, so the profile page was validated primarily through build/type-check plus route wiring rather than a full live browser render.

## Known Gaps

- Compare is still local-state staging only.
- No persistent save/skip analytics backend was added.
- The profile page still depends on currently available data; unsupported sections stay hidden rather than being invented.
- Some evidence sections are concise summaries because the app does not currently expose every source URL/date in the live payload.

## Next Recommendations

1. Add a true compare page for 2-3 selected facilities.
2. Add persistence for save/skip events if an analytics backend becomes available.
3. Expand source-date provenance where the backend payload supports it.
4. Consider a richer image ingestion pipeline if more verified public imagery becomes available.
