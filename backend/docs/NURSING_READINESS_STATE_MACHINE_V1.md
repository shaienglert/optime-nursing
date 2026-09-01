# OPTIME Nursing Readiness / Decision State Migration

Status: Phase 2 shadow validation complete; Phase 3 is blocked only on resolving the
recorded production divergences below. No production control flow is changed by this
document or by `canonical_decision_state.py`.

Phase 1 (`canonical_decision_state.py` + tests) is merged and stays shadow-only/add-only --
it has zero writers into any production control field and is not called from `app/main.py`
or any request path. It is frozen here, alongside this completed design document, so a
future session can continue directly into Phase 2 without re-deriving this design. Do not
start Phase 3 (single writer) before Phase 2's shadow comparison (see "Phase 2 status"
below) has run against more than the initial six happy-path fixtures and every divergence
has been resolved explicitly.

### Phase 2 status

`derive_canonical_decision_state(result)` consumes a full pipeline `result` payload
(`results`, `must_eligible_count`, `decision_intelligence.facility_selection_pipeline`,
etc.) -- the shape `run_patient_decision_engine` returns for one complete request.
`gold_examples/nursing_gold_v1.jsonl`'s 13 cases are at a narrower grain: single
facility/engine checks (`client_intent_runtime`, `semantic_facility_requirements`,
`combined_care_solution_runtime`) validated by `validate_against_engine.py`, not full
pipeline runs -- so Phase 2 cannot compare canonical state against that file directly.

`gold_examples/validate_canonical_state_shadow.py` (added the same session, after this
note was first written) takes a third path, deliberately kept separate from
`validate_against_engine.py`: six hand-built pipeline-grain fixtures (not JSONL, not the
existing gold set), each asserting an `expected phase` + `next_action`. Run it with:

```
cd backend && python gold_examples/validate_canonical_state_shadow.py
```

PR #159 extends this harness to system-failure, no-eligible, fail-closed,
deterministic-fallback, and ambiguous-payload paths. On 2026-09-01 it was also compared
locally (read-only) against two real production responses from
`/decision-engine/recommendations`:

1. An independent-living request had `READY`, execution allowed, and
   `PROVISIONAL_RANKING_VISIBLE`, while its ranking status was
   `DETERMINISTIC_FALLBACK`. Canonical state correctly returned `AI_RANKING` /
   `RUN_AI_RANKING`. Showing recommendations before a validated AI rank is a legacy
   visibility divergence, now explicitly emitted as
   `LEGACY_VISIBILITY_SHOWS_PREMATURE_RECOMMENDATION`.
2. A client-interview request had three `client_owned_blockers` and no adaptive question,
   yet legacy state allowed execution and showed provisional recommendations. Canonical
   state correctly returned `CLIENT_INPUT_REQUIRED` / `ASK_CLIENT`, surfacing
   `LEGACY_READINESS_ADVANCES_WITH_CLIENT_BLOCKERS` and
   `LEGACY_EXECUTION_ALLOWS_PREMATURE_RECOMMENDATION`.

These are confirmed legacy writer defects, not reasons to weaken canonical inference.
Phase 3 must remove those writers' authority and derive global execution, visibility,
and finality from Canonical Decision State. The adaptive-question generator remains the
owner of question content, while Canonical Decision State determines only whether a
client question is required.

## Problem

The current runtime does not have one authoritative decision state. Multiple fields encode overlapping control decisions and are written by different layers:

- `decision_readiness`
- `adaptive_questions`
- `recommendation_execution_allowed`
- `recommendation_visibility`
- `decision_finality`
- per-facility `client_intent_fit.hard_gate`

This allows state drift: one layer can consider the client interview complete while another blocks recommendation visibility, or a provider-research failure can be represented with the same readiness value used for a legitimate provider-owned unknown.

## Current writer / reader map

### `decision_readiness`

Primary writer:
- `human_intelligence_runtime_verified.py`: initializes `NEEDS_CLARIFICATION`, accepts Semantic AI readiness, applies Guardian veto, and can convert invalid/failed paths to `NEEDS_RESEARCH`.

Readers / secondary control:
- `backend/app/services/__init__.py`: decides whether the interview blocks the downstream recommendation pipeline.
- `frontend/src/app/adaptive-interview/page.tsx`: routes client flow based on readiness.
- `patient_decision_engine_runtime/__init__.py`: carries readiness into decision intelligence/audit output.
- tests and Gold lifecycle harnesses.

Risk: `NEEDS_RESEARCH` currently mixes provider-owned research with some AI failure/fallback conditions.

### `recommendation_execution_allowed`

Writers / mutators:
- `backend/app/services/__init__.py`
- `semantic_facility_requirements.py`
- `must_ai_nice_pipeline.py`

Risk: evidence/research layers can alter global recommendation control state instead of reporting facts to one state machine.

### `recommendation_visibility`

Writers:
- `backend/app/services/__init__.py`
- `must_ai_nice_pipeline.py`

Risk: visibility becomes an independent control plane rather than a derived property of decision state.

### `decision_finality`

Writers / mutators found in:
- `backend/app/services/__init__.py`
- `decision_agent_bridge.py`
- `decision_agent_bridge_fast.py`
- `semantic_facility_requirements.py`
- `must_ai_nice_pipeline.py`
- `patient_decision_engine_runtime/__init__.py`

Risk: research, ranking and orchestration layers can independently label the same decision provisional/final/blocked.

### `client_intent_fit.hard_gate`

This remains facility-level state and should not be collapsed into the global state machine. It is an input to global transitions:
- PASS -> candidate can enter AI ranking.
- FAIL -> candidate is excluded.
- PENDING_VERIFICATION -> provider evidence collection remains required.

## Proposed authoritative phase machine

1. `CLIENT_INPUT_REQUIRED`
2. `EVIDENCE_COLLECTION`
3. `MUST_EVALUATION`
4. `AI_RANKING`
5. `PREFERENCE_VERIFICATION`
6. `PROVISIONAL_RECOMMENDATION`
7. `FINAL_RECOMMENDATION`
8. `SYSTEM_BLOCKED`

`SYSTEM_BLOCKED` is reserved for system failures and invariant violations. It must never be represented as provider research.

## Orthogonal state dimensions

The canonical state also stores dimensions that should not be overloaded into one phase name:

- client: `INCOMPLETE | COMPLETE`
- evidence: `MATERIAL_GAPS | SUFFICIENT`
- must: `NOT_EVALUATED | PENDING | PASS | NO_ELIGIBLE_CANDIDATES`
- ranking: `NOT_STARTED | RUNNING | COMPLETE | FAILED`
- preferences: `NOT_STARTED | PARTIAL | COMPLETE`
- finality: `NONE | PROVISIONAL | FINAL`
- system: `HEALTHY | DEGRADED | BLOCKED`

## Guardian (precise definition)

Guardian is **not a new component and not an additional AI model**. It is a policy layer:
the set of deterministic validators that already exist across the codebase, unified
behind one call surface, not rewritten from scratch. Each existing validator keeps its
current authority; Guardian's job in the migration is only to aggregate their verdicts
into the canonical state's orthogonal dimensions, and to be the single place a new
validator gets registered rather than a fifth ad hoc control field.

- **Client-completeness validator** = `human_intelligence_runtime_verified.py`'s existing
  `readiness_guardian` (`client_owned_blockers`, veto mechanism, already implemented and
  already what `canonical_decision_state.py`'s `_material_client_blockers` reads). Owns:
  whether a client-owned fact is still missing. This already *is* Guardian's
  `CLIENT_INPUT_REQUIRED` check -- Phase 1 just consumes its output, no new code needed here.
- **MUST validator** = `client_intent_runtime.evaluate_candidate_intent`. Owns PASS / FAIL /
  UNKNOWN per MUST per facility, including the rule that UNKNOWN is never a hard fail on
  unverified agent evidence (see governed_evidence_runtime.py and the semantic/combined-care
  fixes from the same migration effort). In the target architecture this becomes **one
  validator registered inside Guardian**, not Guardian itself: it has authority only over
  facility-level MUST verdicts, which Guardian aggregates into the canonical `must` state
  dimension (`NOT_EVALUATED | PENDING | PASS | NO_ELIGIBLE_CANDIDATES`). It never gets
  authority over global `phase`.
- Semantic AI proposes client understanding and the next question; it does not decide
  `client` state itself -- the client-completeness validator (readiness_guardian) does,
  and can veto Semantic AI's proposal (already implemented: `veto_applied`,
  `veto_resolution` in the current runtime).

## Ownership rules

- Semantic AI proposes client understanding and next question.
- Guardian (the validator set above) determines `client`, `must`, and material-blocker state.
- Research workers write evidence only, and choose *what to research next* using
  `research_priority` (`decision_agent_bridge.py`) -- see "Value-of-information inside
  EVIDENCE_COLLECTION" below. They never write `phase`, `finality`, or any other global
  control field; `semantic_facility_requirements.py` currently violates this (see Adjacent
  architecture issue) and must stop doing so in the same migration.
- MUST Guardian (the MUST validator above) writes facility MUST verdicts only.
- AI ranker writes ranking only.
- Preference verifier writes preference assessments only.
- Process Owner proposes the next decision action.
- Canonical Decision State Machine is the only component that may write global phase.

## Value-of-information inside EVIDENCE_COLLECTION

`research_priority(dimension, candidate_rank_index)` (`decision_agent_bridge.py`, shipped
the same night as this design) is not a separate state or a new capability the state
machine needs to model -- it is the **existing mechanism EVIDENCE_COLLECTION already
delegates to** for choosing which of several material gaps to resolve first. The state
machine only needs to know "we are in EVIDENCE_COLLECTION, N candidates have pending MUST
evidence"; `research_priority`'s dimension-stakes-then-pool-position ordering decides the
work order of the research queue underneath that one phase. No new field, no new owner --
just an explicit note so a future implementer does not duplicate it as e.g. an
`evidence_priority` dimension on `CanonicalDecisionState`.

## Transition invariants

### `CLIENT_INPUT_REQUIRED -> EVIDENCE_COLLECTION`
Allowed only when no material client-owned blocker remains.

### `EVIDENCE_COLLECTION -> MUST_EVALUATION`
Allowed when provider-owned evidence needed for current MUST evaluation is sufficient to evaluate the relevant candidate set.

### `MUST_EVALUATION -> AI_RANKING`
Allowed only for the exact closed world of all and only MUST-PASS candidates.

### `AI_RANKING -> PREFERENCE_VERIFICATION`
Allowed only after validated closed-world AI ranking. Required AI failure goes to `SYSTEM_BLOCKED`, never deterministic user-visible fallback.

### `PREFERENCE_VERIFICATION -> PROVISIONAL_RECOMMENDATION` vs `-> FINAL_RECOMMENDATION`

The distinction is not "any unknown remains" -- it is **which kind of unknown**:

- A **MUST unknown** is material to a specific facility's *eligibility*. While it remains
  unresolved for a candidate, that candidate cannot be in the MUST-PASS closed world at
  all (`must` stays `PENDING`, the candidate stays in `EVIDENCE_COLLECTION`, never reaches
  ranking). A MUST unknown never produces `PROVISIONAL_RECOMMENDATION` for that candidate --
  it simply is not eligible to be recommended yet, provisionally or otherwise.
- A **NICE/preference unknown** for a candidate that has *already* passed every MUST does
  not revoke that candidate's eligibility. It can still change *ordering* (a candidate
  ranked 6th might complete every NICE preference while 1st-5th remain partial) or NICE
  completeness reporting, but the already-PASS candidate remains legitimately displayable.
  This is what makes `PROVISIONAL_RECOMMENDATION` correct: the displayed set is not
  provisionally *eligible*, only provisionally *final-ranked*.

So: `-> PROVISIONAL_RECOMMENDATION` is allowed once ranking is complete for the full
MUST-PASS closed world and at least one displayed candidate exists, even if
`preferences` is `PARTIAL`. `-> FINAL_RECOMMENDATION` requires `preferences` to reach
`COMPLETE` (no material NICE/provider unknown remains that could still change the
displayed set or its ordering) with all other recommendation invariants passing. Neither
transition ever depends on a MUST unknown -- by the time either is reachable, `must` is
already `PASS` for the full eligible set.

### Any phase -> `SYSTEM_BLOCKED`
For required AI outage, malformed required AI output, database/evidence corruption, or Guardian invariant violation.

## Derived UI/control properties

Legacy fields should become derived, read-only compatibility fields during migration.

Example:

```python
can_show_recommendations = phase in {
    PROVISIONAL_RECOMMENDATION,
    FINAL_RECOMMENDATION,
}
```

The frontend should eventually consume a canonical `next_action` such as:

- `ASK_CLIENT`
- `RESEARCH_PROVIDER_EVIDENCE`
- `RUN_AI_RANKING`
- `VERIFY_MATERIAL_PREFERENCES`
- `SHOW_PROVISIONAL_RECOMMENDATION`
- `SHOW_FINAL_RECOMMENDATION`
- `RECOVER_SYSTEM`

and stop interpreting `READY || NEEDS_RESEARCH` itself.

## Migration plan

### Phase 1 — shadow only (DONE, frozen on `refactor/nursing-canonical-decision-state`)
- Add `CanonicalDecisionState` and legacy adapter. -- done: `canonical_decision_state.py`.
- Do not change any existing control field. -- confirmed: not referenced from `app/main.py` or any request path.
- Attach state only in tests/diagnostics until shadow behavior is validated. -- `attach_canonical_decision_state_shadow` exists and is exercised only by `tests/test_canonical_decision_state.py` (6 tests, passing).
- Record conflicts between canonical state and legacy fields. -- done: `legacy_state_conflicts`.
- Not yet merged to `main`. Merge only after Phase 2 (below) has run and every divergence is resolved explicitly.

### Phase 2 — shadow evaluation (in progress)
- Add expected phase/next-action assertions to representative lifecycle fixtures. -- started: `gold_examples/validate_canonical_state_shadow.py`, 6/6 happy-path fixtures passing (see "Phase 2 status" above for what's left).
- Compare canonical state with current production decisions. -- not yet done against real recorded payloads, only synthetic fixtures so far.
- Resolve every divergence explicitly; do not silently force parity when legacy behavior is wrong. -- 2 conflicts already surfaced and not yet triaged.

### Phase 3 — one writer
- Introduce an orchestrator-owned transition function.
- Research/ranking/verification layers stop writing global control fields.
- Legacy fields are derived from canonical state for compatibility.

### Phase 4 — frontend migration
- Frontend consumes `phase`, `next_action`, and `can_show_recommendations`.
- Remove direct branching on `READY`, `NEEDS_RESEARCH`, `recommendation_execution_allowed`, and `recommendation_visibility`.

### Phase 5 — remove legacy readiness control
- `decision_readiness` remains only as historical/audit data or is removed after all callers migrate.
- CI forbids new writes to legacy global state fields outside the compatibility adapter.

## Adjacent architecture issue

`semantic_facility_requirements.py` currently reparses Semantic AI output using token families (for example dietary, walking/layout and social tokens) to select downstream dimensions. That should be removed in the same broader migration: Semantic AI should emit canonical `parameter_id` / `capability_id` / `required_service_level`, and downstream layers should consume those IDs instead of interpreting raw text again.
