# Pilot acceptance cases

Ten family situations, run end to end through the decision engine against the
`synthetic-pilot` market, and graded against the pilot catalog rather than against
anything the engine says about itself.

```bash
python scripts/pilot_acceptance/run_all.py
python scripts/pilot_acceptance/run_all.py --case 10_couple_different_needs   # one case
```

Exits non-zero if any case fails. A per-case JSON snapshot and log are written to
`--out` (default `pilot-acceptance-out/`).

## Why this market

The pilot catalog carries, for all 200 communities, a curated record (type, archetype,
whether it houses couples, capacity) and verified evidence for 31 parameters including
`current_price`. That makes it the only market where a recommendation can be independently
checked: the real Nevada licence registry has no price evidence, so every candidate there
sits pending verification and nothing about matching quality can be concluded from it.

Runs expose all 200 communities (`OOMNIK_PILOT_FACILITY_LIMIT=200`). The product default
is 50, which is fine for a demo and useless for a benchmark.

## How a case is graded

`oracle.py` never reads the engine's fit verdict. For every recommendation it looks up the
community's own record and checks:

- **Budget.** Its `current_price` against the budget on the family's needs profile.
- **Capabilities.** Every parameter the profile marks REQUIRED or HIGH is actually `YES`
  on that community.
- **Setting.** Its `synthetic_archetype` against the case's `never_archetypes`, and
  against `any_of_archetypes` where the situation demands a particular kind of community.
- **Couples.** For a couple, that `accepts_couples` is true.

`never_archetypes` is the half that catches real harm. That a dementia case reaches memory
care is easy; the failures that cost a family money and independence are the opposite —
help with bathing answered by a nursing home, mild forgetfulness answered by a locked
memory unit.

Case 9 asserts the reverse: no community in the pilot that provides ADL support costs
$3,000 or less, so the correct answer is no recommendations plus a notice saying why.
Presenting anything there would be a failure.

## The interview AI

With `OPTIME_SEMANTIC_AI_API_KEY` set, the interview runs for real. Without it, it is
pinned to a fixed READY answer, every snapshot records `"interview_ai": "MOCKED"`, and the
summary says so. A mocked run leaves ranking on the deterministic fallback, where every
eligible community ties at the same rank — so a mocked pass says matching is sound and
says nothing about ranking quality. Do not read one as the other.

## Adding a case

Add an entry to `cases.py`. The `questionnaire` must answer the client-owned questions a
real interview would ask for that situation — Medicare for a post-hospital case, for
instance. Until they are answered the engine correctly withholds every facility
(`identities_hidden_pending_client_input`), and the case cannot complete; that is a gap in
the test, not in the product.
