# OPTIME Nursing Readiness / Decision State Migration

Status: design + shadow implementation. No production control flow is changed by this document or by `canonical_decision_state.py` in phase 1.

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

## Ownership rules

- Semantic AI proposes client understanding and next question.
- Guardian validates whether client-owned material blockers remain.
- Research workers write evidence only.
- MUST Guardian writes facility MUST verdicts only.
- AI ranker writes ranking only.
- Preference verifier writes preference assessments only.
- Process Owner proposes the next decision action.
- Canonical Decision State Machine is the only component that may write global phase.

## Transition invariants

### `CLIENT_INPUT_REQUIRED -> EVIDENCE_COLLECTION`
Allowed only when no material client-owned blocker remains.

### `EVIDENCE_COLLECTION -> MUST_EVALUATION`
Allowed when provider-owned evidence needed for current MUST evaluation is sufficient to evaluate the relevant candidate set.

### `MUST_EVALUATION -> AI_RANKING`
Allowed only for the exact closed world of all and only MUST-PASS candidates.

### `AI_RANKING -> PREFERENCE_VERIFICATION`
Allowed only after validated closed-world AI ranking. Required AI failure goes to `SYSTEM_BLOCKED`, never deterministic user-visible fallback.

### `PREFERENCE_VERIFICATION -> PROVISIONAL_RECOMMENDATION`
Allowed when the recommendation is useful but material provider-owned preference unknowns can still change ordering or NICE completeness.

### `PREFERENCE_VERIFICATION -> FINAL_RECOMMENDATION`
Allowed when no decision-material unknown remains and all recommendation invariants pass.

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

### Phase 1 — shadow only
- Add `CanonicalDecisionState` and legacy adapter.
- Do not change any existing control field.
- Attach state only in tests/diagnostics until shadow behavior is validated.
- Record conflicts between canonical state and legacy fields.

### Phase 2 — Gold shadow evaluation
- Add expected phase/next-action assertions to representative Gold cases.
- Compare canonical state with current production decisions.
- Resolve every divergence explicitly; do not silently force parity when legacy behavior is wrong.

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
