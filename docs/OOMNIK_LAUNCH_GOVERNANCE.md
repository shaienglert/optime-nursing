# Oomnik Launch Governance

## Launch freeze

During canonical journeys 1–10, Nursing has one active writing stream. Other sessions may inspect and report, but must not change decision, evidence, ranking, explanation, report, or journey files.

Every change uses a fresh branch from current `main`. Shared stashes and reused worktrees are prohibited. Before merge, update from `main` and rerun the launch gate on the resulting head commit.

## Scenario fixtures, not a frozen provider truth

Only the ten client inputs and their invariants are versioned fixtures. A frozen facility snapshot may be used for deterministic unit tests, but it is never accepted as evidence that current production data is correct.

All ten scenarios also run weekly against the live production application and its current database. They may also be dispatched together with `scenario=all`. A fixture pass and a live pass are separate required signals.

## Decision-authority migration

The target architecture is one canonical decision object. Today, readiness is still represented by `human_intelligence.decision_readiness`, `recommendation_execution_allowed`, `canonical_decision_state`, and `facility_selection_pipeline.ai_ranking`. The launch contract cross-checks these existing sources and blocks contradictory output. It does not pretend that the architectural migration is complete.

Consolidating these fields is a separate, staged architectural change. It requires an inventory of every reader/writer, compatibility fields during migration, and explicit owner approval before removing an authority.

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
