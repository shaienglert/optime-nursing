# Facility ↔ resident intake alignment v2
Date: 2026-10-04. Status: implementation draft, not deployed.
## Principle impact
RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-006, PR-007, PR-008, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO for additive form collection/mapping (B: implementation completion, explicitly requested). No new ranking weight, MUST change, universal fit score or automatic promotion of provider claims is authorized.
## Delivered
The existing provider profile editor and save endpoint now consume an additive questionnaire schema: 117 fields in 16 sections, retaining all 33 existing keys. Every one of the 65 IDs in frontend/src/lib/intake-questions.ts has an explicit disposition: provider capability, support context, or existing resident/geospatial data.
The counterpart is a need-to-capability relationship, not a word-for-word copy of the resident's question. Resident age and clinical history are not facility desirability variables. Personal destinations are evaluated from addresses, not a provider's subjective assertion that it is nearby.
The UI groups sections, uses touch-friendly answer controls and allows numeric, text and date values alongside state answers. Provider details include conditions, scope, delivery, evidence URL and observed date. Details persist in the existing FacilityCapability.notes column with separate audit records; no migration or new table.
A provider-supplied URL is stored, not fetched or independently verified by this endpoint. Submission remains provider-supplied. Missing is UNKNOWN, not NO. Generic profile completeness does not improve ranking.
## Collection examples
| Resident question | Provider counterpart |
|---|---|
| Help with bathing/dressing/toileting/medications | Separate capability for each task |
| One-person, two-person or mechanical transfers | Separate transfer capabilities and service conditions |
| Secure memory care and wandering | Secure-unit capability, scope and wandering response |
| Medical language | Supported medical-discussion languages and interpreter delivery |
| Budget | Scoped base, care, mandatory and second-person monthly fees plus entry fee and quote basis |
| Temporary support | Supported temporary stays and minimum/maximum duration |
| Move date | Earliest admission date, accepting admissions and waiting list |
| Social preferences | Actual schedule, small groups and quiet-space options |
| Daily routine/autonomy | Flexible meals/schedule, outings, privacy and belongings |
| Concern about moving | Transition support capability; no resident penalty |
| Couple | Shared room, different care needs and separation/escalation policy |
## Operational limits
The primary intake has 65 question IDs on pinned main 67303fe78fcf31b1889ce15acef73898c44eaa0f. This contract does not claim coverage of every legacy question graph or of future questions; the test fails when this primary inventory changes without a mapping update.
For each new UNKNOWN, the form provides an answer slot; it does not prove the facility has answered, that any evidence is verified, or that all 500 pilot records have been populated.
The numeric provider profile stores one scoped quote. The existing FacilityRoomType records remain the model for multiple room/care/occupancy quotes; a single quote cannot establish a region's minimum price or universal cost.
Other/unlisted clinical, diet or activity needs require case-specific review. A generic capability YES cannot resolve every possible free-text need.
The canonical engine's facility ID/evidence ingestion path is not changed here. New data is collected and mapped, but there is no automatic ranking use or evidence verification. Before claiming production matching coverage, connect the existing verification/canonical-ID pipeline and demonstrate a verified answer affecting the appropriate resident need in a live journey.
Email verification for real providers remains an existing limitation noted by the page; the isolated OPTICARE demo remains available. This PR does not alter authentication or unlock real community claims.
## Validation
- 13 new contract/persistence/validation tests passed against the actual SQLAlchemy models and in-memory SQLite.
- 27 existing provider portal tests passed, including roles, auditing, unknown behavior and isolated OPTICARE demo.
- TypeScript check passed for edited provider page/API plus downloaded dependencies; this is not a full repository build.
- ESLint check of the edited page/API: see PR validation result.
- No production deployment or live browser verification performed.
## Release acceptance
1. Review UI with a real admissions/clinical operator; confirm permission categories and terminology.
2. Populate and reload numeric quotes, LIMITED conditions and a program-specific third-party capability.
3. Resolve provider identity / canonical ID and run the existing independent verification path.
4. Check relevant matching behavior with pinned resident cases, preserving MUST and UNKNOWN.
5. Deploy and verify provider entry → stored provenance → verified matching input → family explanation.

