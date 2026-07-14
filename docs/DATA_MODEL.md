# OPTIME Nursing Data Model

## Design Goals
- Support rapid MVP delivery and continuous CMS imports.
- Preserve historical data by reporting period.
- Keep score computation auditable and reproducible.

## Entity: Facility
Purpose: Master record for each nursing home.

Fields:
- id (PK, integer)
- cms_id (unique, indexed)
- name
- address
- city (indexed)
- state (indexed)
- zip_code (indexed)
- phone
- latitude
- longitude
- ownership_type (nullable)
- chain_id (nullable, indexed)
- chain_name (nullable)
- beds (nullable)
- is_active (default true)
- created_at
- updated_at

Indexes:
- unique(cms_id)
- index(state, city)
- index(zip_code)

Relationships:
- Facility 1:N FacilityStaffing
- Facility 1:N FacilityInspection
- Facility 1:N FacilityQualityMeasure
- Facility 1:N FacilityReview
- Facility 1:N OptimeScore

## Entity: FacilityStaffing
Purpose: Store staffing metrics by reporting period.

Fields:
- id (PK)
- facility_id (FK -> Facility.id, indexed)
- period_start
- period_end
- staffing_rating
- rn_hours_per_resident_day
- total_nurse_hours_per_resident_day
- weekend_total_nurse_hours_per_resident_day
- source_file_date
- created_at

Indexes:
- index(facility_id, period_end desc)
- unique(facility_id, period_start, period_end)

## Entity: FacilityInspection
Purpose: Capture inspections, deficiencies, and enforcement signals.

Fields:
- id (PK)
- facility_id (FK -> Facility.id, indexed)
- inspection_date
- inspection_rating
- deficiency_count
- severe_deficiency_count
- fine_amount
- payment_denials_count
- source_file_date
- created_at

Indexes:
- index(facility_id, inspection_date desc)

## Entity: FacilityQualityMeasure
Purpose: Store measure-level quality data over time.

Fields:
- id (PK)
- facility_id (FK -> Facility.id, indexed)
- measure_code
- measure_name
- measure_value
- numerator (nullable)
- denominator (nullable)
- period_start
- period_end
- quality_rating
- source_file_date
- created_at

Indexes:
- index(facility_id, measure_code, period_end desc)
- unique(facility_id, measure_code, period_start, period_end)

## Entity: FacilityReview
Purpose: Family/user review and preference signal capture.

Fields:
- id (PK)
- facility_id (FK -> Facility.id, indexed)
- source
- reviewer_hash
- rating
- review_text (nullable)
- sentiment_score (nullable)
- created_at

Indexes:
- index(facility_id, created_at desc)

## Entity: OptimeScore
Purpose: Versioned and explainable score snapshots.

Fields:
- id (PK)
- facility_id (FK -> Facility.id, indexed)
- score_version
- overall_score
- fit_score (nullable)
- quality_component
- staffing_component
- safety_component
- reviews_component
- value_component
- computed_at
- metadata_json

Indexes:
- index(facility_id, computed_at desc)
- unique(facility_id, score_version, computed_at)

## Scalability Considerations
- Keep raw ingestion tables or files for replayability.
- Partition high-volume fact tables by period in future warehouse migration.
- Use incremental upserts keyed by (cms_id, period).
- Add materialized views for query-heavy API patterns (state/city/rating filters).
- Introduce job orchestration and data quality checks before production-scale refresh.

## Architecture Recommendation Summary
Recommended path:
- MVP implementation: Single Facility table populated from Provider Information for quick API launch.
- Production implementation: Normalized multi-table design above for time-series analytics and explainable scoring.

Reasoning:
- Single table accelerates initial release and reduces operational complexity.
- Normalized model avoids data duplication, preserves temporal history, and supports robust scoring evolution.
- This hybrid path minimizes rework because Facility remains the stable anchor entity in both phases.
