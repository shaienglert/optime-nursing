# Nevada Canonical Facility Universe Report

Generated: `2026-08-04T20:30:15Z`

## Sources

| Source | Authority | Dataset | Retrieval | Used |
| --- | --- | --- | --- | --- |
| CMS Provider Information | Federal government | 4pq5-n9py | 2026-08-04T20:30:15Z | Yes |
| Nevada HCQC Health Facility Licensing | Nevada state licensing authority | Unavailable | Unavailable | No |
| NPPES NPI Registry | Federal government | tmpwkqvgvq1.zip | 2026-08-04T20:30:15Z | Yes |

## Results

- Raw records by source: `{"CMS Provider Information": 66, "NPPES NPI Registry": 887}`
- Canonical Nevada records: **876**
- Las Vegas Valley records: **589**
- Complete authoritative identities: **108**
- Complete Las Vegas Valley identities: **68**
- Records with phone: **876**
- Records with full address: **108**
- Records with Nevada license ID: **0**
- Records with CMS/CCN: **66**
- Records with NPI: **815**
- Active facilities: **876**
- Inactive/closed facilities: **0**
- Duplicates merged: **77**
- Unresolved duplicate candidates: **260**
- Field conflicts: **5**
- Records missing critical identity fields: **768**
- Schema-validation errors: **0**
- Invalid ZIP codes: **0**
- Invalid or malformed phones: **0**
- Processing time: **Unavailable**
- Peak memory: **Unavailable**

## Facility Types

- Assisted Living: **209**
- Memory Care: **40**
- Nursing Facility: **23**
- Other Governed Senior-Care Residential: **415**
- Skilled Nursing Facility: **189**

## Missing Fields

- cms_certification_number: **810**
- nevada_license_id: **876**
- npi: **61**
- zip: **768**

## Media Pilot Gate

**FAIL**: 68 complete Las Vegas Valley identities; 100 required.

No media pilot was run.

## Source Limitations

- Nevada HCQC Health Facility Licensing: No machine-readable Nevada HCQC export was available locally. The official licensing vendor endpoint was reachable but redirected in a loop and exposed no verified public export during this run.
