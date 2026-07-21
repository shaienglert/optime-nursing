# Florida Facility Universe — Executable Ingestion Plan

Status: ACTIVE DATA WORK

Governing principle: PR-009 Parameter-First Facility Matching.

## Objective

Build a statewide Florida senior-care universe from authoritative sources without treating facility labels as capability proxies.

Canonical model:

`Person requirements -> Facility -> Campus/Unit/Program/Service Line -> Parameters -> Evidence -> Current Availability`

## Authoritative Source Layers

### Florida AHCA / FloridaHealthFinder

Use official facility/provider exports where available (CSV/XLSX/ZIP), with the All Facilities inventory as the statewide identity/licensure backbone and type-specific datasets for richer fields.

Verified public dataset surfaces include:
- All Facilities
- Nursing Home
- Assisted Living Facility
- Adult Family Care Home
- Adult Day Care Center
- Home Health Agency
- Hospice and other supporting provider categories where case-relevant

Do not classify every AHCA provider as a residential candidate. Preserve a separate role:
- RESIDENTIAL_CANDIDATE
- SUPPORTING_PROVIDER
- BOTH
- OUT_OF_SCOPE

### CMS

Join CMS Nursing Home datasets to applicable Florida facilities using governed identity resolution (CCN/provider identifiers plus verified identity fields). CMS supplies deeper federal evidence including provider information, ownership, staffing/PBJ, inspections/deficiencies, penalties, quality measures and other nursing-home datasets.

## Minimum Facility Identity Schema

- ahca_file_number
- ahca_license_number
- cms_ccn when applicable
- facility_name
- facility_type_raw
- address
- city
- county
- zip
- phone
- license_status
- licensed_beds
- ownership/profit status where available
- source_record_id
- source_retrieved_at

## Parameter Extraction

Preserve raw source values and map them into canonical parameters. Examples:

- nurse availability, including 24-hour availability states where reported
- special programs and services
- activities
- specialty licenses/certifications
- licensed bed/capacity information
- complaints and substantiated complaints where reported
- sanctions/final orders
- fines
- deficiencies and severity classes
- ownership/affiliations
- Medicaid/Medicare/certification attributes where applicable
- rehabilitation and therapy evidence
- unit/program-level capabilities

Never infer a capability solely from `facility_type_raw`.

## Unit / Program Rule

A capability may exist only in a smaller unit or program within a broader facility. Store the evidence at the narrowest supported scope:

- FACILITY
- CAMPUS
- UNIT
- PROGRAM
- SERVICE_LINE

A facility-level category must not erase a verified unit/program capability.

## Dynamic Availability

Availability is never inferred from operating status.

For Top 10 verification, capture:
- appropriate unit/service availability now
- bed/room type
- earliest admission date
- waiting list
- current price/fees when relevant
- current promotion when relevant
- verified_at timestamp

## Required Outputs

1. `florida_facility_universe_raw` — source-preserving records.
2. `florida_facility_universe_canonical` — deduplicated facility identities.
3. `facility_capability_evidence` — parameter-level evidence with scope/provenance.
4. `facility_source_crosswalk` — AHCA/CMS/other authoritative identifiers.
5. `FLORIDA_FACILITY_UNIVERSE_AUDIT.json` and `.md` with:
   - exact record counts by source
   - active/inactive counts
   - counts by raw facility/provider type
   - residential/supporting/out-of-scope classification counts
   - CMS match counts and unmatched records
   - duplicate/identity-conflict counts
   - parameter coverage by family
   - UNKNOWN counts
   - source failures/access limitations

## Acceptance Rules

The statewide universe is NOT complete until exact counts are produced from downloaded/ingested authoritative datasets. Search-engine result counts or manually sampled pages are not acceptable substitutes.

No guessed counts.
No guessed capabilities.
No conversion of UNKNOWN to NO.
No automatic exclusion based only on facility title/type.
No claim of current availability without direct, timestamped verification.

## Current Verified Facts

- FloridaHealthFinder publicly exposes Export Facility Data controls for All Facilities and type-specific facility/provider pages, including CSV/XLSX/ZIP options.
- The Nursing Home public surface currently exposes 686 nursing-home records in the previously verified inventory count.
- Assisted Living exposes richer comparison fields including bed size, substantiated complaints, sanctions/final orders, fine amount, deficiency counts/classes, activities, nurse availability, and special programs/services.
- AHCA explicitly notes that facilities may offer additional activities/programs/services not shown in the public comparison data; these remain candidates for direct verification rather than negative evidence.

## Immediate Execution Gate

The next executable step is authoritative file ingestion. If automated AHCA export download is blocked in a runtime, record the exact HTTP/status/challenge and use a sanctioned alternate official download route or browser-mediated export. Do not replace the missing export with scraped samples and do not mark the universe complete until ingestion and audit counts succeed.