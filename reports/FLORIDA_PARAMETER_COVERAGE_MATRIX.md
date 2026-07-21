# Florida Parameter Coverage Matrix

Generated At (UTC): 2026-07-21T15:01:12+00:00
Canonical Facilities: 11090
Recovered Parameters: 59
Sparse Evidence Records: 19276

## Family Counts

| Family | Parameter Count |
| --- | --- |
| CARE_NURSING | 10 |
| DYNAMIC | 5 |
| FINANCIAL_ACCESS | 5 |
| PERSONAL_FIT | 10 |
| QUALITY_SAFETY | 12 |
| REHABILITATION | 6 |
| SPECIALIZED_CARE | 11 |

## Coverage

| Parameter | Parameter ID | Family | Facilities With Evidence | Evidence Rows | Missing Definition |
| --- | --- | --- | --- | --- | --- |
| Skilled nursing capabilities | skilled_nursing_capabilities | CARE_NURSING | 3706 | 4090 | NO |
| 24/7 nursing | nursing_24_7 | CARE_NURSING | 3706 | 4090 | NO |
| Direct 24hr nurse availability | direct_24hr_nurse_availability | CARE_NURSING | 0 | 0 | NO |
| Third Party 24hr nurse availability | third_party_24hr_nurse_availability | CARE_NURSING | 0 | 0 | NO |
| RN hours per resident day | rn_hours_per_resident_day | CARE_NURSING | 676 | 676 | NO |
| Total nurse hours per resident day | total_nurse_hours_per_resident_day | CARE_NURSING | 676 | 676 | NO |
| ADL support | adl_support | CARE_NURSING | 1034 | 1409 | NO |
| Medication support | medication_support | CARE_NURSING | 0 | 0 | NO |
| Transfer assistance | transfer_assistance | CARE_NURSING | 0 | 0 | NO |
| Higher-acuity capabilities | higher_acuity_capabilities | CARE_NURSING | 0 | 0 | NO |
| Physical therapy | pt | REHABILITATION | 32 | 42 | NO |
| Occupational therapy | ot | REHABILITATION | 16 | 24 | NO |
| Speech therapy | speech_therapy | REHABILITATION | 18 | 23 | NO |
| Short-term rehabilitation | short_term_rehab | REHABILITATION | 0 | 0 | NO |
| Post-stroke/neurological evidence | post_stroke_neuro_evidence | REHABILITATION | 0 | 0 | NO |
| Therapy staffing | therapy_staffing | REHABILITATION | 0 | 0 | NO |
| Memory Care | memory_care | SPECIALIZED_CARE | 142 | 142 | NO |
| Dementia/Alzheimer programs | dementia_alz_programs | SPECIALIZED_CARE | 142 | 142 | NO |
| Wound care | wound_care | SPECIALIZED_CARE | 12 | 12 | NO |
| Dialysis arrangements | dialysis_arrangements | SPECIALIZED_CARE | 2 | 2 | NO |
| Respiratory/tracheotomy/ventilator capabilities | respiratory_trach_vent | SPECIALIZED_CARE | 9 | 14 | NO |
| Hospice/palliative arrangements | hospice_palliative_arrangements | SPECIALIZED_CARE | 114 | 136 | NO |
| Specialty licenses | specialty_licenses | SPECIALIZED_CARE | 0 | 0 | NO |
| Extended Congregate Care | extended_congregate_care | SPECIALIZED_CARE | 0 | 0 | NO |
| Limited Nursing Services | limited_nursing_services | SPECIALIZED_CARE | 0 | 0 | NO |
| Limited Mental Health | limited_mental_health | SPECIALIZED_CARE | 527 | 540 | NO |
| Secured units | secured_units | SPECIALIZED_CARE | 0 | 0 | NO |
| Inspection rating | inspection_rating | QUALITY_SAFETY | 691 | 691 | NO |
| Deficiency count | deficiency_count | QUALITY_SAFETY | 688 | 688 | NO |
| Deficiency severity | deficiency_severity | QUALITY_SAFETY | 688 | 688 | NO |
| Complaint-related findings | complaint_related_findings | QUALITY_SAFETY | 688 | 688 | NO |
| Fire safety deficiencies | fire_safety_deficiencies | QUALITY_SAFETY | 659 | 659 | NO |
| Infection control findings | infection_control_findings | QUALITY_SAFETY | 688 | 688 | NO |
| Penalties/fines | penalties_fines | QUALITY_SAFETY | 694 | 694 | NO |
| Sanctions/final orders | sanctions_final_orders | QUALITY_SAFETY | 0 | 0 | NO |
| Payment denials | payment_denials | QUALITY_SAFETY | 694 | 694 | NO |
| Quality measures | quality_measures | QUALITY_SAFETY | 694 | 694 | NO |
| Hospital/claims outcomes | hospital_claims_outcomes | QUALITY_SAFETY | 0 | 0 | NO |
| Staffing turnover | staffing_turnover | QUALITY_SAFETY | 0 | 0 | NO |
| Languages | languages | PERSONAL_FIT | 0 | 0 | NO |
| Dietary capabilities | dietary_capabilities | PERSONAL_FIT | 0 | 0 | NO |
| Gluten-free | gluten_free | PERSONAL_FIT | 0 | 0 | NO |
| Kosher | kosher | PERSONAL_FIT | 0 | 0 | NO |
| Religious/cultural services | religious_cultural_services | PERSONAL_FIT | 0 | 0 | NO |
| Activities | activities | PERSONAL_FIT | 0 | 0 | NO |
| Transportation | transportation | PERSONAL_FIT | 320 | 380 | NO |
| Amenities | amenities | PERSONAL_FIT | 0 | 0 | NO |
| Private/shared rooms | private_shared_rooms | PERSONAL_FIT | 0 | 0 | NO |
| Accessibility | accessibility | PERSONAL_FIT | 0 | 0 | NO |
| Payer information | payer_information | FINANCIAL_ACCESS | 0 | 0 | NO |
| Medicaid attributes | medicaid_attributes | FINANCIAL_ACCESS | 0 | 0 | NO |
| Medicare attributes | medicare_attributes | FINANCIAL_ACCESS | 694 | 694 | NO |
| Published rates | published_rates | FINANCIAL_ACCESS | 0 | 0 | NO |
| Fees | fees | FINANCIAL_ACCESS | 0 | 0 | NO |
| Current bed/unit availability | current_availability | DYNAMIC | 0 | 0 | NO |
| Earliest admission date | earliest_admission_date | DYNAMIC | 0 | 0 | NO |
| Waiting list | waiting_list | DYNAMIC | 0 | 0 | NO |
| Current price | current_price | DYNAMIC | 0 | 0 | NO |
| Current promotions | current_promotions | DYNAMIC | 0 | 0 | NO |

## Validation

| Check | Status | Detail |
| --- | --- | --- |
| UNKNOWN never becomes NO | PASS | Resolved rows default to UNKNOWN/Not verified when sparse evidence is absent. |
| Secondary taxonomy evidence survives | PASS | Multi-taxonomy facilities retain multiple NPPES evidence rows instead of collapsing to a single primary taxonomy. |
| UNIT/PROGRAM evidence not promoted to FACILITY | PASS | Service and program evidence preserve narrower scope in resolved rows and sparse evidence records. |
| Availability is not inferred | PASS | Current availability resolves to 'Confirm directly with facility' without synthetic availability evidence. |
| Facility type is not a blanket exclusion | PASS | Residential NPPES-only facilities remain in the canonical universe and receive sparse evidence where supported. |
| Comparison uses identical parameter IDs | PASS | All facilities in a comparison return the same ordered parameter ID set. |
| Missing data does not affect ranking by completeness | PASS | Personalized ordering uses registry priority and user needs only; it never awards facilities for extra evidence volume. |