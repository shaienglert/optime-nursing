# Targeted Research 40-Request Forensic Ledger

- Run ID: 20260720T222246Z
- Total requests: 40
- Source successes: 35
- Source failures: 5

## Reconciliation

- RESOLVED: 0
- NO_RELEVANT_INFORMATION: 0
- EXTRACTION_FAILURE: 0
- IDENTITY_FAILURE: 0
- FIELD_MAPPING_FAILURE: 0
- VERIFICATION_FAILURE: 0
- PERSISTENCE_FAILURE: 0
- SOURCE_ACCESS_FAILURE: 5
- OTHER: 35

## A-H (35 successes)

- A_NO_INFORMATION_ABSENT: 0
- B_PRESENT_BUT_EXTRACTOR_MISSED: 0
- C_WRONG_FIELD_MAPPING: 0
- D_IDENTITY_REJECTED: 0
- E_VERIFICATION_REJECTED: 0
- F_PERSISTENCE_FAILED: 0
- G_ALREADY_EXISTS_NOT_NEW: 35
- H_POOR_TARGETING: 0

## Per Request

### Request 10119 | BISCAYNE HEALTH AND REHABILITATION CENTER | Official website
- CMS ID: 105008
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=utf-8', 'response_size': 175891, 'final_url': 'https://biscaynerehab.com/', 'request_time': '2026-07-20T22:22:47.969953+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['["cardiac_pulmonary", "dialysis", "specialized_nursing", "stroke_rehabilitation", "wound_care"]', '["cultural", "religious", "social"]', '["therapeutic_diets"]']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10127 | BISCAYNE HEALTH AND REHABILITATION CENTER | CMS Provider Dataset
- CMS ID: 105008
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['BISCAYNE HEALTH AND REHABILITATION CENTER', '12505 NE 16TH AVE', '5', '4', '5']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10129 | BISCAYNE HEALTH AND REHABILITATION CENTER | CMS Inspection Dataset
- CMS ID: 105008
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 13, "severe_deficiency_count": 0, "survey_dates": ["2022-07-14", "2023-07-27", "2024-10-31"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10131 | BISCAYNE HEALTH AND REHABILITATION CENTER | CMS Quality Dataset
- CMS ID: 105008
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10132 | CORAL GABLES NURSING AND REHABILITATION CENTER | Official website
- CMS ID: 105005
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: SOURCE_RATE_LIMITED
- HTTP/access: {'response_code': 429, 'failure_reason': 'http_429'}
- Content received: {'response_type': 'text/html; charset=utf-8', 'response_size': 33788, 'final_url': 'https://www.miradorliving.com/assisted-living/florida/miami/coral-gables-nursing-and-rehabilitation', 'request_time': '2026-07-20T22:22:54.240105+00:00', 'classification': 'HTTP_429'}
- Relevant info present: NO
- Extractor ran: NO
- Claim extracted: NO
- Extracted value: []
- Facility identity matched: YES
- Field mapped: NO
- Normalization result: []
- Evidence created: NO
- Verification status: []
- Persisted: NO
- Unknown resolved: NO
- Exact failure point: SOURCE_ACCESS_FAILURE

### Request 10140 | CORAL GABLES NURSING AND REHABILITATION CENTER | CMS Provider Dataset
- CMS ID: 105005
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['CORAL GABLES NURSING AND REHABILITATION CENTER', '7060 SW 8TH STREET', '5', '5', '4']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10142 | CORAL GABLES NURSING AND REHABILITATION CENTER | CMS Inspection Dataset
- CMS ID: 105005
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 2, "severe_deficiency_count": 0, "survey_dates": ["2024-07-11"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10144 | CORAL GABLES NURSING AND REHABILITATION CENTER | CMS Quality Dataset
- CMS ID: 105005
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10148 | FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | Official website
- CMS ID: 105172
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html;charset=utf-8', 'response_size': 250061, 'final_url': 'https://www.fountainmanorhealth.com/', 'request_time': '2026-07-20T22:22:55.455837+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['["occupational_therapy", "specialized_nursing", "speech_therapy", "wound_care"]', '["cultural", "religious", "social"]', '["therapeutic_diets"]']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10156 | FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | CMS Provider Dataset
- CMS ID: 105172
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['FOUNTAIN MANOR HEALTH & REHABILITATION CENTER', '390 NE 135TH ST', '5', '3', '5']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10158 | FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | CMS Inspection Dataset
- CMS ID: 105172
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 13, "severe_deficiency_count": 0, "survey_dates": ["2023-10-30", "2024-11-15", "2025-02-10", "2025-06-18", "2025-07-28"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10160 | FOUNTAIN MANOR HEALTH & REHABILITATION CENTER | CMS Quality Dataset
- CMS ID: 105172
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10161 | MIAMI JEWISH HEALTH SYSTEMS, INC | Official website
- CMS ID: 105030
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: SOURCE_GEO_BLOCKED_OR_SUSPECTED
- HTTP/access: {'response_code': 403, 'failure_reason': 'http_403'}
- Content received: {'response_type': 'text/html', 'response_size': 75193, 'final_url': 'https://www.miamijewishhealth.org/', 'request_time': '2026-07-20T22:22:57.015502+00:00', 'classification': 'GEO_BLOCK_SUSPECTED'}
- Relevant info present: NO
- Extractor ran: NO
- Claim extracted: NO
- Extracted value: []
- Facility identity matched: YES
- Field mapped: NO
- Normalization result: []
- Evidence created: NO
- Verification status: []
- Persisted: NO
- Unknown resolved: NO
- Exact failure point: SOURCE_ACCESS_FAILURE

### Request 10169 | MIAMI JEWISH HEALTH SYSTEMS, INC | CMS Provider Dataset
- CMS ID: 105030
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['MIAMI JEWISH HEALTH SYSTEMS, INC', '5200 NE 2ND AVENUE', '4', '5', '4']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10171 | MIAMI JEWISH HEALTH SYSTEMS, INC | CMS Inspection Dataset
- CMS ID: 105030
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 11, "severe_deficiency_count": 1, "survey_dates": ["2024-05-09", "2025-02-25", "2025-06-02", "2025-09-19", "2026-03-18"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10173 | MIAMI JEWISH HEALTH SYSTEMS, INC | CMS Quality Dataset
- CMS ID: 105030
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10175 | NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | Official website
- CMS ID: 105217
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=utf-8', 'response_size': 5499, 'final_url': 'https://northbeachrehab.com/', 'request_time': '2026-07-20T22:22:58.987819+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['["specialized_nursing"]']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10183 | NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | CMS Provider Dataset
- CMS ID: 105217
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['NORTH BEACH HEALTHCARE AND REHABILITATION CENTER', '2201 NE 170TH STREET', '1', '4', '4']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10185 | NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | CMS Inspection Dataset
- CMS ID: 105217
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 37, "severe_deficiency_count": 5, "survey_dates": ["2023-06-15", "2023-08-31", "2024-02-01", "2025-01-09", "2026-02-11"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10187 | NORTH BEACH HEALTHCARE AND REHABILITATION CENTER | CMS Quality Dataset
- CMS ID: 105217
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10190 | PINES NURSING HOME | Official website
- CMS ID: 105057
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 99451, 'final_url': 'https://npino.com/nursing-home/1326423682-pines-nursing-home-2015', 'request_time': '2026-07-20T22:23:00.567905+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['["dialysis", "occupational_therapy", "physical_therapy", "specialized_nursing", "speech_therapy"]', '["cultural", "lectures", "religious", "social"]']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10198 | PINES NURSING HOME | CMS Provider Dataset
- CMS ID: 105057
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['PINES NURSING HOME', '301 NE 141 STREET', '3', '4', '4']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10200 | PINES NURSING HOME | CMS Inspection Dataset
- CMS ID: 105057
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 25, "severe_deficiency_count": 1, "survey_dates": ["2022-10-06", "2023-07-07", "2023-12-07", "2025-04-30"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10202 | PINES NURSING HOME | CMS Quality Dataset
- CMS ID: 105057
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10203 | Pinecrest Center for Rehabilitation and Healing | Official website
- CMS ID: 105153
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: SOURCE_GEO_BLOCKED_OR_SUSPECTED
- HTTP/access: {'response_code': 403, 'failure_reason': 'http_403'}
- Content received: {'response_type': 'text/html', 'response_size': 75193, 'final_url': 'https://pinecrestrehab.com/', 'request_time': '2026-07-20T22:23:02.199104+00:00', 'classification': 'GEO_BLOCK_SUSPECTED'}
- Relevant info present: NO
- Extractor ran: NO
- Claim extracted: NO
- Extracted value: []
- Facility identity matched: YES
- Field mapped: NO
- Normalization result: []
- Evidence created: NO
- Verification status: []
- Persisted: NO
- Unknown resolved: NO
- Exact failure point: SOURCE_ACCESS_FAILURE

### Request 10211 | Pinecrest Center for Rehabilitation and Healing | CMS Provider Dataset
- CMS ID: 105153
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['Pinecrest Center for Rehabilitation and Healing', '13650 NE 3RD COURT', '5', '3', '5']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10213 | Pinecrest Center for Rehabilitation and Healing | CMS Inspection Dataset
- CMS ID: 105153
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 19, "severe_deficiency_count": 0, "survey_dates": ["2022-11-03", "2023-10-12", "2025-03-13"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10215 | Pinecrest Center for Rehabilitation and Healing | CMS Quality Dataset
- CMS ID: 105153
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10216 | SANDS AT SOUTH BEACH CARE CENTER, THE | Official website
- CMS ID: 105229
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: SOURCE_GEO_BLOCKED_OR_SUSPECTED
- HTTP/access: {'response_code': 403, 'failure_reason': 'http_403'}
- Content received: {'response_type': 'text/html', 'response_size': 92805, 'final_url': 'https://www.seniorlivingguide.com/communities/the-sands-at-south-beach-care-center-42-collins-ave-miami-beach-fl-33139/', 'request_time': '2026-07-20T22:23:04.067598+00:00', 'classification': 'GEO_BLOCK_SUSPECTED'}
- Relevant info present: NO
- Extractor ran: NO
- Claim extracted: NO
- Extracted value: []
- Facility identity matched: YES
- Field mapped: NO
- Normalization result: []
- Evidence created: NO
- Verification status: []
- Persisted: NO
- Unknown resolved: NO
- Exact failure point: SOURCE_ACCESS_FAILURE

### Request 10224 | SANDS AT SOUTH BEACH CARE CENTER, THE | CMS Provider Dataset
- CMS ID: 105229
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['SANDS AT SOUTH BEACH CARE CENTER, THE', '42 COLLINS AVENUE', '5', '4', '5']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10226 | SANDS AT SOUTH BEACH CARE CENTER, THE | CMS Inspection Dataset
- CMS ID: 105229
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 26, "severe_deficiency_count": 0, "survey_dates": ["2022-12-01", "2024-03-07", "2025-06-03", "2025-07-24"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10228 | SANDS AT SOUTH BEACH CARE CENTER, THE | CMS Quality Dataset
- CMS ID: 105229
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10231 | SERENITY BAY NURSING AND REHABILITATION CENTER | Official website
- CMS ID: 105120
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 112538, 'final_url': 'https://serenitybaycare.com/', 'request_time': '2026-07-20T22:23:05.971552+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['["dialysis", "specialized_nursing"]', '["religious"]']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10238 | SERENITY BAY NURSING AND REHABILITATION CENTER | CMS Provider Dataset
- CMS ID: 105120
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['SERENITY BAY NURSING AND REHABILITATION CENTER', '16650 W DIXIE HWY', '3', '5', '2']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10240 | SERENITY BAY NURSING AND REHABILITATION CENTER | CMS Inspection Dataset
- CMS ID: 105120
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 29, "severe_deficiency_count": 0, "survey_dates": ["2023-01-20", "2024-06-20", "2025-12-04"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10242 | SERENITY BAY NURSING AND REHABILITATION CENTER | CMS Quality Dataset
- CMS ID: 105120
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10243 | VILLA MARIA NURSING CENTER | Official website
- CMS ID: 105232
- Target field: 24_7_skilled_nursing|post_stroke_neuro_rehab|physical_therapy|occupational_therapy|speech_therapy|language_cultural_info|activities|nutrition_dietary|pricing
- Request result: SOURCE_ACCESS_FAILED
- HTTP/access: {'response_code': 403, 'failure_reason': 'http_403'}
- Content received: {'response_type': 'text/html', 'response_size': 986, 'final_url': 'https://www.catholichealthservices.org/location/villa-maria-nursing-center/', 'request_time': '2026-07-20T22:23:09.111788+00:00', 'classification': 'HTTP_403'}
- Relevant info present: NO
- Extractor ran: NO
- Claim extracted: NO
- Extracted value: []
- Facility identity matched: YES
- Field mapped: NO
- Normalization result: []
- Evidence created: NO
- Verification status: []
- Persisted: NO
- Unknown resolved: NO
- Exact failure point: SOURCE_ACCESS_FAILURE

### Request 10251 | VILLA MARIA NURSING CENTER | CMS Provider Dataset
- CMS ID: 105232
- Target field: cms_overall_quality|staffing|certified_beds|ownership
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/4pq5-n9py', 'request_time': '2026-07-20T22:22:48.629196+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['VILLA MARIA NURSING CENTER', '1050 NE 125TH STREET', '2', '4', '5']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['STALE_REFRESHED', 'UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10253 | VILLA MARIA NURSING CENTER | CMS Inspection Dataset
- CMS ID: 105232
- Target field: health_inspection|regulatory_findings|penalties_fines
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/r5ix-sfxw', 'request_time': '2026-07-20T22:22:50.780945+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"deficiency_count": 23, "severe_deficiency_count": 3, "survey_dates": ["2022-12-01", "2024-03-15", "2025-07-31", "2025-09-05"]}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

### Request 10255 | VILLA MARIA NURSING CENTER | CMS Quality Dataset
- CMS ID: 105232
- Target field: quality_measures
- Request result: RAN_CONNECTED_NO_NEW_VALUE
- HTTP/access: {'response_code': 200, 'failure_reason': None}
- Content received: {'response_type': 'text/html; charset=UTF-8', 'response_size': 2196, 'final_url': 'https://data.cms.gov/provider-data/djen-97ju', 'request_time': '2026-07-20T22:22:52.495580+00:00', 'classification': 'CONNECTED_NO_DATA'}
- Relevant info present: YES
- Extractor ran: YES
- Claim extracted: YES
- Extracted value: ['{"measure_codes": ["401", "404", "406", "407", "408", "409", "410", "415", "430", "434"], "quality_rows": 17}']
- Facility identity matched: YES
- Field mapped: YES
- Normalization result: ['UNCHANGED']
- Evidence created: YES
- Verification status: ['VERIFIED']
- Persisted: YES
- Unknown resolved: NO
- Exact failure point: OTHER

