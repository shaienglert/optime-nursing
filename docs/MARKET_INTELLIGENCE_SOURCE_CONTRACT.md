# Market Intelligence Source Contract

The executive market report is evidence-backed market context. It is never an
input to facility recommendation or ranking. A numeric observation is valid only
when it has a geography, period, source URL, source scope and capture time.

## Required report rows

| Requested metric | Geography | Valid source contract | Current collector | Coverage rule |
| --- | --- | --- | --- | --- |
| Facility count by segment | Nevada / United States | State licence registry for state residential care; CMS Provider Information for SNF | CMS collector | Never label CMS as all senior living; it is SNF only. |
| Licensed rooms/beds by segment | Nevada / United States | State capacity fields; CMS certified beds | CMS collector | Beds and apartment units are separate inventories. |
| Occupancy | Nevada / United States | Licensed market series with stated segment and period | Pending source connection | Do not use a news article as a market-rate observation. |
| Falls with major injury | Nevada / United States | CMS Nursing Home Quality Measures | CMS collector | SNF only; retain CMS published measure definition and unit. |
| Hospitalization | Nevada / United States | CMS Nursing Home Quality Measures | CMS collector | SNF only; retain whether CMS reports percent or a rate. |
| Units/beds under construction | Nevada / United States | Permit/developer/project record with units and verified construction status | Pending source connection | Planned-only projects are not construction inventory. |
| Older-adult population projection | Nevada / United States | Census/state-demographer projection with age band and projection year | Pending source connection | Historic growth is not a projection. |

## Status semantics

- `AVAILABLE` means a current observation met the source contract.
- `MISSING` means no source-backed observation exists. It is not zero.
- The displayed source scope must state exclusions, especially the difference
  between CMS skilled nursing and the broader senior-living market.

## Refresh policy

- CMS public datasets: refresh only when the stored CMS snapshot is older than
  28 days; a refresh runs outside request handling.
- State licence registry: refresh from the state registry on its own cadence and
  reject a pull that collapses coverage unexpectedly.
- Market-data subscriptions and population projections: refresh cadence follows
  their published release schedule and requires a source connection before any
  number is published.
