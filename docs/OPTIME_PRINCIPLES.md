# OPTIME Core Principles

## Law 00: Trusted + Intelligent
OPTIME exists to become the world's most trusted and intelligent decision institution.

All product decisions are evaluated against two required outcomes:

1. Trust
2. Institutional Intelligence

If a feature does not improve one or both, it does not belong in OPTIME.

## Command Canon
The institutional command canon is mandatory doctrine for all OPTIME decisions:

- Command 001-020: see `docs/COMMAND_CANON_001_020.md`
- Decision Psychology Command DP-001 to DP-018: see `docs/COMMAND_DP_001_018.md`
- Expert Coordination Command EXP-001 to EXP-015: see `docs/COMMAND_EXP_001_015.md`
- Database Command DB-001 to DB-010: see `docs/COMMAND_DB_001_010.md`
- Discovery Agent Constitution D-001 to D-020: see `docs/COMMAND_D_001_020_DISCOVERY_AGENT.md`

## Canonical Principles Registry
The canonical source of principle truth and lifecycle status is:

- `docs/OPTIME_PRINCIPLES_REGISTRY.md`

All substantial work that touches ranking, scoring, recommendations, agents, evidence, unknown handling, confidence, source governance, monetization boundaries, or architecture must run a Principle Impact Check before semantic changes.

## Principle 1: Outcome-Only Optimization
The recommendation engine optimizes only for the user's outcome.

The engine must never use:
- referral fees
- advertising spend
- sponsorships
- partner status
- premium accounts
- available inventory

The engine may only use:
- user profile
- user preferences
- user constraints
- objective evidence
- verified outcomes
- confidence levels

## Principle 2: No Evidence, No Score
No evidence, no score.

If evidence is insufficient:
- return null
- display "insufficient evidence"

Missing values must never be estimated.

## Principle 3: Explainability Is Mandatory
Every recommendation must be explainable.

For every recommendation, OPTIME must show:
- why it was recommended
- which data sources were used
- confidence level
- missing information

## Principle 4: Uncertainty Must Be Visible
Uncertainty is a first-class output and must always be shown.

Display one of:
- High confidence
- Medium confidence
- Low confidence
- Insufficient evidence

Uncertainty must never be hidden.

## Principle 5: Strict Separation of Recommendation and Business Logic
Business logic is separated from recommendation logic.

Revenue systems must never influence:
- rankings
- scores
- recommendations

Business data must not be accessible by the recommendation engine.

## Principle 6: User Outcome Over Platform Transaction
OPTIME searches for the optimal outcome for the user, not the optimal transaction for the platform.

## Principle 7: Knowledge Is The Strategic Asset
OPTIME does not compete on access to a language model.

OPTIME competes on the quality, breadth, freshness, and trustworthiness of its knowledge.

Knowledge must be:
- structured
- verified
- reusable
- explainable
- independent of any single model vendor

## Principle 8: One Trusted Voice
Families experience one advisor.

They never see:
- internal agents
- scoring formulas
- model orchestration
- architecture details

All internal complexity must resolve into one professional, grounded recommendation voice.

## Principle 9: No Commercial Bias
Recommendations must never be influenced by:
- referral fees
- commissions
- advertising
- placement agreements
- lead value
- popularity for its own sake

Only verified resident needs and verified knowledge may shape the recommendation.

## Principle 10: Knowledge Never Stops Improving
Every provider update, research update, outcome signal, and verified correction should strengthen the institution.

Knowledge is never finished.

It compounds.

It improves every future recommendation.

## Principle 11: Booking + Tinder Decision Journey
OPTIME must combine:
- Booking-style decision depth for rich facility profiles and structured comparison
- Tinder-style discovery efficiency for fast visual scanning, save/skip/compare behavior, and shortlist learning
- OPTIME-specific evidence intelligence that answers what the facility means for this person specifically

This is a product principle, not a branding directive.

It does not permit copying Booking or Tinder layouts, branding, or proprietary interaction patterns.

## Principle 12: Principle Consistency And Owner Approval
Established OPTIME product principles are constitutional constraints, not implementation suggestions.

No contributor may silently change an established principle, including ranking philosophy, scoring semantics, UNKNOWN meaning, evidence weighting, confidence semantics, canonical architecture, or recommendation ordering.

Every substantial change must be classified as one of:

- Implementation Bug
- Implementation Completion
- Product Principle Ambiguity
- Product Principle Change
- Architectural Deviation

If the change is Product Principle Ambiguity, Product Principle Change, or Architectural Deviation:

- semantic implementation must stop
- current principle and behavior must be documented
- problem, proposal, alternatives, and risks must be surfaced
- explicit owner approval is required before implementation

Broad implementation directives such as "continue", "fix it", or "improve it" are not authorization to alter established principles.

Missing information is not negative evidence.

More generic profile completeness does not automatically mean a better facility.

Verified, case-relevant knowledge may legitimately strengthen a recommendation because OPTIME can prove the match.

Facilities may improve representation by supplying evidence, but unverified facility-supplied claims may not improve organic ranking and facilities cannot buy ranking.
