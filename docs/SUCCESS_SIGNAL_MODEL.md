# OPTIME Success Signal Model v1

## Goal
Identify and measure the factors that predict successful adjustment after moving to senior living.

This model is for intelligence collection and outcome prediction design only.
It does not create recommendation scores.

## Scoring Framework

- predictive_value_score: 1 (low) to 5 (high)
- collection_difficulty: 1 (easy) to 5 (hard)
- confidence_score: 1 (low confidence) to 5 (high confidence)
- reliability_score: 1 (weak source reliability) to 5 (strong source reliability)

## Category 1 - Family Connection

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| Distance from family | Nearness increases visit consistency and emotional continuity. | Miles between reference family location and community. | Family input, mapping APIs | 5 | On change | 4 | 1 | 5 |
| Expected visit frequency | More frequent visits usually improve adjustment and retention. | Self-reported expected visits per week or month. | Family interview, intake form | 3 | At intake and reassessment | 4 | 2 | 3 |
| Travel time | Long travel burden reduces real visit follow-through. | Median drive time from family to community. | Mapping APIs, traffic APIs | 5 | On change | 4 | 1 | 5 |
| Family involvement level | High involvement predicts better advocacy and transition support. | Structured intake scale (low, medium, high). | Family interview, care team notes | 3 | Monthly | 5 | 3 | 3 |

## Category 2 - Community Fit

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| Language compatibility | Communication barriers can slow trust and care quality. | Match ratio between resident language needs and community support. | Community website, staff listings, intake form | 4 | Quarterly | 4 | 2 | 4 |
| Religious compatibility | Faith alignment can improve comfort and belonging. | Binary and degree-of-fit match to stated preferences. | Community website, family interview | 4 | Quarterly | 3 | 2 | 4 |
| Cultural compatibility | Cultural fit affects adaptation, social confidence, and satisfaction. | Qualitative fit index from profile matching. | Website, activities, family input, reviews | 3 | Quarterly | 4 | 3 | 3 |
| Community size preference | Size mismatch can reduce comfort and social integration. | Difference between preferred and actual resident size band. | Community profile, intake form | 4 | Quarterly | 3 | 2 | 4 |
| Luxury preference | Lifestyle mismatch can affect satisfaction and perceived value. | Amenity tier match against family preference. | Website, photos, pricing collateral, intake form | 3 | Quarterly | 3 | 3 | 3 |
| Social environment preference | Introvert or extrovert fit affects daily wellbeing and participation. | Fit score from activity intensity and resident style preferences. | Activities calendar, reviews, intake form | 3 | Monthly | 4 | 3 | 3 |

## Category 3 - Social Success

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| Activity participation quality | High quality activities improve adjustment and reduce isolation risk. | Theme extraction on activity experience quality mentions. | Reviews, resident testimonials, family notes | 3 | Weekly | 4 | 4 | 3 |
| Activity diversity | Diverse programming supports broader engagement and sustained interest. | Count of distinct activity categories per month. | Activities calendar, website | 4 | Monthly | 4 | 2 | 4 |
| Community engagement | High engagement correlates with stronger social adaptation. | Mention trends for belonging and interaction. | Reviews, community posts, website updates | 3 | Weekly | 4 | 4 | 3 |
| Resident satisfaction mentions | Positive satisfaction signal is a leading indicator of adjustment. | Positive minus negative satisfaction mention balance. | Reviews, survey summaries | 3 | Weekly | 4 | 4 | 3 |
| Loneliness risk indicators | Early loneliness risk predicts failed transitions and move-outs. | Recurring loneliness language pattern detection. | Reviews, family feedback, care notes | 2 | Weekly | 5 | 4 | 2 |

## Category 4 - Staff Relationship

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| Staff warmth mentions | Warmth strongly affects trust and emotional security. | Recurring warmth signal extraction with minimum mention threshold. | Google, Caring, Seniorly | 3 | Weekly | 5 | 4 | 3 |
| Staff responsiveness mentions | Responsiveness predicts issue resolution and family confidence. | Recurring response-time and follow-through mention extraction. | Google, Caring, A Place for Mom | 3 | Weekly | 5 | 4 | 3 |
| Staff continuity | Continuity improves relationship stability and care consistency. | Staff continuity proxy from tenure and turnover indicators. | Indeed, Glassdoor, staffing disclosures | 3 | Monthly | 4 | 4 | 3 |
| Employee turnover | High turnover is associated with instability and lower care consistency. | Trend in turnover and departure mentions over time. | Indeed, Glassdoor, CMS staffing trends | 3 | Monthly | 5 | 4 | 3 |
| Employee satisfaction | Staff morale influences resident interactions and service quality. | Aggregated employee sentiment trend score. | Indeed, Glassdoor | 3 | Monthly | 4 | 3 | 3 |

## Category 5 - Safety

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| CMS ratings | Broad safety and quality benchmark tied to outcomes. | Latest overall CMS rating. | CMS Care Compare, CMS Provider Database | 5 | Monthly | 5 | 1 | 5 |
| Staffing ratings | Staffing quality predicts care responsiveness and safety outcomes. | Latest CMS staffing rating and trend. | CMS Provider Database | 5 | Monthly | 5 | 1 | 5 |
| Inspection ratings | Inspection performance captures compliance and risk signals. | Latest CMS inspection rating and trend. | CMS Provider Database | 5 | Monthly | 5 | 1 | 5 |
| Deficiencies | Deficiency severity and recurrence indicate operational risk. | Count and severity of deficiencies in rolling windows. | CMS deficiency records, state inspections | 5 | Monthly | 5 | 3 | 5 |
| Fines | Monetary penalties indicate confirmed compliance failures. | Fine count and severity in rolling windows. | CMS, state enforcement actions | 5 | Monthly | 5 | 3 | 5 |

## Category 6 - Stability

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| Ownership changes | Frequent ownership changes can disrupt operations and culture. | Ownership change events in last 12 months. | CMS Provider Database, state filings | 4 | Monthly | 4 | 2 | 4 |
| Executive Director tenure | Leadership continuity supports stable operations and resident trust. | Tenure length in months and change events. | Website, leadership pages, filings | 3 | Quarterly | 4 | 4 | 3 |
| Director of Nursing tenure | Clinical leadership stability predicts care consistency. | Tenure length in months and change events. | Website, filings, compliance disclosures | 3 | Quarterly | 4 | 4 | 3 |
| Staff turnover trend | Worsening turnover trend signals rising disruption risk. | 90-day and 180-day trend slope on turnover signals. | Indeed, Glassdoor, staffing trend sources | 3 | Monthly | 5 | 4 | 3 |

## Category 7 - Quality of Life

| signal_name | why_it_matters | how_measured | sources | reliability_score | update_frequency | predictive_value_score | collection_difficulty | confidence_score |
|---|---|---|---|---:|---|---:|---:|---:|
| Food quality | Dining quality is a top driver of day-to-day satisfaction. | Recurring food sentiment signal extraction. | Reviews, dining pages | 3 | Weekly | 4 | 4 | 3 |
| Outdoor spaces | Access to outdoor areas supports wellbeing and social interaction. | Presence and quality indicators from photos and descriptions. | Website, virtual tours, reviews | 3 | Monthly | 3 | 3 | 3 |
| Transportation | Reliable transport affects independence and appointment adherence. | Transportation availability, schedule breadth, and satisfaction mentions. | Website, reviews | 4 | Monthly | 4 | 3 | 4 |
| Dining flexibility | Flexible dining options improve autonomy and quality of life. | Availability of choice windows, menu flexibility, accommodation mentions. | Website, reviews | 3 | Monthly | 3 | 3 | 3 |
| Room quality | Room quality influences comfort and long-term retention. | Recurring room condition and comfort mentions. | Reviews, photos, floor plans | 3 | Monthly | 4 | 4 | 3 |
| Wellness programs | Wellness support improves functional outcomes and satisfaction. | Presence and breadth of wellness program categories. | Website, program calendars | 4 | Monthly | 4 | 2 | 4 |

## Priority Signals For Placement Outcome Prediction

Top 24 signals with strongest expected impact for successful adjustment:

1. Family involvement level
2. Travel time
3. Language compatibility
4. Social environment preference
5. Activity participation quality
6. Community engagement
7. Loneliness risk indicators
8. Staff warmth mentions
9. Staff responsiveness mentions
10. Employee turnover
11. Staff continuity
12. CMS ratings
13. Staffing ratings
14. Inspection ratings
15. Deficiencies
16. Fines
17. Ownership changes
18. Executive Director tenure
19. Director of Nursing tenure
20. Staff turnover trend
21. Food quality
22. Transportation
23. Room quality
24. Wellness programs

## Operational Notes

- Missing values remain null until evidence is collected.
- Facts should remain separate from opinions and allegations.
- For mention-based signals, require recurring patterns rather than isolated comments.
- Collection cadence should be enforced by category-specific refresh schedules.