# OPTIME Intelligence Signal Priority

## Objective
Prioritize the intelligence signals that most strongly predict successful senior living placements.

Scoring scale used in this roadmap:
- `predictive_value_score`: 1 (lowest) to 5 (highest)
- `collection_cost`: 1 (lowest effort/cost) to 5 (highest effort/cost)
- `competitive_advantage_score`: 1 (commodity) to 5 (differentiating)

Tier logic:
- Tier 1 (Critical): predictive value >= 4 and reliability strong enough for operational use.
- Tier 2 (Important): predictive value = 3-4, useful when combined with Tier 1 signals.
- Tier 3 (Nice to Have): context signals with lower direct predictive power.

## Signal Priority Table (30 Signals)

| tier | signal_name | category | predictive_value_score | reliability | collection_cost | update_frequency | competitive_advantage_score |
|---|---|---|---:|---:|---:|---|---:|
| TIER 1 | CMS overall rating | Regulatory | 5 | 5 | 1 | Monthly | 3 |
| TIER 1 | CMS staffing hours per resident day | Regulatory | 5 | 5 | 2 | Monthly | 4 |
| TIER 1 | CMS staffing rating | Regulatory | 5 | 5 | 1 | Monthly | 3 |
| TIER 1 | CMS health inspection rating | Regulatory | 5 | 5 | 1 | Monthly | 3 |
| TIER 1 | Deficiency severity pattern (12m) | Regulatory | 5 | 5 | 3 | Monthly | 4 |
| TIER 1 | Fines/enforcement count and severity (12m) | Regulatory | 5 | 5 | 3 | Monthly | 4 |
| TIER 1 | License action events | Regulatory | 5 | 5 | 2 | Weekly | 4 |
| TIER 1 | Understaffing signal recurrence (employee + family corroboration) | Employee Experience | 5 | 4 | 4 | Weekly | 5 |
| TIER 1 | Turnover signal trend | Employee Experience | 4 | 4 | 4 | Weekly | 5 |
| TIER 1 | Communication responsiveness issues (family signal, recurring) | Family Experience | 4 | 4 | 4 | Weekly | 5 |
| TIER 1 | Complaint trajectory (increasing/decreasing) | Trend Signals | 4 | 4 | 3 | Monthly | 4 |
| TIER 1 | Hospitalization frequency proxy | Outcome Signals | 5 | 4 | 4 | Quarterly | 5 |
| TIER 1 | Resident retention / early move-out proxy | Outcome Signals | 5 | 3 | 5 | Monthly | 5 |
| TIER 1 | Successful transition stability (first 90 days) | Outcome Signals | 5 | 3 | 5 | Monthly | 5 |
| TIER 2 | Ownership changes | Stability | 4 | 4 | 2 | Monthly | 4 |
| TIER 2 | Administrator tenure | Stability | 4 | 3 | 4 | Monthly | 5 |
| TIER 2 | Director of Nursing tenure | Stability | 4 | 3 | 4 | Monthly | 5 |
| TIER 2 | Staff warmth recurring signal | Family Experience | 4 | 3 | 4 | Weekly | 4 |
| TIER 2 | Cleanliness recurring signal | Family Experience | 4 | 3 | 4 | Weekly | 4 |
| TIER 2 | Management quality recurring signal | Employee Experience | 4 | 3 | 4 | Weekly | 5 |
| TIER 2 | Burnout recurrence signal | Employee Experience | 4 | 3 | 4 | Weekly | 5 |
| TIER 2 | Improving review trend (90-day) | Trend Signals | 3 | 3 | 3 | Weekly | 4 |
| TIER 2 | Declining staffing trend | Trend Signals | 4 | 4 | 3 | Monthly | 5 |
| TIER 2 | Family satisfaction after move | Outcome Signals | 5 | 2 | 5 | Monthly | 5 |
| TIER 3 | Religious affiliation fit | Community Culture | 3 | 4 | 2 | Quarterly | 3 |
| TIER 3 | Language support availability | Community Culture | 3 | 4 | 2 | Quarterly | 4 |
| TIER 3 | Cultural identity fit | Community Culture | 3 | 3 | 3 | Quarterly | 4 |
| TIER 3 | Social atmosphere fit | Community Culture | 3 | 2 | 4 | Monthly | 4 |
| TIER 3 | Distance from family | Location | 3 | 5 | 1 | On change | 2 |
| TIER 3 | Hospital access proximity | Location | 3 | 5 | 1 | Quarterly | 2 |

## Recommended Predictive Core (Top 24)

The strongest outcome-oriented core for MVP-to-v1 intelligence operations:

1. CMS overall rating
2. CMS staffing hours per resident day
3. CMS staffing rating
4. CMS health inspection rating
5. Deficiency severity pattern (12m)
6. Fines/enforcement count and severity (12m)
7. License action events
8. Understaffing signal recurrence
9. Turnover signal trend
10. Communication responsiveness issues
11. Complaint trajectory
12. Hospitalization frequency proxy
13. Resident retention / early move-out proxy
14. Successful transition stability (first 90 days)
15. Ownership changes
16. Administrator tenure
17. Director of Nursing tenure
18. Staff warmth recurring signal
19. Cleanliness recurring signal
20. Management quality recurring signal
21. Burnout recurrence signal
22. Declining staffing trend
23. Improving review trend (90-day)
24. Family satisfaction after move

## Tier Summary

- TIER 1 (Critical): 14 signals
- TIER 2 (Important): 10 signals
- TIER 3 (Nice to Have): 6 signals

## Implementation Notes

- Treat Tier 1 as the default foundation for operational decision support.
- Use Tier 2 to improve fit quality and earlier risk detection.
- Use Tier 3 for personalization and context, not as dominant risk signals.
- Trend signals should be computed over fixed windows (30/90/180 days) for consistency.
- Outcome signals should be governed with strict provenance and timestamping.