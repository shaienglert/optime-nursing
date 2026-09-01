# AI ranking failure and NICE preference blocking -- 2026-09-01

Investigation triggered by: production returning zero recommendations for broad,
common search profiles even after MUST evaluation and AI ranking both succeed.
Two independent, unrelated root causes were found and are documented separately
below. The first is fixed and verified live in production. The second is found
and diagnosed, not yet fixed -- it needs a product decision, not just a code change.

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

## 2. NICE preference verification structurally cannot complete -- FOUND, NOT FIXED

### Symptom
Even after AI ranking succeeds (`ranking: COMPLETE`, `must: PASS`),
`canonical_decision_state.py` still blocks all output:
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

### Not fixed here -- needs a product decision, not a code patch
Candidates for a real fix, none applied:
- Should `build_dynamic_preference_model` filter or flag preferences that
  are not verifiable claims about a facility (values/goals vs. facts),
  rather than treating all NICE statements uniformly?
- Should preference completeness require *every* checked candidate to be
  perfect, or should it follow the same "any eligible candidate with a
  complete, validated ranking can be shown provisionally" principle already
  used for the MUST/ranking gates (see `fix/canonical-shortlist-gate-lineage`,
  PR #165, same day)?
- Should preference verification support resuming/accumulating across
  requests, instead of a stateless per-request bounded search?

## Cross-references
- `fix/ai-ranking-batch-isolation` (commit `3052090`): the AI ranking fix
  documented in section 1.
- `fix/canonical-shortlist-gate-lineage` (PR #165): the same-day fix for the
  analogous MUST-gate problem ("pending evidence on unrelated candidates
  should not hide a completed, validated shortlist"). Section 2 above is
  structurally the same category of bug in the preference-verification
  layer instead of the MUST layer, not yet addressed there.
- Benchmark payload and raw responses used for verification are not
  committed to the repo (contain a synthetic but detailed client scenario);
  available in the investigating session's scratch output if needed to
  reproduce.
