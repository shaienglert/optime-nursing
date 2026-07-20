# Overnight Data Quality Backlog

- Generated: 2026-07-20T22:17:42.522606+00:00
- RUN_ID: OVERNIGHT_20260720T221742Z

## P0

- COMPONENT: Facility evidence coverage
  ISSUE: Decision-critical fields remain largely UNKNOWN/SOURCE_ACCESS_FAILED across canonical cohort.
  IMPACT: Could reduce recommendation confidence and explainability.
  CLASSIFICATION: DATA QUALITY ISSUE
  SAFE AUTO-FIX?: YES
  OWNER APPROVAL REQUIRED?: NO
  RECOMMENDED NEXT ACTION: Run targeted bounded discovery against highest-value unknown fields.

## P1

- COMPONENT: Source connectivity telemetry
  ISSUE: Mixed source failures (geo/rate/access) require per-source remediation playbooks.
  IMPACT: Material confidence loss in evidence parity.
  CLASSIFICATION: IMPLEMENTATION BUG / OPERATIONS GAP
  SAFE AUTO-FIX?: YES
  OWNER APPROVAL REQUIRED?: NO
  RECOMMENDED NEXT ACTION: Add automated connector-health drilldowns and parser-failure tracing.

## P2

- COMPONENT: Agent execution observability
  ISSUE: Some metrics show definition/snapshot presence without recommendation usage logs.
  IMPACT: Weakens control-tower execution truth confidence.
  CLASSIFICATION: IMPLEMENTATION COMPLETION
  SAFE AUTO-FIX?: YES
  OWNER APPROVAL REQUIRED?: NO
  RECOMMENDED NEXT ACTION: Wire recommendation usage logging on each ranked run.

## P3

- COMPONENT: Reporting UX
  ISSUE: Daily report readability can improve with source failure trend charts.
  IMPACT: Operational clarity.
  CLASSIFICATION: ENRICHMENT
  SAFE AUTO-FIX?: YES
  OWNER APPROVAL REQUIRED?: NO
  RECOMMENDED NEXT ACTION: Add trend deltas and daily sparkline summaries.
