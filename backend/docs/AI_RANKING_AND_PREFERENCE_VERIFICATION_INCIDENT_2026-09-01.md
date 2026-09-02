# AI ranking failure and NICE preference blocking -- 2026-09-01 to 2026-09-02

**Status: both root causes fixed and confirmed live. `main` returns real
recommendations for the traced query as of PR #169 (merged `e5f18fb`).**

Investigation triggered by: production returning zero recommendations for broad,
common search profiles even after MUST evaluation and AI ranking both succeed.
Two independent, unrelated root causes were found. Both are now fixed and
verified against real production traffic, not mocks -- see the timeline at the
end of this document for exactly what each of the three PRs changed and what
each live verification run showed.

## 1. AI batch ranking failure -- FIXED, verified live

### Symptom
`/decision-engine/recommendations` returned `result_count: 0` with
`recommendation_visibility: BLOCKED_EVIDENCE_COLLECTION` /
`BLOCKED_AI_RANKING` for a normal, broad query (light ADL needs, no memory
care, Las Vegas, $5,000 budget) even though 374 of 377 facilities passed every
MUST gate.

### Root cause (confirmed against real Render logs, not guessed)
`app/services/ai_candidate_ranking_runtime.py`'s batched ranking path
(`_batch_ai_rank`) sends candidates in groups (batch size was 30 in
production at investigation time, later reduced to 12). Each batch gets one
scoring attempt and one contract-repair retry. Two failure modes dominated:

- `AI_CANDIDATE_SCORING_INVALID_CLAIM_CITATION` -- the model cited a
  `claim_id` absent from that candidate's governed evidence ledger.
- `AI_CANDIDATE_SCORING_CLOSED_WORLD_VIOLATION` -- the model returned more
  or fewer candidate IDs than supplied, frequently with heavy duplication
  (e.g. `supplied=30 returned=49 ... duplicates=23`).

Render logs showed **0 of 7** batched 374-candidate ranking runs succeeded in
the preceding 24 hours. Nearly every batch needed its repair retry (12 of 13
in one traced run), and whenever even one batch's repair *also* failed, the
exception propagated out of the whole `ThreadPoolExecutor` loop and discarded
every other batch's valid scores too -- a single bad batch reset the entire
374-candidate ranking to a silent `DETERMINISTIC_FALLBACK`, which
`canonical_decision_state.py` then treats as ranking never having completed,
blocking all visibility with no reason surfaced to the caller.

Reducing `OPTIME_AI_RANKING_BATCH_SIZE` from 30 to 12 alone did **not** fix
this: a controlled baseline (3 fresh requests, same payload, batch_size=12,
pre-fix code) still failed 0/3, confirming the bug was structural
(all-or-nothing failure propagation), not batch-size-driven.

### Fix (`fix/ai-ranking-batch-isolation`, commit `3052090`)
Three changes to `ai_candidate_ranking_runtime.py`, none touching the
required-ranking hard-fail path:

1. A fabricated claim_id citation on `rank_drivers`/`rank_risks` is now
   **stripped**, not fatal -- that field is documented as optional ("may be
   empty" in the prompt contract). The candidate's score/rank are kept and
   the row is marked `citation_validation: PARTIAL` so the gap stays visible
   rather than silently vanishing. A genuine closed-world violation (wrong
   candidate set) is unchanged: still a hard failure -- this is a real
   integrity problem, not an optional-field gap.
2. A batch that still fails after its one repair attempt is now **split in
   half and retried independently**, recursively down to individual
   candidates, instead of taking every other (valid) batch's scores down
   with it.
3. The actual failure reason now survives into the returned status as
   `fallback_reason` instead of only reaching a log line.

Deliberately out of scope: `OPTIME_AI_RANKING_BATCH_SIZE` tuning (infra/env,
not code) and how much partial candidate coverage should be "enough" to show
results to a family (a product/safety threshold, not a bug fix) --
`canonical_decision_state.py` was not touched.

### Verification
- 11/11 unit tests green, including a dedicated regression
  (`test_one_persistently_confused_batch_no_longer_erases_every_other_batchs_valid_scores`)
  that reproduces the exact production failure shape (a batch that returns
  confused/duplicated output when grouped, but scores cleanly once split) and
  asserts the fix recovers full `AI_BATCH_RANKED` coverage instead of falling
  back.
- **Deployed live to production** (commit `3052090`, manual deploy, no merge
  to `main`, `OPTIME_AI_RANKING_BATCH_SIZE=12` unchanged) for direct
  confirmation, not just local tests:
  - Baseline (pre-fix, same commit `e6ee2e9` that was live before, same
    payload, 3 runs): **0/3** -- `DETERMINISTIC_FALLBACK` every time.
  - Post-fix (commit `3052090` live, same payload, 4 runs total across two
    batches): **4/4** -- `AI_BATCH_RANKED` every time.

The ranking failure this investigation started from is resolved and
confirmed working against real production data, not a mock.

## 2. NICE preference verification structurally could not complete -- FIXED, verified live

### Symptom
Even after AI ranking succeeds (`ranking: COMPLETE`, `must: PASS`),
`canonical_decision_state.py` still blocked all output:
`phase: PREFERENCE_VERIFICATION`, `can_show_recommendations: false`,
`result_count: 0`. Three independent requests over ~9 minutes returned
**identical** `nice_complete_candidate_count: 0`,
`verification_required_count: 10`, `candidates_verified: 40` -- no
progress between requests.

### Root cause chain (each layer confirmed against source, not inferred)

1. **`semantic_preference_runtime.py:build_dynamic_preference_model`**
   extracts a "NICE preference" from *any* NICE-tagged statement or
   AI-reported preference in the interview, with no filter for whether it is
   actually a verifiable fact about a facility. For the traced query this
   produced preferences including `"Preserve independence."` and
   `"Least restrictive safe setting."` -- client values, not checkable
   claims. No governed evidence field can ever "support" these, so they can
   never resolve to `MATCH`.
2. Deduplication is exact-string only (`casefold()` equality). Three
   differently-worded statements about the same "would consider a CCRC"
   answer produced three separate preference entries instead of one,
   inflating the requirement count.
3. **`verify_dynamic_preferences`** (same file) only marks a candidate
   `NICE_COMPLETE` if it `MATCH`es *every* preference simultaneously. Since
   at least one preference in this set can never receive a `MATCH` from any
   candidate, `nice_complete_candidate_count` stays 0 forever, for every
   candidate, no matter how many are checked.
4. **`canonical_decision_state.py:181`**
   (`if complete > 0 and verification_required == 0`) requires not just one
   perfect candidate, but that *every candidate checked in this pass* be
   perfect (`verification_required_count == 0` across the whole checked
   set) before preferences are considered resolved enough to show anything
   -- even provisionally.
5. The wave search that checks preferences (`must_ai_nice_pipeline.py:
   _verify_dynamic_preferences_in_waves`) is **bounded and stateless**:
   capped at `OPTIME_NICE_WAVE_SEARCH_MAX_CANDIDATES` (40) candidates per
   request, with no persistence between requests. Retrying does not resume
   past where the last request stopped -- it reruns the same bounded search
   over what is usually the same top-ranked candidates and gets the same
   result.

### Why this matters
This is not a slow-to-resolve or occasionally-stuck state. For any query
whose semantic interview produces at least one preference that is
inherently unverifiable against governed evidence -- which ordinary
natural-language answers produce routinely ("preserve her independence",
"least restrictive setting", "somewhere she'll feel at home") -- the block
cannot resolve by waiting, retrying, or raising the wave-search cap. It is
a structural ceiling, not a queue depth. This likely affects a meaningful
share of real production queries, not just the traced case.

### Fix, part 1 -- classify what's actually verifiable (PR #167)
`semantic_preference_runtime.py` gained a fourth verification status,
`NOT_APPLICABLE`, alongside `MATCH`/`MISMATCH`/`UNKNOWN`: the verifier now
distinguishes "this facility's evidence doesn't resolve it" (`UNKNOWN`,
unchanged) from "no facility's evidence ever could, because this is a client
value/goal/search-scope statement, not a checkable fact" (`NOT_APPLICABLE`).
`NOT_APPLICABLE` assessments are excluded from both the completeness
requirement and `verification_required_count`. 12/12 tests green, including
two reproducing the traced production shape (mixed checkable+unverifiable,
and all-unverifiable).

### Fix, part 2 -- one resolved candidate shouldn't wait on another (PR #168)
`canonical_decision_state.py` also blocked whenever *any* checked candidate
had gaps, even if a *different* candidate's preferences were already fully
resolved -- the same "one unresolved candidate is a research queue, not a
veto" principle already applied to the MUST gate (PR #165) and AI ranking
(PR #166), now applied here too: block only when `nice_complete_candidate_count
== 0` (nothing resolved *anywhere* yet); once at least one candidate is fully
resolved, fall through to `PROVISIONAL_RECOMMENDATION`.

### The logging gap that made 1+2 unverifiable
`semantic_preference_runtime.py` had **zero logger calls** -- confirmed by
grepping the file, not by absence of search results. Unlike
`ai_candidate_ranking_runtime.py` (which logs every batch/repair/failure),
there was no way to tell whether `NOT_APPLICABLE` was actually being returned
by the model, whether verification calls were silently failing (`verify_one`
already swallowed exceptions when not required), or whether checkable
preferences simply never matched. `apply_must_ai_nice_pipeline_ms` showed
**179.8 seconds** of real work in that stage on one production request with
nothing to show for it in the logs. Added: a warning on each per-candidate
verification failure, and one INFO summary per `verify_dynamic_preferences`
call with the full `status_counts` breakdown. Purely additive, no behavior
change.

### What the logs actually showed, and fix part 3 -- preferences never gate visibility (PR #169)
With PR #167 and #168 both deployed and the new logging live, four
consecutive clean production runs of the same query *still* returned
`nice_complete_candidate_count: 0`. The logs finally showed why -- and it
confirmed parts 1+2 were both working correctly, while surfacing a third,
different problem:

```
status_counts={'UNKNOWN': 33, 'NOT_APPLICABLE': 26, 'MISMATCH': 7, 'MATCH': 4}
status_counts={'UNKNOWN': 33, 'NOT_APPLICABLE': 29, 'MISMATCH': 8}
status_counts={'UNKNOWN': 36, 'MISMATCH': 3, 'NOT_APPLICABLE': 30, 'MATCH': 1}
status_counts={'UNKNOWN': 35, 'NOT_APPLICABLE': 33, 'MISMATCH': 2}
```

`NOT_APPLICABLE` was firing on ~40% of all assessments, exactly as designed.
But of the remaining *checkable* preferences, roughly half came back
`UNKNOWN` and a handful `MISMATCH` -- real `MATCH` count across all 4 waves,
40 candidates, ~280 assessments: **5**. `NICE_COMPLETE` requires every
checkable preference to `MATCH`, so under real evidence coverage essentially
no candidate can ever be fully clean, independent of parts 1 and 2 -- a
candidate needing zero UNKNOWN across ~4 checkable preferences when roughly
half of all checks return UNKNOWN is a near-impossible bar, not a rare one.

This was the point the investigation turned into a product decision rather
than a bug hunt: **NICE preferences are a ranking/labeling signal, not a
visibility gate.** More confirmed matches can raise a candidate's standing,
but their absence must never block a validated, fully MUST-passed and
AI-ranked shortlist from being shown at all. PR #169 removed the
`PREFERENCE_VERIFICATION`-blocks branch from `derive_canonical_decision_state`
entirely (parts 1+2's mechanisms remain in the code and are still correct --
they just stopped being the thing that closes the loop by themselves). Once
`eligible > 0` and ranking is complete, the pipeline now always proceeds to
`PROVISIONAL_RECOMMENDATION` (or `FINAL_RECOMMENDATION` once preferences
genuinely are complete). `DecisionPhase.PREFERENCE_VERIFICATION` is kept in
the enum but is unreachable from this function.

### Final live verification
Same traced query, same payload, deployed commit `977dda1` (PR #169's
branch tip, later merged as `e5f18fb`):

```
canonical phase: PROVISIONAL_RECOMMENDATION | can_show: True | finality: PROVISIONAL
recommendation_execution_allowed: True
result_count: 10

#1 The Grand at Southern Hills            | Las Vegas | score=82.0
#2 JCR HOME CARE INC                       | Las Vegas | score=79.0
#3 MorningStar Senior Living at The Canyons | Las Vegas | score=79.0
#4 Vista Pointe at Mira Loma               | Henderson | score=77.0
#5 Serenity Living at Mountains Edge       | Las Vegas | score=76.0
```

The exact query that returned zero results on every single run of this
investigation -- baseline, post-#166, post-#167, post-#168, three separate
deploys -- returned a real, ranked, scored shortlist once #169 was live.

## Timeline / PR reference
- **PR #166** (`fix/ai-ranking-batch-isolation`, commit `3052090`, merged):
  section 1's fix. Baseline 0/7 (24h prod) and 0/3 (controlled) -> 4/4 live
  after fix.
- **PR #165** (`fix/canonical-shortlist-gate-lineage`, merged): same-day fix
  for the analogous MUST-gate problem ("pending evidence on unrelated
  candidates should not hide a completed, validated shortlist"). Section 2's
  bug was the same category of problem one layer up, in preference
  verification instead of MUST evaluation.
- **PR #167** (`fix/nice-preference-verifiability-classification`, closed,
  superseded by #169): `NOT_APPLICABLE` classification.
- **PR #168** (`fix/preference-partial-completeness-gate`, closed, superseded
  by #169): one-resolved-candidate-shouldn't-wait-on-another.
- **PR #169** (`integration/preference-verification-combined`, merged
  `e5f18fb`): contains #167 and #168's commits, adds the missing logging,
  and adds the fix that actually closes the loop (preferences never gate
  visibility). This is the PR to look at for the final, complete diff.
- Benchmark payload and raw responses used for verification are not
  committed to the repo (contain a synthetic but detailed client scenario);
  available in the investigating session's scratch output if needed to
  reproduce.
