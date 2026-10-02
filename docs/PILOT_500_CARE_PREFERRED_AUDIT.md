# 500-community care and preference audit

## Approved service/program contract — 2026-10-02

The owner explicitly selected option 2. `oracle.care` now grades independently
verified services/programs rather than literal building categories, as required by
PR009. See `architecture/PILOT_CARE_PATH_CONTRACT.md` for the exact proof matrix.
The frozen personas, data and their declared care paths were not changed.
`oracle.preferred` enforcement remains active.

The stronger proof first exposed a real engine gap in persona 004: 16 Small Group
Homes beyond the Top-10 passed rehab on PT+OT alone. The new explicit post-hospital
program MUST requires a rehabilitation program, therapy staffing, nursing and
physician coordination. It is registered with evidence loading and the affordability
floor. The engine and independent oracle now agree on 26 eligible communities
for 004; the 16 false positives are removed. Generic outpatient PT/OT access remains
a separate requirement. UNKNOWN remains pending rather than a verified failure.

Local validation: 90/90 focused tests (Golden Decision, full-universe Ranking Oracle,
Oomniker counterfactuals, affordability, intent, and program evidence counterfactuals);
10/10 Pilot Acceptance cases on 500 (interpreter MOCKED). The acceptance memory
case explicitly demands secured-unit evidence; the post-hospital case demands full
rehabilitation proof for every shown recommendation. No fixture facts were changed.

The broader local suite recorded 1176 passes, seven local CORS dependency errors,
and one old Las Ventanas assertion equating a therapy URL
with complete post-hospital clinical proof. It now explicitly requires PENDING and
keeps every previous therapy/couple positive assertion. Real cases with missing
full-program evidence need research; the program is never inferred from that URL. The corrected provider regression and
care-path counterfactual module pass 19/19. Full CI on the new commit is still required.

#424 remains Draft and NO-GO. Live interpreter and browser CI results must be checked
on the new commit; deterministic and mocked results do not authorize cutover.

## Historical literal-category baseline

The following findings describe the earlier, superseded interpretation and its
then-pending owner decision. They are retained as the audit trail.

Catalog and engine baseline: `9812cdd1b4eb342cb58819b6367b260d49c2862d`.
Scope: deterministic structured submissions, 500 synthetic communities, independent
catalog evidence and eligibility oracle. This is not a production or live AI claim.

## Newly enforced contracts

`oracle.care` is checked literally against each Top-10 community archetype.
`oracle.preferred` must reach NICE and have a per-result match, mismatch, or visible
unknown trace. Hebrew matches require catalog language evidence. Nearby places
must disclose a source when known and a reason when unknown. Missing nearby
evidence does not become negative evidence. Unimplemented Oracle keys fail.
Pilot 009 now explicitly requires dialysis transportation, with verified service
evidence; the engine maps an explicit Yes to a REQUIRED transportation need.

## Care failures exposed by literal enforcement

| Persona | Observed Top-10 | Literal care mismatch |
| --- | --- | --- |
| 003 | 8 Memory Care, 2 Continuing Care | 2 Continuing Care |
| 004 | 10 Continuing Care | 10 Continuing Care |
| 007 | Assisted Living and Small Group Home | Small Group Home |
| 009 | 10 Continuing Care | 10 Continuing Care |

These are failing tests, not exclusions or expected failures. No category gate was
added to the engine and the declared care expectations were not changed.

## 004 and 009: price and eligibility

Counts below come from the independent ranking oracle over the entire frozen
catalog. Eligibility includes all other case constraints, not just price.

| Persona | Archetype | Catalog count | Minimum monthly price | Within budget +10% | Eligible |
| --- | --- | ---: | ---: | ---: | ---: |
| 004 ($7,000) | Skilled Nursing | 62 | $8,905 | 0 | 0 |
| 004 ($7,000) | Rehabilitation | 62 | $7,606 | 2 | 1 |
| 004 ($7,000) | Continuing Care | 62 | $5,851 | 31 | 25 |
| 009 ($7,500) | Skilled Nursing | 62 | $8,905 | 0 | 0 |
| 009 ($7,500) | Rehabilitation | 62 | $7,606 | 8 | 4 |
| 009 ($7,500) | Continuing Care | 62 | $5,851 | 42 | 17 |

For 004, Continuing Care with verified PT and OT can occupy the in-budget band;
the eligible Rehabilitation option is in the budget-exception band. For 009,
there are zero eligible communities of either declared care category (Assisted
Living or Skilled Nursing), while Continuing Care and Rehabilitation have
case-relevant evidence. This explains the observed results without proving that
the literal category contract is the correct clinical/product contract.

## Owner decision required for category semantics

Classification: C, Product Principle Ambiguity. Relevant principles: PR-002,
PR-003, PR-005, PR-006, PR-007, PR-009. No principle has been changed.

PR-009 requires matching verified case-relevant capabilities and prohibits using
category alone as blanket inclusion/exclusion absent a verified applicable legal,
licensing, regulatory, or clinical constraint. A literal care-category Oracle can
conflict with that rule even when the facility has a verified relevant program.

Proposed direction: distinguish an explicitly required setting from an expected
care pathway, and grade the latter at verified unit/program/service level. This
would change Oracle semantics and requires owner approval before implementation.
Alternative: require the listed building categories, then document and approve
the corresponding product principle exception and its no-result consequences.
Risk: translating a care pathway into a building type hides valid options;
translating a genuinely mandatory setting into capabilities can ignore a family
requirement. Recommendation: preserve parameter-first matching and make explicit
setting constraints separate. Until resolved, keep the four failures and NO-GO.

Live interpreter verification remains a separate mandatory gate. Passing
deterministic ranking tests cannot authorize production cutover.
