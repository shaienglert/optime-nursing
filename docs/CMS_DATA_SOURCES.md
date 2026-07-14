# CMS Data Sources for OPTIME Nursing

## Scope
This document evaluates public CMS datasets needed to build and maintain OPTIME Nursing ingestion pipelines and scoring.

Primary publication portal: https://data.cms.gov/provider-data/

Licensing and usage baseline:
- CMS Provider Data is publicly available and generally intended for public use.
- Data should be attributed to CMS in product documentation.
- No warranty is provided by CMS; records must be validated during import.

## Dataset Catalog

### 1) Provider Information (Nursing Home Provider Info)
- Purpose: Facility-level master list and key descriptive attributes.
- Source URL: https://data.cms.gov/provider-data/dataset/4pq5-n9py
- Primary key: cms_certification_number_ccn (CCN)
- Update frequency: Monthly (typical CMS Provider Data cadence)
- Approximate record count: ~15,000 to 16,500 facilities
- Important fields:
  - cms_certification_number_ccn
  - provider_name
  - provider_address
  - citytown
  - state
  - zip_code
  - telephone_number
  - overall_rating
  - staffing_rating
  - health_inspection_rating
  - qm_rating
  - number_of_certified_beds
  - latitude, longitude
- Use within OPTIME:
  - Master Facility ingestion source
  - Initial ratings and location baseline
  - MVP FL-state filtered import

### 2) Health Inspections
- Purpose: Inspection outcomes and deficiency context for safety and compliance.
- Source URL: https://data.cms.gov/provider-data/search?query=nursing%20home%20health%20inspection
- Primary key: Composite, typically (CCN + inspection period/date + deficiency identifiers)
- Update frequency: Monthly to quarterly depending on specific published table
- Approximate record count: Hundreds of thousands of inspection-deficiency rows over time
- Important fields:
  - CCN
  - survey dates
  - deficiency counts
  - deficiency severity/scope
  - weighted inspection scores
- Use within OPTIME:
  - Safety and Inspection score component
  - Time-decayed quality and risk trend features

### 3) Staffing
- Purpose: Nursing staffing levels and staffing quality proxies.
- Source URL: https://data.cms.gov/provider-data/search?query=nursing%20home%20staffing
- Primary key: Composite, typically (CCN + reporting period)
- Update frequency: Quarterly to monthly publication windows
- Approximate record count: Tens to hundreds of thousands of CCN-period rows
- Important fields:
  - CCN
  - RN hours per resident day
  - total nurse staffing hours per resident day
  - weekend staffing metrics
  - staffing_rating
- Use within OPTIME:
  - Staffing score component
  - Reliability and trend models by role and time

### 4) Quality Measures (QM)
- Purpose: Clinical and outcome quality indicators.
- Source URL: https://data.cms.gov/provider-data/search?query=nursing%20home%20quality%20measures
- Primary key: Composite, typically (CCN + measure_id + period)
- Update frequency: Quarterly
- Approximate record count: High; one row per CCN/measure/period
- Important fields:
  - CCN
  - measure ID/name
  - numerator/denominator or measure values
  - measure period
  - qm_rating or derived quality score references
- Use within OPTIME:
  - Overall quality scoring component
  - Explainable quality dashboards

### 5) Ownership Information
- Purpose: Ownership and chain context, ownership type, legal entity metadata.
- Source URL: https://data.cms.gov/provider-data/search?query=nursing%20home%20ownership
- Primary key: Composite (CCN + ownership effective date or chain ID context)
- Update frequency: Monthly/periodic refresh
- Approximate record count: Similar order to facility count, plus historical changes
- Important fields:
  - CCN
  - legal_business_name
  - ownership_type
  - chain_id
  - chain_name
- Use within OPTIME:
  - Facility profile enrichment
  - Risk segmentation and transparency features

### 6) Penalties and Fines
- Purpose: Enforcement actions, penalties, and payment denials.
- Source URL: https://data.cms.gov/provider-data/search?query=nursing%20home%20fines%20penalties
- Primary key: Composite (CCN + penalty action date + action type)
- Update frequency: Monthly/periodic
- Approximate record count: Tens of thousands historically
- Important fields:
  - CCN
  - number_of_fines
  - total_amount_of_fines_in_dollars
  - number_of_payment_denials
  - action dates
- Use within OPTIME:
  - Safety/risk modifiers in scoring
  - Family-facing trust indicators

## Recommended Long-Term Source Strategy
- Preferred anchor source: Provider Information dataset (`4pq5-n9py`) because it is stable, complete, and already includes core ratings and location metadata.
- Use Provider Information as the anchor dataset keyed by CCN.
- Join periodic datasets (staffing, inspections, quality, penalties, ownership) via CCN and period/date keys.
- Maintain raw staging tables to preserve source fidelity and support reproducible reprocessing.
- Build curated analytics tables optimized for API access and scoring.

## Architecture Recommendation
- MVP: Single Facility table with core ratings and metadata for fast delivery.
- Production: Normalized multi-table model with periodic fact tables (staffing, inspections, quality, penalties) and derived score snapshots.
- Recommendation: Start with single-table ingestion pipeline for immediate value, while creating normalized schema now so migration is additive, not disruptive.

## Architecture Recommendation Summary
- Build now: Single Facility table ingestion from Provider Information for fast API and scoring bootstrap.
- Build next: Normalize staffing, inspections, quality, ownership, and penalties into separate time-series tables.
- Why this works: It keeps MVP simple while preserving a clean migration path to explainable and auditable production scoring.
