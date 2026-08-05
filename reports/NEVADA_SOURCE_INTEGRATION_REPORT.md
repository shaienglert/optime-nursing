# Nevada Source Integration Report

Generated: `2026-08-04T20:30:15Z`

## Summary

- Sources integrated: **2**
- Sources still blocked: **1**
- Facilities before: **66**
- Facilities after: **876**
- Coverage increase: **810**
- Duplicates removed / canonical merges: **77**

## Source Decisions

| Source | Lifecycle | Blocking reason | Solvable | Connector gap | Facilities gained | Categories added | Expected overlap with CMS | Expected new canonical facilities | Required connector | Required parser | Required normalization | Required validation |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |
| CMS Provider Information | INTEGRATED | None; already integrated | YES | CSV only | 0 | Skilled Nursing Facility, Nursing Facility | Source is CMS baseline | 0 | Existing CMS CSV reader | Existing cms_rows() parser | Existing CMS address/phone/zip normalization | Existing Nevada canonical validation |
| Nevada HCQC Health Facility Licensing | BLOCKED_TEMPORARILY | No machine-readable Nevada HCQC export was available locally. The official licensing vendor endpoint was reachable but redirected in a loop and exposed no verified public export during this run. | NO | Redirect; No API; Manual export |  | Assisted Living, Residential Facility for Groups, Skilled Nursing Facility, Nursing Facility, Continuing Care / Life Plan | High overlap for skilled nursing; unknown overlap for assisted living and other state categories |  | Official licensing export connector | Nevada HCQC machine-readable export parser | Facility-name, address, phone, and license-ID normalization | License ID, status, facility-type, and duplicate-merge validation |
| NPPES NPI Registry | INTEGRATED | No Nevada-filtered NPPES source extract was available locally; the existing repository extract is Florida-only and was not reused. | YES | CSV only | 0 | Assisted Living, Memory Care, Skilled Nursing Facility, Nursing Facility, Continuing Care / Life Plan | 5 | 810 | Streaming NPPES ZIP downloader | npidata_pfile CSV parser with taxonomy-slot expansion | NPI, facility name, DBA, address, zip, phone, taxonomy normalization | NPI-only identity checks, residential-taxonomy filter, duplicate merge and conflict audit |

## Facility Types

- Before: Skilled Nursing Facility
- After: Assisted Living, Memory Care, Nursing Facility, Other Governed Senior-Care Residential, Skilled Nursing Facility

## Remaining Gaps

- Records with Nevada license ID: **0**
- Records with NPI: **815**
- Media pilot gate status: **FAIL**
