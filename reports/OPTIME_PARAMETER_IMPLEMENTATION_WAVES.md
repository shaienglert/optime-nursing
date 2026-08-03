# OPTIME Parameter Implementation Waves

Generated: 2026-08-02T13:32:03+00:00

## Wave 1 - High-value, easy, authoritative

- Parameter count: 22
- Engineering effort: MEDIUM
- Operational effort: LOW
- Expected cumulative profile coverage: approximately 35% for an applicable skilled-nursing pilot; actual coverage varies by facility type and parameter applicability.
- Expected ranking-confidence effect: High for governed covered factors
- Dependencies: CMS/AHCA connectors and identity crosswalk
- Risk: Publication lag and facility-type coverage gaps
- Parameters: skilled_nursing_capabilities, nursing_24_7, rn_hours_per_resident_day, total_nurse_hours_per_resident_day, specialty_licenses, extended_congregate_care, limited_nursing_services, limited_mental_health, inspection_rating, deficiency_count, deficiency_severity, complaint_related_findings, fire_safety_deficiencies, infection_control_findings, penalties_fines, sanctions_final_orders, payment_denials, quality_measures, hospital_claims_outcomes, staffing_turnover, medicaid_attributes, medicare_attributes

## Wave 2 - Facility website and document extraction

- Parameter count: 18
- Engineering effort: HIGH
- Operational effort: MEDIUM
- Expected cumulative profile coverage: approximately 60% for an applicable skilled-nursing pilot; actual coverage varies by facility type and parameter applicability.
- Expected ranking-confidence effect: Incremental only where evidence is verified and case-relevant; generic completeness does not affect rank.
- Dependencies: Website discovery, robots/terms checks, PDF parser, source snapshots
- Risk: Website drift, access restrictions, and claim ambiguity
- Parameters: pt, ot, speech_therapy, short_term_rehab, memory_care, dementia_alz_programs, wound_care, hospice_palliative_arrangements, dietary_capabilities, gluten_free, kosher, activities, transportation, amenities, private_shared_rooms, accessibility, payer_information, published_rates

## Wave 3 - Direct facility confirmation

- Parameter count: 15
- Engineering effort: MEDIUM
- Operational effort: HIGH
- Expected cumulative profile coverage: approximately 85% for an applicable skilled-nursing pilot; actual coverage varies by facility type and parameter applicability.
- Expected ranking-confidence effect: Incremental only where evidence is verified and case-relevant; generic completeness does not affect rank.
- Dependencies: Question routing, contact management, claim state, expiry
- Risk: Low response rates and rapidly stale answers
- Parameters: direct_24hr_nurse_availability, third_party_24hr_nurse_availability, adl_support, medication_support, transfer_assistance, therapy_staffing, dialysis_arrangements, secured_units, languages, fees, current_availability, earliest_admission_date, waiting_list, current_price, current_promotions

## Wave 4 - Manual and proprietary intelligence

- Parameter count: 4
- Engineering effort: LOW engineering after tooling
- Operational effort: VERY HIGH
- Expected cumulative profile coverage: approximately 90% for an applicable skilled-nursing pilot; actual coverage varies by facility type and parameter applicability.
- Expected ranking-confidence effect: Incremental only where evidence is verified and case-relevant; generic completeness does not affect rank.
- Dependencies: Reviewer queues, compliance controls, outcome/feedback governance
- Risk: Cost, subjectivity, rights, and inconsistent evidence
- Parameters: higher_acuity_capabilities, post_stroke_neuro_evidence, respiratory_trach_vent, religious_cultural_services

## Guardrails

Coverage targets are operational estimates, not measured pilot outcomes. UNKNOWN remains neutral, and no wave changes ranking logic or evidence authority.
