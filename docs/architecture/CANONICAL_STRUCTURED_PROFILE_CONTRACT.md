# OOmnik Canonical Structured Profile Contract — Draft v0.1

Status: DRAFT / SHADOW ONLY. This document does not transfer production authority.

## Authority boundary

Natural-language AI has one authority only: extract client language into this contract. It does not decide readiness, MUST/NICE status, care type, facility eligibility, ranking, budget expansion, geographic filtering, evidence sufficiency, or the next fact to collect.

Question buttons write directly to the same profile. Deterministic policy selects the next unresolved fact. AI may phrase that already-selected question.

The decision engine accepts only a client-confirmed Structured Profile. Raw client narrative is never a decision-engine input after cutover.

## Envelope

```json
{
  "schema_version": "oomnik-structured-profile/0.1",
  "profile_status": "DRAFT|CONFIRMED",
  "fields": {},
  "out_of_schema": [],
  "conflicts": [],
  "unprocessed": []
}
```

Every atomic field is represented as:

```json
{
  "value": null,
  "state": "EXPLICIT|NEGATED|UNCLEAR|UNKNOWN|CONFLICT",
  "provenance": "BUTTON|AI_EXTRACTED",
  "quote": null,
  "source_question_key": null
}
```

Rules:
- AI_EXTRACTED requires an exact quote present in the supplied family text.
- BUTTON never requires a quote; source_question_key is required.
- CONFLICT is never resolved silently. It becomes a deterministic clarification target.
- OUT_OF_SCHEMA and UNPROCESSED never affect matching or ranking.
- A negated fact is not a positive requirement.
- Only the owner-approved CONFIRMED profile is eligible for decision execution.

## Current questionnaire mapping

The initial schema must preserve all existing QuestionnaireState business facts, including:

### Identity and timing
relationship, gender, ageGroup, coupleAssistance, moveTiming, careSearchApproach.

The interpreter may supply `questionnaire_patch_sources`, a flat index of full
patch leaf paths to exact family-text quotes, in addition to statement mappings.
This is source provenance only: the index cannot authorize a new canonical field,
invent a quote, override a button answer, or erase an ambiguous statement state.
Existing packets with exact statement field mappings remain compatible.

### Current support and medical
assistanceLevel; medicalCareProfile.hasOngoingMedicalNeeds, needs, mobilityMethod, transferAssistance, recentFalls, dialysisFrequency, dialysisCenter, dialysisTransportation, oxygenUse, woundCareFrequency, complexConditionDetails, physicianCoordination.

### Memory, safety and transition
memoryStatus; humanIntelligenceV2.transitionRiskProfile.biggestFear, attitudeTowardMove, previousMoves, bereavementStatus, lonelinessRisk, socialIsolationConcern, recentHospitalization, hospitalizationRecency, postHospitalRehabNeed, wanderingConcerns.

### Coverage and affordability
budget, medicareStatus, medicaidStatus.

### Geography
searchState, locationImportant, referenceLocationType, referenceLocationValue, referenceAddress, maximumDistanceMiles, customDistanceMiles, approvedSearchRadiusMiles, distanceFromFamily, nearbyPlaces, nearbyPlacesImportance, personalDestinations; humanIntelligenceV2.distanceProfile.referenceLocations, driveTimes, familyVisitExpectation, familyGeographyModel, emotionalDistanceFactors, optimizationStrategy.

### Future care
futureCarePreference; humanIntelligenceV2.futureCareProfile.agingInPlaceImportance, avoidFutureMovesPreference, continuumOfCarePreference, secureMemoryNeighborhoodNeed, familiarLanguageRequirement.

### Social, family and lifestyle
happinessPreferences, moveLossConcerns, otherInterests; humanIntelligenceV2.socialProfile.*, familyProfile.*, communityPreferenceProfile.preferredEnvironment, personalityProfile.*, interestsProfile, independenceProfile.*.

### Culture, language and food
humanIntelligenceV2.culturalProfile.*, languageProfile.*, foodProfile.dietaryPreferences, familyCultureProfile.*.

### Practical
parkingRequirement, parkingVehicleCount.

### Completion metadata
questionnaireCompletion is workflow metadata, not a client fact. It remains outside fields and is derived deterministically.

### Excluded derived/scoring data
humanIntelligenceV2.confidence and scoringEngine.*, distanceProfile.scores/inferredConfidence, AI readiness, AI ranking, inferred care strategy and facility evidence are not client-profile facts and must not be writable by the language extractor.

## OUT_OF_SCHEMA

Each item:
```json
{"text":"exact family text","quote":"exact quote","reason":"NO_CANONICAL_FIELD","status":"OUT_OF_SCHEMA"}
```

Examples: a preference or constraint with no approved schema field. These are shown at confirmation and collected for schema-governance review; they have zero decision weight.

## UNPROCESSED

Used when semantic extraction is unavailable. Structured BUTTON facts remain usable. Narrative is retained for later retry but has zero decision weight until extracted and confirmed.

## Conflict policy

If BUTTON and AI_EXTRACTED disagree on the same fact, create CONFLICT with both candidates and their provenance. Deterministic policy selects that fact for clarification. No source wins automatically.

## Question authority

A deterministic completeness policy owns:
1. required field set;
2. conditional field dependencies;
3. UNCLEAR/CONFLICT resolution priority;
4. next target_fact_key.

AI may receive target_fact_key + allowed answer contract and produce wording only. It cannot choose another target.

## Facility evidence AI

Provider-document AI follows the same pattern in a separate evidence contract: extraction only, exact source/provenance, explicit UNKNOWN/CONFLICT, then deterministic evidence policy. It never directly changes eligibility or rank.

## Golden gates before cutover

### Interpreter set
Real website payload -> real model -> Structured Profile.
Predeclared thresholds:
- 100% correctness on mandatory fields, including negation.
- >=95% correctness across all scored fields.
- zero AI quotes absent from source text.
- zero cases where new extraction is wrong and legacy is correct on a mandatory field.
- owner approves every expected result.

### Decision set
Confirmed Structured Profile -> deterministic decision engine -> expected filtering/ranking. No AI interpreter participates. Payloads must be captured from the real website contract, not hand-shaped substitutes.

Every production bug becomes a golden case before its fix is accepted.

## Migration order

1. AI-unavailable structured fallback + UNPROCESSED.
2. Golden Decision Set and merge gate.
3. Versioned Structured Profile + provenance/state/quote.
4. Shadow interpreter on Golden Interpreter Set; legacy remains production authority.
5. Measure against fixed thresholds.
6. Owner approval for cutover.
7. Decision engine reads confirmed Structured Profile only.
8. Remove duplicate language interpreters and frontend decision authority only after parity/cutover evidence.

## Freeze

During shadow migration, legacy interpreters are frozen except critical production fixes. Any exception must be documented and reflected in the comparison baseline.


## Conversational AI ownership — owner clarification

The client experience is not a form. The AI is the conversational expert and owns the dialogue experience end-to-end: it explains why a fact matters, acknowledges prior answers, phrases the next question naturally, gives short relevant education, reflects uncertainty, and prepares the final understanding for confirmation.

Decision authority remains separate. Deterministic policy supplies the AI with the next target fact, allowed answer contract and any safety/decision context. The AI may decide *how to conduct that turn* — wording, explanation, tone and concise follow-up framing — but may not silently choose a different decision fact, infer an unconfirmed value, promote a preference to MUST, or decide facility eligibility/ranking.

The UI may render buttons/choices inside the conversation, but they are interaction controls in an expert-led dialogue, not a visible conventional form.
