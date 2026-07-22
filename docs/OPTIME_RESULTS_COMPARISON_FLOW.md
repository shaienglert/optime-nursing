# OPTIME Results And Comparison Flow

Date: 2026-07-22
Status: ACTIVE
Classification: B. Implementation Completion

## Governance Gate

- RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-006, PR-007, PR-008, PR-009; OPTIME Principles 3, 4, 8, 11; OPTIME Master Parameter Registry Core Rules 5, 7, 8 and Customer Availability Disclosure
- DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
- OWNER APPROVAL REQUIRED? NO

## Purpose

This document defines the canonical consumer decision flow for OPTIME Results and Compare.

It does not change ranking doctrine.

It specifies how governed recommendation truth is presented to families.

## Canonical Definitions

### Top 5

Top 5 is the consumer-facing primary recommendation set.

It contains exactly the five highest currently ranked OPTIME recommendations for the patient context.

These are shown as ranks #1 through #5.

Top 5 answers:

- Which five facilities does OPTIME currently recommend for this person?
- Why are they recommended?
- What meaningful differences exist between them?
- Why is one ranked above another when a governed difference exists?

### Top 10

Top 10 is an internal operational verification and outreach queue.

It is not a consumer result limit.

It exists so OPTIME can investigate and prepare backup options beyond the primary Top 5.

Top 10 may be used to verify:

- current availability
- admission fit
- insurance or payment compatibility
- required service confirmation
- contact attempts
- verification timestamps
- verification outcome

Until verified, these items remain UNKNOWN or confirm directly with facility.

Operational outreach status must never fabricate clinical evidence and must not alter organic ranking without governed verified inputs.

### More Results

More Results is the consumer-facing continuation of the ranked list after Top 5.

It begins at rank #6 and may continue through all remaining relevant ranked facilities returned by the ranking engine.

More Results must not be capped at the internal Top 10.

### Favorites

Favorites is the user-curated shortlist created while scanning Top 5 and More Results.

Favorites is a presentation and navigation feature.

It does not change ranking truth.

### Compare My Favorites

Compare My Favorites is the consumer comparison experience for user-selected facilities.

It uses the same canonical parameter registry, governed evidence semantics, PatientNeedsProfile relevance logic, and UNKNOWN handling as every other comparison surface.

### Favorite Vs OPTIME Recommendation

Favorite Vs OPTIME Recommendation is a focused two-facility comparison.

It compares:

- the facility the user selected
- the current best applicable OPTIME recommendation

Normally the OPTIME reference facility is rank #1.

If rank #1 is later legitimately disqualified by newly verified information, the comparison must explicitly state which higher valid OPTIME recommendation is being used instead and why.

### Full Compare

Full Compare is the canonical expanded parameter comparison.

It must contain exactly 59 unique governed parameters.

Missing evidence does not remove a canonical parameter.

Missing evidence must display as UNKNOWN, Not verified, or confirm directly with facility depending on the governed parameter semantics.

## Canonical Consumer Flow

1. Search or questionnaire submission returns governed ranked recommendations.
2. Results presents Top 5 prominently as the primary decision set.
3. Results includes a patient-specific Top-5 decision table showing only relevant parameters by default.
4. Results exposes concise Why This Rank explanations for the Top 5.
5. Results offers View all parameters to expand to the full canonical 59.
6. Results offers Show more results to reveal all remaining ranked facilities beginning at #6.
7. Users may favorite facilities while scanning.
8. Users may compare their favorites using the canonical comparison engine.
9. Users may compare a chosen favorite against the current best applicable OPTIME recommendation.
10. Facility Profile remains the deeper evidence page.

## Top-5 Table

The Top-5 section is the primary patient-specific decision table.

It must not force the user to open five separate facility profiles just to understand the main differences.

For each Top-5 facility the table should clearly show:

- rank
- facility name
- location
- verified facility image when available, otherwise neutral fallback
- qualitative recommendation label
- relevant parameter statuses
- important strengths
- important items to verify
- CTA to the facility profile

Consumer language should remain qualitative, such as:

- Best fit
- Strong fit
- Good fit
- Strong
- Needs verification
- Verified
- Not verified
- Confirm with facility

Consumer-facing OPTIME percentages or invented numeric scores must not appear in the Results or Compare presentation.

Official source-native metrics, such as clearly labeled CMS values, may remain numeric when presented as source facts rather than OPTIME scores.

## Relevant Parameter Logic

The default parameter set shown in Top 5, Favorites comparison, and Favorite Vs OPTIME comparison is patient-specific.

It is composed from:

- parameters explicitly selected or implied by the user
- parameters OPTIME determines are important for this patient through PatientNeedsProfile and governed parameter-order logic

The default set must not be a universal hard-coded list.

The full comparison remains the same canonical 59 for all consumers.

## Why This Rank

Each Top-5 facility needs a concise Why This Rank explanation.

When meaningful adjacent differences exist, OPTIME should explain them in governed language.

Examples:

- both facilities satisfy core nursing needs, but one has stronger verified rehabilitation evidence relevant to this patient
- both remain strong choices, but one has fewer unresolved questions for current high-priority needs

Never manufacture differences to justify ranking.

UNKNOWN is not negative evidence.

Generic completeness must not become ranking points.

## Comparison Model

All comparison surfaces must use one canonical truth model:

- one canonical parameter registry
- one governed evidence model
- one PatientNeedsProfile relevance model
- one comparison semantics layer
- one UNKNOWN policy

The presentation may differ across Top 5, Favorites, and focused two-facility comparison.

The underlying truth must not.

## Difference-First Focused Comparison

Favorite Vs OPTIME Recommendation exists to answer:

I like this facility. What do I gain or give up compared with OPTIME's recommendation?

The default view should:

- prioritize meaningful differences
- keep required patient needs visible even when both facilities are equal
- avoid cluttering the initial view with irrelevant identical rows

The full canonical 59 must remain available through View all parameters.

## Narrative Difference Summary

The focused two-facility comparison must include a concise patient-specific narrative summary generated only from governed evidence.

The summary should emphasize:

- where both facilities are similarly strong
- where OPTIME's recommendation has stronger verified patient-relevant evidence
- where the user's chosen facility has an advantage, if supported
- important UNKNOWN or verification gaps
- meaningful quality and safety differences
- meaningful patient-fit differences

UNKNOWN must never be rewritten as NO.

The summary must not claim a facility does not offer something unless verified negative evidence exists.

## Favorites Persistence

Favorite state should persist through normal navigation and back behavior during a user session.

Persistence is a consumer convenience feature and does not change recommendation truth.

Internal identifiers should not be exposed in the visible UI.

## Images

Images do not block the Results or Compare experience.

If a verified facility-specific image exists, show it.

If not, show a polished neutral fallback.

Image status must not affect clinical ranking.

No image may be falsely attributed to a facility.

## Internal Top-10 Verification Queue Interface

If outreach infrastructure is not yet implemented, the clean interface must support at least:

- queue_scope: TOP_10_DECISION_QUEUE
- canonical_facility_id
- current_rank_position
- queue_reason
- availability_status
- insurance_payment_status
- required_service_confirmation_status
- contact_status
- contact_attempts
- last_contact_at
- verified_at
- verified_by
- verification_notes
- verification_outcome

Dynamic operational facts remain separate from clinical capability truth.

Operational queue state may update consumer recommendations only through newly verified governed evidence.

## Responsive Layout

More Results should prefer two readable cards side-by-side on larger screens.

On mobile, the layout may use two columns only when cards remain genuinely readable.

Otherwise it should fall back to one card per row.

The Top-5 decision table and compare flows should preserve usability at narrow widths through responsive presentation, not by hiding governed truth.

## Acceptance Rules

- Top 5 consumer results contains exactly 5 primary recommendations.
- More Results begins at #6 and may continue through all remaining relevant facilities.
- Internal Top 10 is not presented as the consumer result limit.
- Default comparison views are patient-specific.
- Expanded comparison shows exactly 59 unique canonical parameters.
- UNKNOWN never becomes NO.
- Consumer-facing OPTIME numeric scores or percentages remain absent.
- Images use verified facility-specific media only when available.
