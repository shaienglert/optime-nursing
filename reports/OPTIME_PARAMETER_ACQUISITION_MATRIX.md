# OPTIME Parameter Acquisition Matrix

> LEGACY STRATEGY NOTICE: This generated matrix reflects the pre-Data-Intelligence acquisition model. For current product planning, use `reports/OPTIME_DATA_INTELLIGENCE_BLUEPRINT.md`. Runtime and canonical registry data have not yet been migrated to that blueprint.

Generated: 2026-08-02T13:32:03+00:00

Canonical source of truth: `database/optime_parameter_registry.json` (59 parameters). This audit does not add parameters or alter ranking/evidence semantics.

## Acquisition Summary

| Primary class | Count |
| --- | --- |
| DIRECT_FACILITY_REQUEST | 15 |
| FACILITY_DOCUMENT_AUTOMATIC | 5 |
| FACILITY_WEBSITE_AUTOMATIC | 13 |
| GOVERNMENT_AUTOMATIC | 22 |
| HUMAN_VERIFICATION | 3 |
| MANUAL_RESEARCH | 1 |
| NOT_RELIABLY_AVAILABLE | 0 |
| THIRD_PARTY_INTERNET_AUTOMATIC | 0 |

## Practical Categories

| Category | Canonical parameter count |
| --- | --- |
| 1. Identity and licensing | 0 |
| 2. Ownership and organization | 0 |
| 3. Capacity and occupancy | 0 |
| 4. Care capabilities | 11 |
| 5. Rehabilitation | 6 |
| 6. Nursing and staffing | 11 |
| 7. Quality and outcomes | 2 |
| 8. Inspections and enforcement | 9 |
| 9. Pricing and payment | 7 |
| 10. Availability and admissions | 3 |
| 11. Language and culture | 2 |
| 12. Dietary needs | 3 |
| 13. Amenities and lifestyle | 5 |
| 14. Resident experience and reviews | 0 |
| 15. Location and practical access | 0 |
| 16. Media and photos | 0 |
| 17. Documents and downloadable materials | 0 |
| 18. Legal and reputation | 0 |
| 19. OPTIME proprietary intelligence | 0 |

> Zero-count categories are intentional: those concepts are not canonical parameters in the current 59-parameter registry and were not invented for this audit.

## Top 10 Hardest Parameters

| Parameter | Primary class | Reason |
| --- | --- | --- |
| Current bed/unit availability | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Current price | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Earliest admission date | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Waiting list | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Post-stroke/neurological evidence | HUMAN_VERIFICATION | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Respiratory/tracheotomy/ventilator capabilities | HUMAN_VERIFICATION | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Higher-acuity capabilities | HUMAN_VERIFICATION | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Therapy staffing | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Direct 24hr nurse availability | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |
| Third Party 24hr nurse availability | DIRECT_FACILITY_REQUEST | Dynamic, scope-sensitive, clinically ambiguous, or dependent on current facility response |

## Top 10 Easiest High-Value Parameters

| Parameter | Primary class | Reason |
| --- | --- | --- |
| Inspection rating | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Deficiency count | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Deficiency severity | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Complaint-related findings | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Fire safety deficiencies | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Infection control findings | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Penalties/fines | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Payment denials | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| RN hours per resident day | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |
| Total nurse hours per resident day | GOVERNMENT_AUTOMATIC | Authoritative structured government source and direct decision relevance |

## Parameter-by-Parameter Audit

| ID | Display name | Category | Class | Authority | Eligibility | Ranking | Current coverage | Owner | Missing action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| skilled_nursing_capabilities | Skilled nursing capabilities | 6. Nursing and staffing | GOVERNMENT_AUTOMATIC | A | YES | YES | 3706/11090 facilities (33.4%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| nursing_24_7 | 24/7 nursing | 6. Nursing and staffing | GOVERNMENT_AUTOMATIC | A | YES | YES | 3706/11090 facilities (33.4%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| direct_24hr_nurse_availability | Direct 24hr nurse availability | 6. Nursing and staffing | DIRECT_FACILITY_REQUEST | B | YES | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| third_party_24hr_nurse_availability | Third Party 24hr nurse availability | 6. Nursing and staffing | DIRECT_FACILITY_REQUEST | B | YES | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| rn_hours_per_resident_day | RN hours per resident day | 6. Nursing and staffing | GOVERNMENT_AUTOMATIC | A | NO | YES | 676/11090 facilities (6.1%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| total_nurse_hours_per_resident_day | Total nurse hours per resident day | 6. Nursing and staffing | GOVERNMENT_AUTOMATIC | A | NO | YES | 676/11090 facilities (6.1%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| adl_support | ADL support | 6. Nursing and staffing | DIRECT_FACILITY_REQUEST | B | YES | YES | 1034/11090 facilities (9.3%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| medication_support | Medication support | 6. Nursing and staffing | DIRECT_FACILITY_REQUEST | B | YES | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| transfer_assistance | Transfer assistance | 6. Nursing and staffing | DIRECT_FACILITY_REQUEST | B | YES | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| higher_acuity_capabilities | Higher-acuity capabilities | 6. Nursing and staffing | HUMAN_VERIFICATION | B | NO | YES | 0/11090 facilities (0.0%) | CLINICAL_REVIEWER | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| pt | Physical therapy | 5. Rehabilitation | FACILITY_WEBSITE_AUTOMATIC | B | YES | YES | 32/11090 facilities (0.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| ot | Occupational therapy | 5. Rehabilitation | FACILITY_WEBSITE_AUTOMATIC | B | YES | YES | 16/11090 facilities (0.1%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| speech_therapy | Speech therapy | 5. Rehabilitation | FACILITY_WEBSITE_AUTOMATIC | B | YES | YES | 18/11090 facilities (0.2%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| short_term_rehab | Short-term rehabilitation | 5. Rehabilitation | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| post_stroke_neuro_evidence | Post-stroke/neurological evidence | 5. Rehabilitation | HUMAN_VERIFICATION | B | YES | YES | 0/11090 facilities (0.0%) | CLINICAL_REVIEWER | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| therapy_staffing | Therapy staffing | 5. Rehabilitation | DIRECT_FACILITY_REQUEST | B | NO | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| memory_care | Memory Care | 4. Care capabilities | FACILITY_WEBSITE_AUTOMATIC | B | YES | YES | 142/11090 facilities (1.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| dementia_alz_programs | Dementia/Alzheimer programs | 4. Care capabilities | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 142/11090 facilities (1.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| wound_care | Wound care | 4. Care capabilities | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 12/11090 facilities (0.1%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| dialysis_arrangements | Dialysis arrangements | 4. Care capabilities | DIRECT_FACILITY_REQUEST | B | YES | YES | 2/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| respiratory_trach_vent | Respiratory/tracheotomy/ventilator capabilities | 4. Care capabilities | HUMAN_VERIFICATION | B | YES | YES | 9/11090 facilities (0.1%) | CLINICAL_REVIEWER | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| hospice_palliative_arrangements | Hospice/palliative arrangements | 4. Care capabilities | FACILITY_WEBSITE_AUTOMATIC | B | YES | YES | 114/11090 facilities (1.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| specialty_licenses | Specialty licenses | 4. Care capabilities | GOVERNMENT_AUTOMATIC | A | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| extended_congregate_care | Extended Congregate Care | 4. Care capabilities | GOVERNMENT_AUTOMATIC | A | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| limited_nursing_services | Limited Nursing Services | 4. Care capabilities | GOVERNMENT_AUTOMATIC | A | YES | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| limited_mental_health | Limited Mental Health | 4. Care capabilities | GOVERNMENT_AUTOMATIC | A | YES | YES | 527/11090 facilities (4.8%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| secured_units | Secured units | 4. Care capabilities | DIRECT_FACILITY_REQUEST | B | YES | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| inspection_rating | Inspection rating | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 691/11090 facilities (6.2%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| deficiency_count | Deficiency count | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 688/11090 facilities (6.2%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| deficiency_severity | Deficiency severity | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 688/11090 facilities (6.2%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| complaint_related_findings | Complaint-related findings | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 688/11090 facilities (6.2%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| fire_safety_deficiencies | Fire safety deficiencies | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 659/11090 facilities (5.9%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| infection_control_findings | Infection control findings | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 688/11090 facilities (6.2%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| penalties_fines | Penalties/fines | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 694/11090 facilities (6.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| sanctions_final_orders | Sanctions/final orders | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| payment_denials | Payment denials | 8. Inspections and enforcement | GOVERNMENT_AUTOMATIC | A | NO | YES | 694/11090 facilities (6.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| quality_measures | Quality measures | 7. Quality and outcomes | GOVERNMENT_AUTOMATIC | A | NO | YES | 694/11090 facilities (6.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| hospital_claims_outcomes | Hospital/claims outcomes | 7. Quality and outcomes | GOVERNMENT_AUTOMATIC | A | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| staffing_turnover | Staffing turnover | 6. Nursing and staffing | GOVERNMENT_AUTOMATIC | A | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| languages | Languages | 11. Language and culture | DIRECT_FACILITY_REQUEST | B | NO | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| dietary_capabilities | Dietary capabilities | 12. Dietary needs | FACILITY_DOCUMENT_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| gluten_free | Gluten-free | 12. Dietary needs | FACILITY_DOCUMENT_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| kosher | Kosher | 12. Dietary needs | FACILITY_DOCUMENT_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| religious_cultural_services | Religious/cultural services | 11. Language and culture | MANUAL_RESEARCH | B/C | NO | YES | 0/11090 facilities (0.0%) | DATA_RESEARCH_TEAM | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| activities | Activities | 13. Amenities and lifestyle | FACILITY_DOCUMENT_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| transportation | Transportation | 13. Amenities and lifestyle | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 320/11090 facilities (2.9%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| amenities | Amenities | 13. Amenities and lifestyle | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| private_shared_rooms | Private/shared rooms | 13. Amenities and lifestyle | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| accessibility | Accessibility | 13. Amenities and lifestyle | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| payer_information | Payer information | 9. Pricing and payment | FACILITY_DOCUMENT_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| medicaid_attributes | Medicaid attributes | 9. Pricing and payment | GOVERNMENT_AUTOMATIC | A | YES | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| medicare_attributes | Medicare attributes | 9. Pricing and payment | GOVERNMENT_AUTOMATIC | A | YES | YES | 694/11090 facilities (6.3%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| published_rates | Published rates | 9. Pricing and payment | FACILITY_WEBSITE_AUTOMATIC | B | NO | YES | 0/11090 facilities (0.0%) | AUTOMATED_PIPELINE | Keep UNKNOWN; queue source refresh/research; never convert absence into NO. |
| fees | Fees | 9. Pricing and payment | DIRECT_FACILITY_REQUEST | B | NO | YES | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| current_availability | Current bed/unit availability | 10. Availability and admissions | DIRECT_FACILITY_REQUEST | B | NO | NO | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| earliest_admission_date | Earliest admission date | 10. Availability and admissions | DIRECT_FACILITY_REQUEST | B | NO | NO | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| waiting_list | Waiting list | 10. Availability and admissions | DIRECT_FACILITY_REQUEST | B | NO | NO | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| current_price | Current price | 9. Pricing and payment | DIRECT_FACILITY_REQUEST | B | NO | NO | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |
| current_promotions | Current promotions | 9. Pricing and payment | DIRECT_FACILITY_REQUEST | B | NO | NO | 0/11090 facilities (0.0%) | FACILITY_RELATIONS | Keep UNKNOWN; queue facility request; never convert absence into NO. |

The CSV is the exhaustive field-level matrix. The JSON source map preserves the same rows as structured records.
