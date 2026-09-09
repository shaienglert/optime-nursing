# Market Intelligence Source Contract

The executive market report is evidence-backed market context. It is never an
input to facility recommendation or ranking. A numeric observation is valid only
when it has a geography, period, source URL, source scope and capture time.

## Required report rows and source of record

| Requested metric | Nevada / Las Vegas source of record | U.S. source of record | Publication cadence | Coverage rule |
| --- | --- | --- | --- | --- |
| Facility count, total and by segment | Nevada HCQC/ALiS licence registry for licensed care; Clark/City business licence feeds only for the separately labelled independent-living discovery universe | CMS Provider Information for Medicare/Medicaid-certified SNF only; NIC MAP for market-tracked senior housing | Registry refresh + CMS monthly + NIC quarterly | Do not add the independent-living discovery universe to licensed care totals. A national total may only state its exact source population. |
| Rooms/beds, total and by segment | HCQC capacity where published, plus the canonical verified facility record; do not call capacity an apartment/unit count | CMS certified beds for SNF; NIC MAP inventory for IL/AL/MC market supply | Registry refresh + CMS monthly + NIC quarterly | `beds`, `licensed places`, and `apartment units` remain three different measures. |
| Occupancy | NIC MAP Las Vegas market series, with segment and quarter | NIC MAP national market series, with segment and quarter | Quarterly | A publisher-issued NIC/NIC MAP release is acceptable for its explicit figure. The detailed series requires a NIC MAP connection; no inferred occupancy is permitted. |
| Falls with major injury | CMS Nursing Home Quality Measures, filtered to Nevada | CMS Nursing Home Quality Measures, national aggregate | CMS release cadence; refresh monthly | SNF only. Preserve the exact CMS measure description and aggregation method. |
| Hospitalization / rehospitalization | CMS Medicare Claims Quality Measures, filtered to Nevada | CMS Medicare Claims Quality Measures, national aggregate | CMS release cadence; refresh monthly | SNF only. Preserve the exact published measure and whether it is a percentage or another rate. |
| Units/beds under construction | Verified project register: jurisdiction permit **and** developer/operator construction confirmation. NIC MAP Las Vegas series is the market-level source when licensed. | NIC MAP construction pipeline | Permit feed weekly; NIC quarterly | A planning approval, announcement, land purchase, or opening target is not construction. Project units can enter the total only after the construction-status evidence is attached. |
| Relevant older-adult population projection | Nevada State Demographer ASRHO projections, with 65+ and 75+ derived from published cohorts | U.S. Census 2023 National Population Projections, with the same age bands | Annual or new release | Display start/end years, age band and whether the figure is a count or growth percentage. Historic change is never substituted for a forecast. |

## Connection status

| Source | Status | What it closes |
| --- | --- | --- |
| CMS Provider Information and Nursing Home Quality Measures | Connected in the CMS collector | SNF facility count, certified beds, falls and hospitalization for Nevada and U.S. |
| Nevada HCQC/ALiS | Canonical registry import exists; resilient automated refresh remains to be hardened | Licensed Nevada care facilities and state-reported capacity only |
| Nevada State Demographer | Connected as an annual, source-labelled snapshot | Nevada 65+ / 75+ growth from the published 2025-to-2030 projection |
| U.S. Census Population Projections | Connected to the official machine-readable national dataset | U.S. 65+ / 75+ growth from the published 2025-to-2030 projection |
| NIC MAP | Public headline releases available; detailed market feed is not connected | Occupancy and market inventory/pipeline; exact recurring Las Vegas and U.S. figures require a licensed NIC MAP export/API connection |
| Permit + developer register | No statewide standard feed identified | Verified Nevada construction total; build project-level collector rather than manufacture a statewide number |

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
- Population projections: refresh only when the published annual snapshot is older
  than 370 days. Nevada's official PDF remains explicitly identified as a snapshot;
  the U.S. series is downloaded from Census's machine-readable dataset.
- Market-data subscriptions: refresh cadence follows their published release
  schedule and requires a source connection before any number is published.
