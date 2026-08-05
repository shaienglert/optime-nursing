# Realistic Synthetic Facility Simulation

- Dataset: `REALISTIC_SYNTHETIC_FACILITY_INTELLIGENCE_V1`
- Boundary: synthetic validation data only; canonical facility data is unchanged.
- Result: **PASS**

## Coverage Distribution

| Facility | Known coverage | Unknown | Missing | Stale | Contradicted | N/A |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Alder Grove Recovery Center | 85.0% | 1 | 2 | 0 | 1 | 0 |
| Bayshore Multilingual Care | 80.0% | 0 | 4 | 0 | 0 | 0 |
| Cedar Peak Neuro Rehabilitation | 75.0% | 4 | 1 | 0 | 0 | 1 |
| Downtown Daily Support Residence | 60.0% | 1 | 7 | 0 | 1 | 1 |
| Evergreen Full-Service Nursing | 80.0% | 2 | 2 | 0 | 1 | 0 |
| Festival Gardens Assisted Living | 55.0% | 2 | 7 | 0 | 0 | 0 |
| Gulf View Care Unknown Profile | 25.0% | 1 | 14 | 0 | 0 | 0 |
| Harbor Value Senior Community | 60.0% | 2 | 6 | 0 | 0 | 1 |
| Ivy Historic Nursing Pavilion | 75.0% | 2 | 3 | 10 | 0 | 0 |
| Juniper Memory and Wellness | 80.0% | 3 | 1 | 0 | 1 | 0 |

## Ranking Outcome

| Rank | Facility | Archetype | Eligibility | Match | Evidence certainty | Quality |
| --- | --- | --- | --- | ---: | ---: | ---: |
| #1 | Alder Grove Recovery Center | strong facility with strong evidence | ELIGIBLE | 91.15 | 92.86 | 70.0 |
| #2 | Evergreen Full-Service Nursing | broad services with recent regulatory negatives | ELIGIBLE | 86.67 | 85.71 | 0.0 |
| #3 | Cedar Peak Neuro Rehabilitation | excellent rehabilitation evidence with lifestyle and dietary gaps | ELIGIBLE | 84.79 | 85.71 | 70.0 |
| #4 | Harbor Value Senior Community | affordable but clinically incomplete facility | POTENTIALLY_ELIGIBLE | 91.56 | 57.14 | 62.0 |
| #5 | Bayshore Multilingual Care | strong language and daily support with weak staffing coverage | POTENTIALLY_ELIGIBLE | 90.23 | 78.57 | 62.0 |
| #6 | Ivy Historic Nursing Pavilion | historically known facility with a large stale share | POTENTIALLY_ELIGIBLE | 90.0 | 28.57 | None |
| #7 | Downtown Daily Support Residence | strong location and daily support with contradictory rehabilitation evidence | POTENTIALLY_ELIGIBLE | 89.0 | 53.57 | 62.0 |
| #8 | Gulf View Care Unknown Profile | facility with many unknowns and no negative evidence | POTENTIALLY_ELIGIBLE | 81.67 | 21.43 | None |
| #9 | Festival Gardens Assisted Living | weaker facility with complete marketing claims | POTENTIALLY_ELIGIBLE | 80.36 | 50.0 | None |
| #10 | Juniper Memory and Wellness | specialized dementia facility with only moderate stroke relevance | INELIGIBLE | 79.09 | 78.57 | 70.0 |

## Behavioral Assertions

- Strong Verified Beats Marketing Rich: **PASS**
- Lower Coverage Can Outrank Higher Coverage On Relevance: **PASS**
- Many Unknowns Gain No False Negative: **PASS**
- Stale Evidence Not Counted As Proven: **PASS**
- Contradictions Preserved: **PASS**
- Specialized Mismatch Detected: **PASS**
- Regulatory Negatives Reduce Quality: **PASS**
- Coverage Not Used As Generic Score: **PASS**

## Contradiction And Missingness Trace

### Alder Grove Recovery Center

- `published_rates`: **CONTRADICTED** — Published monthly rate is $7,200, while the current admissions quote is $8,050.
- `current_availability`: **UNKNOWN** — Bed availability changes daily and no same-day confirmation was obtained.
- `dietitian`: **UNKNOWN** — No current source was collected because these fields were not central to this rehabilitation profile.
- `memory_care`: **UNKNOWN** — No current source was collected because these fields were not central to this rehabilitation profile.

### Evergreen Full-Service Nursing

- `languages`: **UNKNOWN** — Language availability varies by shift and no current shift roster was supplied.
- `current_availability`: **UNKNOWN** — No current bed census was provided.
- `memory_care`: **CONTRADICTED** — The website claims memory care, but the current synthetic license scope does not authorize a memory-care unit.
- `published_rates`: **UNKNOWN** — Rates are not published and a family-origin distance was not supplied.
- `distance_miles`: **UNKNOWN** — Rates are not published and a family-origin distance was not supplied.

### Cedar Peak Neuro Rehabilitation

- `gluten_free`: **UNKNOWN** — The menu lists gluten-free dishes but does not address medical cross-contamination controls.
- `dietitian`: **UNKNOWN** — No current dietitian assignment could be linked to this rehabilitation program.
- `current_availability`: **UNKNOWN** — Program availability depends on daily discharge and authorization status.
- `activities`: **UNKNOWN** — No dated activity calendar or current resident-program source was published.
- `languages`: **UNKNOWN** — Language staffing was not published for the current shift roster.
- `memory_care`: **NOT_APPLICABLE** — This is a pure rehabilitation program without a memory-care service line.

### Harbor Value Senior Community

- `ot`: **UNKNOWN** — The contract directory confirms PT but does not list occupational therapy.
- `medicare_attributes`: **NOT_APPLICABLE** — Skilled-nursing Medicare reimbursement does not apply to this assisted-living-only community.
- `current_availability`: **UNKNOWN** — Availability changes daily and the quoted room was not held.
- `speech_therapy`: **UNKNOWN** — The assisted-living sources do not establish these clinical program capabilities or specialist staffing fields.
- `post_stroke_neuro_evidence`: **UNKNOWN** — The assisted-living sources do not establish these clinical program capabilities or specialist staffing fields.
- `therapy_frequency`: **UNKNOWN** — The assisted-living sources do not establish these clinical program capabilities or specialist staffing fields.
- `dietitian`: **UNKNOWN** — The assisted-living sources do not establish these clinical program capabilities or specialist staffing fields.
- `therapy_staffing`: **UNKNOWN** — The assisted-living sources do not establish these clinical program capabilities or specialist staffing fields.
- `memory_care`: **UNKNOWN** — The assisted-living sources do not establish these clinical program capabilities or specialist staffing fields.

### Bayshore Multilingual Care

- `speech_therapy`: **UNKNOWN** — Clinical staffing and rehabilitation-frequency sources were not available in the current collection window.
- `post_stroke_neuro_evidence`: **UNKNOWN** — Clinical staffing and rehabilitation-frequency sources were not available in the current collection window.
- `therapy_frequency`: **UNKNOWN** — Clinical staffing and rehabilitation-frequency sources were not available in the current collection window.
- `therapy_staffing`: **UNKNOWN** — Clinical staffing and rehabilitation-frequency sources were not available in the current collection window.

### Ivy Historic Nursing Pavilion

- `adl_support`: **STALE_OFFICIAL** — No current service-scope record replaced the 2019 filing.
- `medication_support`: **STALE_OFFICIAL** — Medication-service evidence has not been refreshed since 2019.
- `transfer_assistance`: **STALE_OFFICIAL** — Transfer capability has not been reverified after ownership changes.
- `nursing_24_7`: **STALE_OFFICIAL** — The certification record is historical and current staffing is missing.
- `pt`: **STALE_OFFICIAL** — PT evidence predates the current therapy contract.
- `ot`: **STALE_OFFICIAL** — OT evidence predates the current therapy contract.
- `speech_therapy`: **STALE_OFFICIAL** — Speech-therapy evidence predates the current therapy contract.
- `therapy_frequency`: **STALE_OFFICIAL** — No current schedule confirms that daily frequency continues.
- `published_rates`: **STALE_OFFICIAL** — The filed rate predates multiple annual price cycles.
- `current_availability`: **UNKNOWN** — Current availability was not supplied.
- `therapy_staffing`: **UNKNOWN** — The latest staffing file contains no therapy-staffing value.
- `inspection_rating`: **STALE_OFFICIAL** — No current synthetic regulatory inspection is available.
- `dietitian`: **UNKNOWN** — No current source covers nutrition staffing, lifestyle programming, or specialist memory care.
- `activities`: **UNKNOWN** — No current source covers nutrition staffing, lifestyle programming, or specialist memory care.
- `memory_care`: **UNKNOWN** — No current source covers nutrition staffing, lifestyle programming, or specialist memory care.

### Downtown Daily Support Residence

- `therapy_frequency`: **CONTRADICTED** — The website claims seven-day therapy, but the current staffing roster supports weekdays only.
- `medicare_attributes`: **NOT_APPLICABLE** — Skilled-nursing Medicare reimbursement does not apply to this assisted-living-only community.
- `current_availability`: **UNKNOWN** — Apartment availability changes daily and was not confirmed.
- `ot`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.
- `speech_therapy`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.
- `post_stroke_neuro_evidence`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.
- `dietitian`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.
- `published_rates`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.
- `therapy_staffing`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.
- `memory_care`: **UNKNOWN** — No scoped source supports these clinical, price, staffing, or specialist-program fields.

### Gulf View Care Unknown Profile

- `current_availability`: **UNKNOWN** — The facility did not respond to the current availability request.
- `medication_support`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `transfer_assistance`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `nursing_24_7`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `pt`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `ot`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `speech_therapy`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `post_stroke_neuro_evidence`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `therapy_frequency`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `languages`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `gluten_free`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `dietitian`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `therapy_staffing`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `inspection_rating`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.
- `memory_care`: **UNKNOWN** — No parameter-specific clinical, staffing, language, diet, inspection, or specialist-program source was found; absence is not negative evidence.

### Festival Gardens Assisted Living

- `medication_support`: **UNKNOWN** — The website mentions wellness support but does not define medication-management scope.
- `current_availability`: **UNKNOWN** — Marketing says accepting residents, but no unit-level availability was confirmed.
- `ot`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.
- `speech_therapy`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.
- `post_stroke_neuro_evidence`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.
- `therapy_frequency`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.
- `medicare_attributes`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.
- `therapy_staffing`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.
- `inspection_rating`: **UNKNOWN** — Marketing materials provide no clinical proof, reimbursement record, staffing submission, or regulatory result for these fields.

### Juniper Memory and Wellness

- `speech_therapy`: **UNKNOWN** — Speech therapy is not listed in the current contract directory.
- `therapy_frequency`: **UNKNOWN** — The page describes therapy broadly but provides no frequency or staffing schedule.
- `languages`: **CONTRADICTED** — A directory lists Hebrew-speaking staff, but the latest facility confirmation says availability is not guaranteed by shift.
- `current_availability`: **UNKNOWN** — Secured-unit availability changes daily and was not confirmed.
- `published_rates`: **UNKNOWN** — The community does not publish rates and no current admissions quote was obtained.
