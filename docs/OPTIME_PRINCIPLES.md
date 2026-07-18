# OPTIME Core Principles

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
