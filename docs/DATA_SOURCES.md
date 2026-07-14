# OPTIME Data Sources

## 1. CMS Provider Information
- Update frequency: Monthly (with periodic corrections)
- Fields available:
  - cms_id (CCN)
  - facility_name
  - address, city, state, zip
  - phone
  - ownership_type
  - number_of_certified_beds
  - facility_type
  - latitude, longitude
- Expected record count:
  - National: ~15,000-16,000 certified nursing facilities
  - Senior Living MVP subset (target geography): ~500-3,000
- Mapping to OPTIME scores:
  - Environment: baseline facility metadata and location context
  - Community: proximity to family and local services (derived)
  - Outcome Prediction: facility-type and capacity features

## 2. CMS Payroll Based Journal (PBJ)
- Update frequency: Quarterly submissions (with publication lag)
- Fields available:
  - rn_hours_per_resident_day
  - lpn_hours_per_resident_day
  - cna_hours_per_resident_day
  - total_nurse_hours_per_resident_day
  - weekend_staffing_hours
  - staffing_turnover_indicators (derived)
  - reporting_period
- Expected record count:
  - National quarterly rows: ~15,000 facilities x 1 row/quarter (+ granular staffing rows)
  - Multi-quarter history in warehouse: 100,000+ rows
- Mapping to OPTIME scores:
  - Staffing: primary driver
  - Safety: secondary signal (understaffing risk)
  - Outcome Prediction: staffing trend features

## 3. CMS Quality Measures
- Update frequency: Quarterly refresh (varies by measure)
- Fields available:
  - quality_measure_code
  - quality_measure_name
  - measure_value
  - numerator, denominator (where available)
  - risk_adjusted_rate (where available)
  - reporting_period
- Expected record count:
  - National: 15,000 facilities x multiple measures (typically 15-40+) per period
  - Typical period volume: 250,000-600,000 measure rows
- Mapping to OPTIME scores:
  - Medical Quality: primary driver
  - Outcome Prediction: strong longitudinal signals
  - Safety: selected adverse event measures

## 4. CMS Inspections and Deficiencies
- Update frequency: Continuous/weekly publication with periodic backfills
- Fields available:
  - inspection_date
  - inspection_type
  - deficiency_tag
  - scope_severity
  - deficiency_count
  - severe_deficiency_count
  - civil_monetary_penalty_amount
  - payment_denial_count
- Expected record count:
  - National annual events: tens of thousands of inspection records and deficiency entries
  - Multi-year warehouse: 1M+ deficiency-level rows
- Mapping to OPTIME scores:
  - Safety: primary driver
  - Medical Quality: secondary compliance and adverse-event proxy
  - Outcome Prediction: risk and trend features from deficiency severity history

## Source-to-Score Summary
- Medical Quality: CMS Quality Measures + Inspections/Deficiencies
- Staffing: CMS PBJ
- Safety: CMS Inspections/Deficiencies + PBJ understaffing indicators
- Outcome Prediction: blended longitudinal features from all four sources
