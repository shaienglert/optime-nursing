# Las Vegas / Clark County Current Supply Report

This is the current evidence-backed supply universe available to the Oomnik
matching engine. It is a supply inventory, not a count of facilities that will
match every client. Recommendation eligibility still depends on the client's
needs and the facility-level evidence required by the decision engine.

## Current offerable supply universe

| Supply group | Distinct locations | What is verified | Capacity available now |
| --- | ---: | --- | ---: |
| Licensed senior-care locations | 440 | Active Nevada HCQC/ALiS licence record and canonical care type | 11,331 state-reported beds/places |
| Independent-living properties, city/business-license evidence | 12 | Primary property/operator evidence explicitly confirms senior or 55+ independent living | Not collected; never estimated |
| Independent-living properties, provider/operator evidence | 11 | Primary provider/property evidence and a standalone canonical record | Not collected; never estimated |
| **Total distinct locations currently in the supply universe** | **463** | Sources above; the two independent-living groups were checked for address overlap | **11,331 licensed beds/places, plus unquantified independent-living inventory** |

The 440 licensed locations are distinct licensed addresses. The 23 independent
living properties are kept separate because Nevada care licensing does not
represent apartment-style independent living, and their apartment counts have
not yet been collected.

## Licensed senior-care supply by canonical segment

| Segment | Licensed locations | Licensed beds/places |
| --- | ---: | ---: |
| Assisted Living Community | 11 | 1,033 |
| Assisted Living with Memory Care | 15 | 1,878 |
| Group Home with Memory Care | 9 | 83 |
| Individual Residential Care | 107 | 214 |
| Dedicated Memory Care Home | 143 | 1,328 |
| Dedicated Large Memory Care | 16 | 1,176 |
| Residential Group Home | 95 | 916 |
| Skilled Nursing | 44 | 4,703 |
| **Total** | **440** | **11,331** |

## Market context currently publishable

| Metric | Las Vegas / Nevada | United States | Scope and source |
| --- | --- | --- | --- |
| Senior-housing occupancy | 87.0% (Q1 2026, Las Vegas market) | 89.5% (Q1 2026) | NIC market release; senior housing market series, not a count of vacancies at individual facilities. |
| Falls with major injury | Not collected into the production report yet | Not collected into the production report yet | CMS Nursing Home Quality Measures is the source; applies to SNF only. |
| Hospitalization / rehospitalization | Not collected into the production report yet | Not collected into the production report yet | CMS Nursing Home Quality Measures is the source; applies to SNF only. |
| Verified units under construction | No aggregated, verified count yet | No aggregated, verified count yet | No number is shown until each project has both construction-status evidence and unit count. |
| 65+ / 75+ population projection | Official Nevada State Demographer source identified; not loaded into report yet | U.S. Census source identified; not loaded into report yet | Projection rows will state age band and start/end years. |

## Evidence boundary

- Registry snapshot: Nevada HCQC/ALiS, Clark County, active credentials,
  refreshed 2026-09-06.
- A licensed bed/place is not an available bed today and not an apartment unit.
- A location enters a client recommendation only after the matching and evidence
  gates pass. Market-level figures never affect ranking.
- Two city/business-license candidates remain `UNKNOWN` and are excluded from
  the 23 confirmed independent-living properties.
