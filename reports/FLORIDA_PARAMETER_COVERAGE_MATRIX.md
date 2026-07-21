# Florida Parameter Coverage Matrix

Generated At (UTC): 2026-07-21T12:24:55.934Z
Total Parameters: 59

## Family Counts

| Family | Parameter Count |
| --- | --- |
| QUALITY_SAFETY | 12 |
| SPECIALIZED_CARE | 11 |
| CARE_NURSING | 10 |
| PERSONAL_FIT | 10 |
| REHABILITATION | 6 |
| DYNAMIC | 5 |
| FINANCIAL_ACCESS | 5 |

## Auto-Answerable Parameters

Count: 7

## Requires Top-10 Verification Parameters

Count: 52

## Matrix

| Parameter | Canonical Name | Source | Raw Field | Coverage | Evidence Quality | Can Affect Case Match | Requires Facility Confirmation | Dynamic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Skilled nursing capabilities | skilled_nursing_capabilities | cms_provider_type | cms_provider_type | 694/694 | HIGH | YES | NO | NO |
| 24/7 nursing | nursing_24_7 | cms_provider_type | cms_provider_type | 694/694 | HIGH | YES | NO | NO |
| Direct 24hr nurse availability | direct_24hr_nurse_availability | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Third Party 24hr nurse availability | third_party_24hr_nurse_availability | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| RN hours per resident day | rn_hours_per_resident_day | rn_hours | rn_hours | 676/694 | HIGH | YES | NO | NO |
| Total nurse hours per resident day | total_nurse_hours_per_resident_day | total_nurse_hours | total_nurse_hours | 676/694 | HIGH | YES | NO | NO |
| ADL support | adl_support | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Medication support | medication_support | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Transfer assistance | transfer_assistance | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Higher-acuity capabilities | higher_acuity_capabilities | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Physical therapy | pt | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Occupational therapy | ot | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Speech therapy | speech_therapy | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Short-term rehabilitation | short_term_rehab | cms_provider_type | cms_provider_type | 0/694 | UNKNOWN | YES | NO | NO |
| Post-stroke/neurological evidence | post_stroke_neuro_evidence | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Therapy staffing | therapy_staffing | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Memory Care | memory_care | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Dementia/Alzheimer programs | dementia_alz_programs | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Wound care | wound_care | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Dialysis arrangements | dialysis_arrangements | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Respiratory/tracheotomy/ventilator capabilities | respiratory_trach_vent | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Hospice/palliative arrangements | hospice_palliative_arrangements | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Specialty licenses | specialty_licenses | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Extended Congregate Care | extended_congregate_care | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Limited Nursing Services | limited_nursing_services | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Limited Mental Health | limited_mental_health | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Secured units | secured_units | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Inspection rating | inspection_rating | inspection_rating | inspection_rating | 691/694 | HIGH | YES | NO | NO |
| Deficiency count | deficiency_count | deficiency_count | deficiency_count | 688/694 | HIGH | YES | NO | NO |
| Deficiency severity | deficiency_severity | severe_deficiency_count | severe_deficiency_count | 0/694 | UNKNOWN | YES | NO | NO |
| Complaint-related findings | complaint_related_findings | complaint_deficiency_count | complaint_deficiency_count | 0/694 | UNKNOWN | YES | NO | NO |
| Fire safety deficiencies | fire_safety_deficiencies | unknown | unknown | 659/694 | HIGH | YES | YES | NO |
| Infection control findings | infection_control_findings | infection_control_count | infection_control_count | 0/694 | UNKNOWN | YES | NO | NO |
| Penalties/fines | penalties_fines | total_fines | total_fines | 0/694 | UNKNOWN | YES | NO | NO |
| Sanctions/final orders | sanctions_final_orders | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Payment denials | payment_denials | total_payment_denials | total_payment_denials | 0/694 | UNKNOWN | YES | NO | NO |
| Quality measures | quality_measures | quality_measure_count | quality_measure_count | 0/694 | UNKNOWN | YES | NO | NO |
| Hospital/claims outcomes | hospital_claims_outcomes | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Staffing turnover | staffing_turnover | turnover | turnover | 0/694 | UNKNOWN | YES | NO | NO |
| Languages | languages | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Dietary capabilities | dietary_capabilities | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Gluten-free | gluten_free | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Kosher | kosher | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Religious/cultural services | religious_cultural_services | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Activities | activities | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Transportation | transportation | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Amenities | amenities | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Private/shared rooms | private_shared_rooms | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Accessibility | accessibility | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Payer information | payer_information | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Medicaid attributes | medicaid_attributes | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Medicare attributes | medicare_attributes | cms_certification_number | cms_certification_number | 0/694 | UNKNOWN | YES | NO | NO |
| Published rates | published_rates | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Fees | fees | unknown | unknown | 0/694 | UNKNOWN | YES | YES | NO |
| Current bed/unit availability | current_availability | dynamic | dynamic | 0/694 | UNKNOWN | NO | YES | YES |
| Earliest admission date | earliest_admission_date | dynamic | dynamic | 0/694 | UNKNOWN | NO | YES | YES |
| Waiting list | waiting_list | dynamic | dynamic | 0/694 | UNKNOWN | NO | YES | YES |
| Current price | current_price | dynamic | dynamic | 0/694 | UNKNOWN | NO | YES | YES |
| Current promotions | current_promotions | dynamic | dynamic | 0/694 | UNKNOWN | NO | YES | YES |
