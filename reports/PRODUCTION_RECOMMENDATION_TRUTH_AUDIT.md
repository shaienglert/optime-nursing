# Production Recommendation Truth Audit

## Executive Summary

The production recommendation flow is now using the live governed backend, but the user-facing semantics were overstating certainty in two places:

1. `100%` match was a verified yes/no fit score, not an evidence-certainty score.
2. Budget `0` was being treated as a real budget and silently replaced with `$7,000`, which could make an unknown budget look intentionally specified.

A second provenance issue was also confirmed: the card price label is not sourced from the backend payload. The backend facilities response currently returns `priceRange: null` for the live dataset, and the frontend derives a synthetic monthly range from facility bed count.

## What Was Verified

- The production frontend is calling the live Render backend.
- `GET /facilities` and `GET /governance/runtime-context` are served with the expected CORS policy.
- The live recommendation cards are rendered from real backend data, not from the old fallback path.
- The governed MUST status is visible in the UI and preserved as `ELIGIBLE_WITH_VERIFICATION_REQUIRED` when details remain unconfirmed.

## Current Truth Model

- `Match: 100%` means the current verified yes/no fit ratio is perfect for the scored items.
- `Confidence` is a separate coverage metric that drops when unknowns remain.
- Unknowns do not reduce the displayed match percentage.
- That separation is technically valid, but the UI can still read as overconfident if the labels are not explicit.

## Findings

### 1. Budget sentinel bug

- The questionnaire state stores budget as a number.
- Production code used `state.budget || 7000`, so `0` was treated as missing and converted to `7000`.
- That affected recommendation scoring, hard-rejection budget checks, and generated family-facing narrative text.
- In the live session state, budget was present as `0`, so the production UI could misrepresent an unspecified budget as a real willingness to pay.

### 2. Price provenance gap

- The backend live facilities payload does not currently author a monthly price range.
- The frontend builds `facility.priceRange` locally from bed count.
- The UI previously rendered that value without labeling it as estimated.
- This is acceptable only if it is clearly disclosed as synthetic.

### 3. Match and confidence semantics are easy to misread

- `100%` match is a ratio of verified yes items to verified yes/no items.
- Unknowns are excluded from that denominator and only reduce confidence.
- The UI needs explicit wording so `100%` cannot be mistaken for complete evidence certainty.

## Changes Applied

- Added a shared budget helper so `0` is treated as unspecified instead of a real budget.
- Updated recommendation scoring and rejection logic to use the shared helper.
- Updated generated verification payloads to say `Budget not supplied` when appropriate.
- Relabeled the UI price line as `Estimated monthly range`.
- Updated family-facing narrative copy to avoid claiming budget certainty when none was supplied.
- Added a focused regression test for the zero-budget sentinel behavior.

## Validation

- Live backend inspection confirmed `priceRange` is null across the current `/facilities` payload.
- The frontend now labels the displayed price as estimated.
- The new regression test asserts that `0` maps to `Budget not supplied` rather than `$7,000`.

## Residual Risk

- Price remains a heuristic estimate unless the backend starts publishing authoritative monthly pricing.
- The `100%` match label is still a fit score; if the product needs stronger truth semantics, the label should be renamed in a future pass to make the distinction even clearer.

## Recommendation

Keep the governed ranking path, but preserve the new disclosure rules:

- use `Budget not supplied` when the budget is unknown,
- show price as an estimate,
- and keep confidence visually distinct from match score.
