# OPTIME Master Parameter Registry

## Purpose

OPTIME matches a person to evidenced facility capabilities through parameters. Facility labels such as Nursing Home, Skilled Nursing Facility, Assisted Living, Memory Care, or CCRC are descriptive inputs, not substitutes for capability evidence.

Canonical governing principle: `PR-009 Parameter-First Facility Matching` in `docs/OPTIME_PRINCIPLES_REGISTRY.md`.

## Core Rules

1. Evaluate every case from the person's requirements and preferences outward.
2. Evaluate capabilities at the most specific evidenced level available: facility, campus, unit, program, or service line.
3. Never infer a capability solely from a facility category/title.
4. Never reject a facility solely from a category/title unless a verified legal, regulatory, licensing, or clinical constraint directly makes the case ineligible.
5. `UNKNOWN` is not `NO`.
6. Verified case-relevant evidence may strengthen proven match; generic profile completeness may not.
7. Current availability is a separate dynamic parameter and must be verified with a timestamp for the relevant unit/bed/service, not merely for the facility generally.
8. Facility verification should confirm important known facts and resolve case-relevant unknowns for the Top 10 before the final updated recommendation table.

## Parameter Families

| Family | Example parameters | Preferred evidence |
| --- | --- | --- |
| Identity & licensing | CCN, AHCA license, LID/file number, address, ownership, certification, licensed capacity | CMS, AHCA, other official registries |
| Care capability | skilled nursing, 24/7 nursing, RN availability, medication complexity, transfer assistance, ADL support | Official regulatory data, verified facility evidence |
| Unit/program capability | post-stroke program, memory care unit, enhanced care unit, ventilator/respiratory, dialysis arrangements, wound care | Official source where available, facility/unit verification |
| Rehabilitation | PT, OT, speech therapy, therapy staffing, short-stay rehab, neurological/post-stroke capability | CMS/PBJ/QRP, official facility evidence, verification |
| Staffing | RN/LPN/CNA/PT staffing, turnover, coverage patterns | CMS/PBJ, AHCA where applicable |
| Quality & safety | inspections, deficiencies, fire safety, complaints/citations, penalties, sanctions, quality measures | CMS, AHCA, official regulatory sources |
| Resident-specific fit | diet, gluten-free, kosher, languages, cultural/religious needs, activities, transportation | Verified facility data and current confirmation |
| Accommodation | private/shared room, accessibility, equipment, unit type | Facility/unit verification |
| Financial | current price, payer acceptance, fees, promotions | Current facility confirmation; official payer data where applicable |
| Dynamic availability | appropriate bed/unit availability, admission date, waiting list | Direct current facility confirmation with timestamp |

## Canonical Parameter Record

Each parameter should support the following fields where applicable:

- `parameter_id`
- `parameter_family`
- `canonical_name`
- `case_requirement`
- `value`
- `evidence_state`: VERIFIED_YES / VERIFIED_NO / VERIFIED_VALUE / UNKNOWN / CONFLICTING / STALE
- `scope`: FACILITY / CAMPUS / UNIT / PROGRAM / SERVICE_LINE
- `scope_identifier`
- `source`
- `source_record_id`
- `source_url_or_reference`
- `observed_date`
- `retrieved_date`
- `verified_at`
- `freshness`
- `decision_relevance`
- `requires_facility_confirmation`
- `notes`

## Source Resolution Order

For each parameter, OPTIME should seek the strongest available evidence without treating source count as quality:

1. Official federal structured sources (for example CMS datasets).
2. Official state structured/regulatory sources (for example AHCA/FloridaHealthFinder).
3. Other authoritative official sources.
4. Official facility-published evidence.
5. Other governed public evidence where permitted.
6. Direct facility verification for unresolved or dynamic case-relevant parameters.

Conflicts must remain explicit until resolved; do not silently choose the more favorable value.

## Facility Type Handling

`facility_type` is retained for discovery, navigation, regulatory context, and explanation. It is not a blanket capability rule.

Example: an Assisted Living facility may contain a smaller licensed or otherwise appropriately authorized unit/program capable of serving a higher-acuity case. OPTIME must evaluate that evidenced unit/program capability rather than reject the entire facility because of the umbrella label.

The inverse also applies: a Nursing Home/SNF label does not prove that a facility can satisfy a specific post-stroke, dietary, language, equipment, or other case requirement.

## Candidate Evaluation

For each case:

1. Convert the person's needs/preferences into explicit parameters.
2. Search the broad relevant facility universe rather than pre-filtering solely by marketing/category labels.
3. Apply only verified case-relevant legal/regulatory/licensing/clinical constraints as hard exclusions.
4. Evaluate evidenced capabilities at facility/unit/program level.
5. Preserve unresolved fields as `UNKNOWN`.
6. Produce a provisional evidence-based Top 10.
7. Ask the Top 10 to confirm important known requirements and answer all case-relevant unknowns.
8. Always verify current availability for the appropriate unit/service, plus admission timing, room/bed type, waiting list, current price, and promotions where relevant.
9. Re-run matching after verified responses and explain material ranking changes in descriptive language.

## Customer Availability Disclosure

Before presenting the initial Top 5, the experience must clearly state that recommendations are based on the needs/preferences provided and the information currently available to OPTIME; availability must be confirmed directly with facilities; OPTIME can verify missing information and current availability; and newly verified information may change the ordering of recommendations.

Availability states should be descriptive and timestamped, for example:

- Availability not yet verified
- Appropriate unit availability confirmed on <date/time>
- No appropriate current availability
- Waiting list confirmed

Never imply current availability solely from a facility's general operating status or capability.

## Next Data Work

Build the field-by-field source matrix for all relevant Florida senior-care facility types, not only CMS Nursing Homes. Map every accessible CMS, AHCA/FloridaHealthFinder, and other authoritative field into this registry before semantic ranking changes. The inventory should include Assisted Living and other relevant senior-care settings while preserving facility/unit/program-level capabilities.