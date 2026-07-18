# 32 Outcome Framework

## Purpose
Document the implemented infrastructure for tracking recommendation outcomes and using measured outcomes to improve future recommendation quality.

## Current Implementation
- Outcome event tracking exists with persisted logs in data/outcome_event_log.json.
- Outcome validation script exists at scripts/run_real_world_outcome_validation.cjs.
- Outcome validation reports exist at reports/real_world_outcome_validation.md and reports/recommendation_accuracy_dashboard.md.
- Resident outcome persistence model exists in backend/app/models/facility.py as ResidentOutcome.
- Outcome-oriented agent surfaces exist in reports/knowledge_gap_report.md and reports/agent_productivity_dashboard.md.

## Architecture
- Event collection layer: tracked lifecycle events from recommendation view through move-in and feedback.
- Persistence layer: structured outcome event log and backend resident outcome model.
- Validation layer: deterministic report generation and benchmark checks.
- Improvement loop: miss analysis and calibration suggestions feed recommendation and decision-intelligence refinement.

## Dependencies
- scripts/outcome_event_tracker.cjs
- scripts/run_real_world_outcome_validation.cjs
- data/outcome_event_log.json
- reports/real_world_outcome_validation.md
- reports/recommendation_accuracy_dashboard.md
- backend/app/models/facility.py
- backend/app/main.py

## Current Status
- Implemented with active validation reporting.
- Latest observed report status: PASS in reports/real_world_outcome_validation.md.

## Completed Work
- Event tracking coverage includes recommendation_viewed, facility_opened, save_to_shortlist, tour_requested, tour_completed, move_in_completed, and user_feedback_score.
- Core KPI reporting includes acceptance, conversion, top-3 selection/visit/move-in, satisfaction, and advisor agreement.
- Benchmark gate checks are implemented with PASS/FAIL status output.
- Miss analysis pipeline provides ranking reason, missed signals, weight imbalance, and calibration suggestion rows.

## Remaining Work
- Expand direct integration from outcome miss analysis into automated recommendation calibration workflows.
- Add clearer lineage from specific outcome deltas to specific ranking-rule or feature updates.
- Increase production-sourced outcome volume to reduce dependence on bootstrap pathways in low-volume environments.

## Known Limitations
- Current reports indicate bootstrap support may be used when live production events are sparse.
- Outcome framework artifacts are distributed across multiple reports rather than a single consolidated operations dashboard.

## Next Implementation Steps
- Add a unified outcome operations dashboard that tracks daily deltas in conversion and satisfaction metrics.
- Track closed-loop changes where a calibration action is explicitly linked to measurable post-change improvement.
- Add per-persona outcome trend reporting so recommendation improvements can be audited by persona type.
