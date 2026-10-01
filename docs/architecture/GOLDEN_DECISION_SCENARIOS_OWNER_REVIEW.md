# OOmnik Golden Decision Scenarios — Owner Review Draft v0.1

Purpose: owner-approved business truth for the deterministic decision engine. These cases start from a CONFIRMED Structured Profile. They do not test natural-language interpretation.

Global invariants for every scenario:
- UNKNOWN is never PASS.
- Explicit MUST failure excludes a facility.
- No facility outside an approved hard geographic radius may be shown as a recommendation.
- Active/required licensing evidence is enforced according to the jurisdiction/care type policy.
- Budget is a ranking band, not a hard exclusion, within the owner-approved +10% tolerance. Every candidate must still pass every non-budget MUST.
- Eligible options at or below the stated budget are shown first. Eligible options above budget may follow, but never above +10%, and every such card visibly states the dollar and percentage deviation.
- OOmnik does not calculate or hide an arbitrary number of over-budget options merely to fill a target count. It shows the best eligible matches in these two bands and explains when few options meet the requested budget.
- NICE preferences influence order only after all MUST gates pass.
- Missing provider evidence is surfaced as pending verification, never invented.
- AI never changes eligibility or deterministic business facts.

## D01 — Independent, social, no clinical need
Profile: mother 76; fully independent; no memory issue; no ongoing medical need; $5,000/mo; Las Vegas; 20 mi; highly social; large/active community preferred.
Expected MUST: geography, budget policy, applicable licensing. No ADL, medication, memory-care or SNF MUST.
Allowed care: Independent Living; Assisted Living only when it is a valid non-overlevel strategy under the approved care-setting policy.
Forbidden: Memory-Care-only, Rehab-only, SNF-only as leading recommendations.
Ranking: in-budget first; then social/activity/community-size evidence.
Expected explanation: independence is preserved; social preferences affect ranking, not eligibility.

## D02 — Moderate dementia with wandering risk
Profile: father 83; moderate dementia; wandering concern; ADL support; $7,000; Las Vegas; 20 mi.
Expected MUST: memory care capability, secure/wandering safety, required ADL support, geography, budget.
Allowed care: Memory Care or a verified setting with the same required secure memory capability.
Forbidden: ordinary IL/AL without verified secure memory capability.
UNKNOWN secure-memory/wandering evidence: pending, not recommendation.
Ranking: verified safety/care capability before lifestyle NICE.

## D03 — Post-hospital hip rehabilitation
Profile: father 84; recent hip replacement; time-limited rehabilitation/PT; immediate move; Medicare known; $7,000; Las Vegas; 20 mi.
Expected MUST: rehabilitation capability appropriate to the confirmed clinical profile, geography, budget and any confirmed coverage constraint.
Allowed care: Rehab/SNF when clinically required; another category only with verified equivalent required capability.
Forbidden: IL and Memory-Care-only.
Ranking: verified rehab capability and relevant quality/safety evidence first; lifestyle later.

## D04 — Couple, one needs daily care
Profile: couple 82+; one spouse needs ADL/medication support; other independent; must remain together; $8,000 combined; Henderson; 20 mi.
Expected MUST: couple co-residence/occupancy, required ADL/medication support for spouse, geography, combined affordability.
Forbidden: a facility that can serve the care need but cannot house the couple together.
UNKNOWN couple policy: pending verification.
Ranking: same-unit/together solution first; then practical/lifestyle NICE.

## D05 — High ADL need, constrained budget, Medicaid pathway
Profile: mother 85; substantial ADL support; $3,000; Las Vegas; 30 mi; Medicaid approved/pending/may qualify as confirmed.
Expected MUST: ADL support, Medicaid pathway when confirmed required, geography, budget rule.
Budget: never show >$3,300. In-budget before +10% exceptions.
If no verified candidate exists: honest no verified recommendation / research state, not a fabricated fit.
A negative Medicaid answer must not create a Medicaid facility MUST.

## D06 — Early memory change, resistant to moving
Profile: father 78; forgets medication/appointments; no confirmed wandering; resistant to move; $6,000.
Expected MUST: only confirmed current care/safety requirements. Resistance/attitude is not a facility hard gate.
Do not automatically escalate to secure Memory Care solely from mild forgetfulness.
Ranking/NICE: familiar/smaller environment and transition support may influence ordering if explicitly preferred.
Expected dialogue consequence belongs to interpreter/conversation set, not decision eligibility.

## D07 — Hebrew + kosher
Profile: grandmother 83; needs dressing/meal-prep assistance; kosher is explicitly required; Hebrew preferred unless explicitly stated required; $6,500; Las Vegas; 30 mi.
Expected MUST: ADL support, kosher accommodation, geography, budget.
Hebrew: NICE by default; MUST only if client confirms it is non-negotiable.
UNKNOWN kosher evidence: pending.
Ranking: after MUST, verified Hebrew/language support improves order.

## D08 — Recently widowed, isolation risk
Profile: mother 79; independent; recently widowed; social connection very important; $5,000; Las Vegas; 30 mi.
Expected MUST: no invented ADL or clinical requirement from bereavement language.
Allowed leading care: independent settings appropriate to confirmed needs.
Ranking: social programming/community fit strongly differentiates among MUST-eligible options.
Bereavement/loneliness affects transition/lifestyle fit, not clinical eligibility unless another confirmed fact requires care.

## D09 — Dialysis + wound care
Profile: father 76; dialysis 3x/week; wound care; $7,500; Las Vegas; 20 mi.
Expected MUST: verified ability to support the confirmed dialysis logistics/coordination and wound-care requirement (including outside-care solution only where policy verifies the complete delivery chain), geography, budget.
UNKNOWN clinical capability: pending, never PASS.
Forbidden: facilities unable to satisfy either clinical MUST.
Ranking: verified clinical delivery and relevant safety/quality before NICE.

## D10 — Self-planning, continuum required
Profile: self, early 70s; independent today; explicitly requires continuum/CCRC future-care path; $9,900; Las Vegas; 50 mi.
Expected MUST: verified continuum-of-care path, geography, budget.
Forbidden: IL-only or AL-only without verified required future-care path.
If future care is merely Preferred, it becomes NICE instead of MUST.
Ranking: continuum evidence first, then lifestyle.

## D11 — Explicit negation: no memory care
Profile: independent client explicitly confirms no memory-care need and no cognitive impairment.
Expected: no MEMORY_CARE MUST may be created. Negated fact cannot become positive requirement.
Memory-care-only facility cannot be promoted because of the negated sentence.

## D12 — Elevator versus patient lift
Profile: mobile client requires an elevator/building accessibility; no transfer-lift need.
Expected: no transfer-assistance or mechanical-lift clinical MUST.
Elevator/accessibility is its own practical/accessibility fact if represented in schema; otherwise OUT_OF_SCHEMA until approved.

## D13 — Bereavement word must not imply ADL
Profile includes: spouse sadly passed away; client otherwise fully independent.
Expected: no ADL/medication/clinical MUST created from bereavement wording.
Social/transition preferences only when confirmed.

## D14 — Location hard radius
Profile: Henderson reference address/location; maximum 15 miles; location constraint confirmed hard.
Expected: every recommended facility with measurable distance is <=15 miles from the confirmed reference point.
Facilities outside radius excluded regardless of match score.
Unknown/unmeasurable location evidence cannot silently PASS a hard radius.

## D14B — Named supported area radius
Profile: Summerlin reference area; maximum 10 miles; location constraint confirmed hard.
Expected: Summerlin resolves to an approved canonical geographic entity/coordinate; every measurable recommendation is within 10 miles. The product must not offer a named area it cannot geocode.

## D15 — Duplicate location text robustness
Confirmed structured profile contains Las Vegas once; narrative may contain duplicated wording such as “Las Vegas Las Vegas”.
Expected decision output is identical because raw narrative is not consumed by the decision engine.

## D16 — Budget: strong in-budget supply
Profile budget $6,000.
Expected: every otherwise-qualified option <=$6,000 is ordered before any otherwise-qualified option from $6,000.01–$6,600. Over-budget cards may still be shown after the in-budget group and must state the deviation. No candidate >$6,600 is shown.

## D17 — Budget: no in-budget matches but options inside tolerance
Profile budget $4,300; otherwise-qualified verified alternatives exist from $4,328 up to $4,730.
Expected: show the best eligible matches within the +10% band; each is clearly labelled above budget with dollar and percentage deviation. Explain that no verified option was found at or below $4,300. Never show >$4,730.

## D18 — Budget tolerance cannot rescue another MUST failure
Candidate price is +5% but fails a clinical/location/licensing MUST.
Expected: excluded. The +10% tolerance changes only budget disposition/order; it never relaxes another MUST.

## D19 — Unknown price
Profile has hard budget. Candidate has no verified/current usable price.
Expected: budget MUST pending verification; candidate cannot be called a verified final recommendation merely because other facts match.

## D20 — Explicit Medicaid MUST versus negative Medicaid
A: client confirms Medicaid is required/approved/pending/may qualify -> facility Medicaid pathway must be verified.
B: client confirms not eligible/not using Medicaid -> no Medicaid facility MUST.
C: free text says “must accept Medicaid” and client confirms extracted fact -> Medicaid MUST.
No model paraphrase may override a confirmed structured negative.

## D21 — Required versus preferred future care
Same resident facts, two profiles:
A continuumOfCare = REQUIRED -> hard gate.
B continuumOfCare = PREFERRED -> ranking preference.
Expected candidate universe differs only because of this explicit state, not because AI wording differs.

## D22 — Dietary preference versus dietary safety MUST
A low-sodium preference -> NICE unless client confirms requirement/safety necessity.
B celiac/gluten cross-contact safety explicitly required -> MUST.
C kosher explicitly required -> MUST.
No generic “dietary accommodation important” model wording may promote A.

## D23 — Pet
Client has a dog and keeping the pet is explicitly non-negotiable.
Expected: if pet policy has an approved canonical field/evidence contract, it is a MUST; until then it is OUT_OF_SCHEMA and must be shown for owner/client handling, with zero hidden decision weight.
A mere pet preference is NICE after schema support exists.

## D24 — Close to daughter in Summerlin
Client says being near daughter at a specific Summerlin address is important.
Expected: when captured as personalDestination/reference location with hard distance importance, geography uses that canonical coordinate/address. If not representable, OUT_OF_SCHEMA; never silently interpreted by ranking.

## D25 — Availability required
Move within 30 days and client explicitly requires current availability.
Expected: verified current availability is MUST when the business contract defines it as required. Unknown availability is pending; explicit no availability fails. If availability is merely preferred, it ranks after MUST.

## D26 — Licensing
Care type/jurisdiction requires an active license.
Expected: required license absent/expired/invalid -> exclude; evidence unknown -> pending verification. For a category where that license is not legally required, absence is disclosed rather than automatically excluded according to the approved regulatory policy.

## D27 — Contradictory button and narrative
Button says no memory problem; extracted narrative says “she has dementia”.
Expected Structured Profile: CONFLICT. Decision engine does not receive a silently chosen value. Deterministic dialogue policy selects memoryStatus for clarification; confirmed answer resolves conflict.

## D28 — AI unavailable after complete button intake
All mandatory/conditional structured answers complete; notes contain extra free text; semantic AI fails.
Expected: structured facts remain usable; notes = UNPROCESSED and have zero decision weight; family sees explicit disclosure and can confirm structured-only profile. No dead end.

## D29 — AI unavailable before required structured facts complete
Required fact missing and semantic AI fails.
Expected: deterministic completeness policy identifies missing fact; conversation continues using structured answer controls. AI failure does not invent an answer. No recommendations until required fact is resolved.

## D30 — Out-of-schema statement
Client adds a meaningful constraint with no canonical field.
Expected: exact statement appears in OUT_OF_SCHEMA on confirmation; zero matching/ranking effect; retained for schema-governance review. It is not dropped and not converted to a generic MUST.

## D31 — Unknown provider evidence
Client MUST is confirmed, but facility evidence is UNKNOWN.
Expected: facility is pending verification for that MUST, not failed and not passed. Research queue may act; visible final recommendation requires governed PASS.

## D32 — Explicit negative provider evidence
Facility has verified evidence that it cannot meet a client MUST.
Expected: hard FAIL/exclude. AI ranking cannot rescue it.

## D33 — NICE cannot outrank failed MUST
Facility A perfectly matches lifestyle but fails one MUST. Facility B passes every MUST but has weaker NICE evidence.
Expected: B is eligible/rankable; A excluded.

## D34 — True tie
Two facilities have identical verified decision evidence.
Expected: joint rank / explicit true tie. Facility name/alphabetical order may be deterministic display order only, not a claimed quality difference.

## D35 — Couple surcharge / total affordability unknown
Couple profile has base room price but no verified second-person/care surcharge.
Expected: if total monthly affordability cannot be verified, budget status is pending; do not claim within-budget from base rent alone.

## D36 — Care fee / level-of-care fee unknown
Base rent fits budget but required care fee is unknown.
Expected: total affordability pending until the approved price model can verify relevant care charges. No false budget PASS.

## D37 — Outside-care agency solution
Facility itself lacks a required support but permits outside care.
Expected: permission alone is not PASS. Only a verified agency/service chain covering the exact required support can satisfy the combined-care rule.

## D38 — Preference evidence missing
All MUSTs pass; one facility has unknown social/language/activity preference evidence.
Expected: unknown NICE is not negative evidence. Ranking explanation states missing evidence; it cannot be treated as a mismatch.

## D39 — Confirmed profile immutability
After client confirms profile, unrelated narrative text or stale earlier answers cannot mutate decision facts without creating a new draft/version and re-confirmation.
Expected: recommendations are bound to confirmed schema version/profile version.

## D40 — Old CRM case / schema migration
Stored case uses earlier schema_version.
Expected: it remains readable through explicit version migration/compatibility logic; missing new fields are UNKNOWN, not fabricated defaults; no historical confirmed fact is silently reinterpreted.

## Owner-review fields to add before gate activation

For each scenario, the executable fixture must include:
- scenario_id and schema_version;
- exact confirmed Structured Profile;
- expected MUST keys;
- expected NICE keys;
- expected forbidden care types;
- expected eligible/pending/excluded facility IDs from the fixed synthetic 200-facility corpus;
- expected top ordering or true-tie groups;
- expected budget/location/licensing/availability disposition;
- expected client-facing explanation assertions.

Facility IDs and exact top order must be generated from the frozen synthetic corpus, then reviewed and approved by the owner before they become golden truth. The engine or AI may not self-author the expected answer.


## Owner-approved budget presentation (2026-10-01)

The stated budget remains the family's stated number. OOmnik applies a fixed product tolerance of +10% without asking the family to restate a higher ceiling.

Results presentation:
1. show the best fully eligible matches at or below budget first;
2. then show the best fully eligible matches up to +10%;
3. label every over-budget result with exact dollar and percentage deviation;
4. never let the tolerance repair another MUST failure;
5. when only a small number meet the requested budget, say how many were found and invite the family to use Oomniker to change parameters and reveal additional options;
6. Oomniker never changes budget/radius/preferences without the family's action.

Example client framing: “We found 2 communities that meet your requirements within your requested budget. Below are additional strong matches that are slightly above it. You can use Oomniker to adjust your preferences and reveal more options.”


## Owner decisions — 2026-10-01

- Result count: show up to 10 recommendations.
- True ties: preserve the true tie; do not manufacture a ranking distinction. Present the tied options and offer Oomniker so the family can adjust parameters/preferences if they want to differentiate or reveal alternatives.
- Pets: an explicitly non-negotiable pet requirement is a MUST. A preference remains NICE.
- Personal destination / proximity constraints: do not force the family through an extra REQUIRED-vs-PREFERRED question. Treat the stated target as the preferred result band. Show the best matches that satisfy it first; when supply is insufficient, continue with the best otherwise-eligible options outside the target and visibly state the distance/deviation, following the same transparent fallback presentation principle used for budget. Never imply that an outside-target option met the requested proximity.
