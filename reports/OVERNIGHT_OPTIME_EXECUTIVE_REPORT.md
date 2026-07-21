# Overnight OPTIME Executive Report

- RUN_ID: OVERNIGHT_20260720T221742Z
- Generated: 2026-07-21T03:33:02.729935+00:00
- Start: 2026-07-20T22:17:42.175669+00:00

## Executive Summary

- Canonical facilities (latest source run cohort): 54
- Agents expected: 11
- Agents actually executed: 11
- Sources attempted: 218
- Sources successful: 205
- Sources failed: 13
- New verified facts: 0
- Changed facts: 0
- Unknowns claimed resolved: 59
- Unknowns evidence-backed resolved: 0
- False/unsupported resolutions: 59

## Phase Status

- Completed: ['Phase 1 baseline truth', 'Phase 7 evidence parity regression (existing PASS artifact)', 'Phase 8 controlled benchmark (existing VALID artifact)', 'Phase 9 Sands causality trace (existing controlled trace)', 'Task 1 permanent Python runtime fix', 'Phase 2 agent authority audit', 'Phase 4 decision-critical coverage matrix', 'Phase 6 source connectivity diagnostics', 'Phase 11 daily automation reality check', 'Phase 13 control tower truth', 'Phase 16 validation', 'Phase 3 canonical 54-facility identity verification']
- Partial: []
- Not Started: ['Phase 5 bounded external discovery refresh', 'Phase 15 safe fix cycle beyond Python runtime determinism']

## Previously Partial Verification

- Phase 2 agent authority audit: EVIDENCE_VERIFIED
  Evidence: agents_expected=11, agents_executed=11, agents_success=11
- Phase 3 canonical 54-facility identity verification: EVIDENCE_VERIFIED
  Evidence: canonical_source_run=20260720T214443Z, db_distinct_facilities=54, coverage_facility_count=54
- Phase 4 decision-critical coverage matrix: EVIDENCE_VERIFIED
  Evidence: fields=23, aggregate_keys=23, facility_count=54
- Phase 6 source connectivity diagnostics: EVIDENCE_VERIFIED
  Evidence: targeted_run_id=20260720T222246Z, targeted_requests=40, targeted_successes=35, targeted_failures=5
- Phase 11 daily automation reality check: EVIDENCE_VERIFIED
  Evidence: scheduler and background refresh calls are wired in backend startup and executive report is generated
- Phase 13 control tower truth: EVIDENCE_VERIFIED
  Evidence: control_tower rows assembled from DB in executive_report_service and reported in authority report
- Phase 16 validation: EVIDENCE_VERIFIED
  Evidence: controlled_validity=VALID APPLES-TO-APPLES, targeted_requests=40

## Targeted Research Provenance

- Run ID: 20260720T222246Z
- Requests: 40
- Successes: 35
- Failures: 5

## Owner Decisions Required

- None identified in this closure pass.
