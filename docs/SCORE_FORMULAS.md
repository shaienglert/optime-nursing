# OPTIME Phase 1 Score Formulas

All scores are clipped to range 0-100.

## MedicalQualityScore

MedicalQualityScore =
- 25% * CMS rating score
- 25% * Hospitalizations score
- 15% * ER visits score
- 15% * Falls score
- 10% * Pressure ulcers score
- 10% * Weight loss score

Where:
- CMS rating score = (QM rating stars / 5) * 100
- Hospitalizations, ER visits, Falls, Pressure ulcers, Weight loss are inverse percentage measures:
  - score = 100 - measure_value
- Missing measure fallback = 50

## StaffingScore

StaffingScore =
- 35% * RN hours score
- 25% * Total staffing score
- 20% * Agency staff score
- 20% * Turnover score

Where:
- RN hours score = min(100, (RN hours per resident day / 0.75) * 100)
- Total staffing score = min(100, (Total nurse hours per resident day / 3.5) * 100)
- Agency staff score = 100 - agency_staff_percentage
- Turnover score = 100 - total_nursing_staff_turnover_percentage
- Missing input fallback = 50

## SafetyScore

SafetyScore =
- 35% * Serious deficiencies score
- 25% * Complaints score
- 20% * Fines score
- 20% * Infection control score

Where:
- Serious deficiencies score = 100 - min(serious_deficiency_count, 10) / 10 * 100
- Complaints score = 100 - min(complaint_count, 25) / 25 * 100
- Fines score = 100 - min(total_fines_dollars, 500000) / 500000 * 100
- Infection control score = 100 - min(infection_control_citations, 10) / 10 * 100
- Missing input fallback = 50

## Overall OPTIME Score

overall_optime_score =
- 0.40 * medical_quality_score
- 0.35 * staffing_score
- 0.25 * safety_score
