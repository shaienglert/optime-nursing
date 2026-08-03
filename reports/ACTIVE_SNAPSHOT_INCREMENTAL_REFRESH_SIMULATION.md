# Active Snapshot Incremental Refresh Simulation

## Contract

- Recommendation input: currently active, precomputed OPTIME facility snapshot only.
- Internet crawling during recommendation: **NO**.
- Facility profile rebuild during recommendation/simulation: **NO**.
- Initial active snapshot: `0c81e52c7136390c`.
- Updated active snapshot: `b576a827bd197aed`.
- One-time local snapshot hydration: **536.672 ms** (outside family response timing).

## Before Source Update

| Facility | Facility snapshot | Last refresh | Changed | Reused | Stale | Missing | Eligibility | Score | Response ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NPI-1073336319 | 20224fb2914db6bc | 2026-07-21T15:01:12+00:00 | None | 3 | None | nursing_24_7, speech_therapy | POTENTIALLY_ELIGIBLE | 55.00 | 0.161 |
| NPI-1083043830 | c98851c3c032a9c2 | 2026-07-21T15:01:12+00:00 | None | 3 | None | speech_therapy | POTENTIALLY_ELIGIBLE | 55.00 | 0.161 |
| CMS-105460 | 94d57b98b0c297ad | 2026-07-21T15:01:12+00:00 | None | 3 | None | pt, speech_therapy | INSUFFICIENT_EVIDENCE | 80.00 | 0.161 |

## Simulated Source Update

- Facility: `CMS-105460`
- Changed parameter: `pt` from UNKNOWN to YES.
- Incremental activation time: **0.175 ms**.
- Unchanged facilities reused: NPI-1073336319, NPI-1083043830.

## After Source Update

| Facility | Facility snapshot | Last refresh | Changed | Reused | Stale | Missing | Eligibility | Score | Response ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMS-105460 | 47439dcb537e57ce | 2026-08-02T15:48:07.098681+00:00 | pt | 2 | None | speech_therapy | ELIGIBLE | 89.38 | 0.073 |
| NPI-1073336319 | 20224fb2914db6bc | 2026-07-21T15:01:12+00:00 | None | 3 | None | nursing_24_7, speech_therapy | POTENTIALLY_ELIGIBLE | 55.00 | 0.073 |
| NPI-1083043830 | c98851c3c032a9c2 | 2026-07-21T15:01:12+00:00 | None | 3 | None | speech_therapy | POTENTIALLY_ELIGIBLE | 55.00 | 0.073 |

## Proof

- PASS: `recommendation_used_active_snapshot_only`
- PASS: `no_internet_crawl_during_recommendation`
- PASS: `no_facility_profile_rebuild`
- PASS: `only_affected_facility_refreshed`
- PASS: `only_affected_parameter_refreshed`
- PASS: `active_snapshot_version_updated`
- PASS: `recommendation_recalculated`
- PASS: `unchanged_facility_objects_reused`
- PASS: `family_response_fast_before`
- PASS: `family_response_fast_after`

The numeric match score is recalculated under existing engine semantics. UNKNOWN is neutral; therefore the proof requires a changed recommendation result and improved eligibility, not a presumption that every confirmation increases a score.
