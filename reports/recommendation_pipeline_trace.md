# Recommendation Pipeline Trace

## Verdict

The community list becomes empty inside the frontend recommendation engine, not in the API and not in any knowledge-snapshot layer.

## Trace

1. Search request enters the results page through `searchParams` and questionnaire state in [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx#L152).
2. The page fetches facilities with `fetchSearchFacilities(textQuery)` in [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx#L166).
3. `fetchSearchFacilities()` calls `GET /facilities`, maps the backend facilities, and falls back to the local dataset if the API returns nothing or errors in [frontend/src/lib/api.ts](../frontend/src/lib/api.ts#L1338).
4. The page passes the returned facilities into `runOptimeV2Engine(facilities, state)` in [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx#L179).
5. The engine builds `recommendations`, then empties the visible list at `accepted = recommendations.filter((recommendation) => recommendation.hardRejectionReasons.length === 0 && recommendation.totalScore > 0)` in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts#L3153).
6. `buildQualityCheck()` then marks the run as failed when `accepted.length === 0` in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts#L2864).
7. The UI shows the background-check banner when `qualityCheck.passed` is false in [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx#L488), but cards only render when `engineOutput.accepted.length > 0` in [frontend/src/app/results/results-page-client.tsx](../frontend/src/app/results/results-page-client.tsx#L506).

## Answers

- Were communities returned by the Recommendation Engine? Yes, into `recommendations`; no, into `accepted` if they fail hard filters.
- Did the API return them? The API path used here returns facilities, not recommendations. `fetchSearchFacilities()` does return a facility list.
- Did the frontend receive them? Yes, into `facilities` state.
- Were they filtered out? Yes, by the engine acceptance filter.
- Is the background readiness check blocking rendering? No. It only shows the warning banner.
- Is the Knowledge Snapshot layer preventing recommendations from being displayed? No. It is not part of this results-page data path.

## Exact Emptying Point

The list becomes empty at the engine acceptance filter in [frontend/src/lib/optime-v2-engine.ts](../frontend/src/lib/optime-v2-engine.ts#L3153).
