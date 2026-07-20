# Source Connectivity Health

- Generated: 2026-07-20T22:17:42.514291+00:00
- RUN_ID: OVERNIGHT_20260720T221742Z
- Source attempt run_id: 20260720T214443Z

## Normalized Status Counts

- GEO_BLOCKED_OR_SUSPECTED: 6
- OTHER: 4
- RATE_LIMITED: 3
- SUCCESS: 205

## Raw Request Status Counts

- RAN_CONNECTED_NO_NEW_VALUE: 205
- SOURCE_ACCESS_FAILED: 4
- SOURCE_GEO_BLOCKED_OR_SUSPECTED: 6
- SOURCE_RATE_LIMITED: 3

## Sources Working

- CMS Inspection Dataset
- CMS Provider Dataset
- CMS Quality Dataset
- Official website
- Seniorly profile

## Sources Blocked/Failing

- Official website

## Recommended Technical Follow-up

- Add source-level parser health metrics for repeated SOURCE_ACCESS_FAILED endpoints.
- Add bounded retry with backoff for SOURCE_RATE_LIMITED sources.
- Preserve GEO_BLOCKED_OR_SUSPECTED separately from NO_DATA_FOUND in all reports.
