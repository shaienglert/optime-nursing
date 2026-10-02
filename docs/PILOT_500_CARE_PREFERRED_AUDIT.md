# 500-community care and preference audit

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
