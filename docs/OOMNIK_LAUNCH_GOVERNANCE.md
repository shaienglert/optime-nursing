# Oomnik Launch Governance

## Launch freeze

During canonical journeys 1–10, Nursing has one active writing stream. Other sessions may inspect and report, but must not change decision, evidence, ranking, explanation, report, or journey files.

Every change uses a fresh branch from current `main`. Shared stashes and reused worktrees are prohibited. Before merge, update from `main` and rerun the launch gate on the resulting head commit.

## Scenario fixtures, not a frozen provider truth

Only the ten client inputs and their invariants are versioned fixtures. A frozen facility snapshot may be used for deterministic unit tests, but it is never accepted as evidence that current production data is correct.

All ten scenarios also run weekly against the live production application and its current database. They may also be dispatched together with `scenario=all`. A fixture pass and a live pass are separate required signals.

## Decision-authority migration

`canonical_decision_state` is the only recommendation-control authority. It owns client completeness, lifecycle phase, MUST state, ranking state, finality, system health, next action, and whether recommendations may be shown.

The other fields have narrower roles:

- `human_intelligence.decision_readiness` is a raw interview-stage signal consumed by the authority;
- `facility_selection_pipeline.ai_ranking` is a raw ranking-stage outcome consumed by the authority;
- `recommendation_execution_allowed`, `recommendation_visibility`, and `decision_finality` are read-only compatibility mirrors emitted by the authority.

Production control readers must use the canonical accessors and fail closed when the authoritative object is absent. They must never fall back to a compatibility mirror. The launch contract verifies that any emitted mirrors still agree with the canonical state, but disagreement cannot change control flow.

The launch contract fails when:

- a required client MUST is absent;
- an unrelated MUST is introduced;
- a verified card has a failed or unknown MUST;
- customer copy describes the same capability as both verified and unverified;
- a material practical gap such as availability, pricing, or payer compatibility is hidden;
- a meaningful client statement is dropped.

## Merge and production gates

`Oomnik Launch Integration Gate` validates the proposed code on pull requests. `Oomnik Production Synthetic Journey` runs only after merge/deploy or by explicit dispatch; it must never claim to validate un-deployed PR code.

Production journeys run serially. A journey is approved only when the browser, API decision object, evidence state, and rendered explanation agree. Ten journeys must pass twice consecutively with no intervening code or data change before launch approval.
