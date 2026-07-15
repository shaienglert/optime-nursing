# OPTIME Validation Study V1

## Goal
Validate whether the current OPTIME success model predicts successful senior living placement outcomes.

Scope for V1:
- Evaluate predictive performance only.
- Do not change model weights.
- Do not introduce new recommendation logic.
- Separate protocol from findings.

## Study Question
Does the current OPTIME success model assign higher predicted placement quality to cases that later have successful outcomes, and does it place the ultimately chosen community in the top 3 ranked options often enough to be operationally useful?

## Cohorts

### Group A: Successful Placement Outcomes
Include cases meeting most of the following:
- Resident stayed more than 12 months.
- Family satisfaction is high.
- No transfer to another community.
- Good social integration.
- Stable health outcome.

### Group B: Unsuccessful Placement Outcomes
Include cases meeting one or more of the following major failure indicators:
- Resident moved again within 12 months.
- Family dissatisfaction.
- Poor social adjustment.
- Frequent complaints.
- Isolation indicators.

## Inclusion and Exclusion Rules

Inclusion:
- Completed placement cases with at least 12 months of follow-up or a documented early failure event.
- Complete baseline resident profile and community profile at time of decision.
- Archived candidate community list available at placement time.

Exclusion:
- Cases with missing final outcome label.
- Cases where candidate list is unavailable.
- Cases with major missing baseline fields that prevent scoring.

## Required Case Data

### Resident Profile Fields
- age
- gender
- mobility_level
- cognitive_status
- marital_status
- language
- religion
- hobbies
- family_proximity
- family_involvement

### Community Profile Fields
- size
- culture
- religious_identity
- activities
- staffing_quality
- regulatory_quality
- distance_from_family

### Outcome Label Fields
- outcome_group: A or B
- stayed_12m: true or false
- family_satisfaction_level: low, medium, high
- transferred_within_12m: true or false
- social_integration_level: low, medium, high
- health_stability: low, medium, high

## Study Dataset Structure

Store one row per resident placement case with:
- case_id
- resident_profile
- selected_community_id
- candidate_community_ids
- candidate_scores_from_optime
- candidate_rankings_from_optime
- outcome_label
- evidence_timestamps

## Evaluation Procedure

1. Freeze model version and feature definitions from [docs/SUCCESS_SIGNAL_MODEL.md](docs/SUCCESS_SIGNAL_MODEL.md).
2. Reconstruct each case as it existed at decision time.
3. Run current OPTIME scoring over that case candidate set.
4. Record selected community rank and score.
5. Compare Group A vs Group B score distributions.
6. Compute classification metrics using a predefined success cutoff.
7. Compute signal contribution analysis from current model outputs.

## Primary Evaluation Questions

1. Did OPTIME rank the chosen community in the top 3?
2. Did OPTIME assign higher scores to successful placements than unsuccessful placements?
3. Which signals contributed most to prediction accuracy?

## Metrics Definition

### Top-3 Ranking Hit Rate
- Definition: proportion of cases where selected community rank <= 3.
- Report overall and by group.

Formula:

$$
\text{Top3HitRate} = \frac{\#(\text{cases with selected rank} \le 3)}{\#(\text{all evaluable cases})}
$$

### Precision

$$
\text{Precision} = \frac{TP}{TP + FP}
$$

### Recall

$$
\text{Recall} = \frac{TP}{TP + FN}
$$

### False Positives
- Cases predicted successful by OPTIME but observed in Group B.

### False Negatives
- Cases predicted unsuccessful by OPTIME but observed in Group A.

### Suggested Supporting Metrics
- ROC-AUC
- PR-AUC
- Calibration error (optional)
- Group-wise mean score difference

## Confusion Matrix Template

| Observed \ Predicted | Successful | Unsuccessful |
|---|---:|---:|
| Successful (Group A) | TP | FN |
| Unsuccessful (Group B) | FP | TN |

## Signal Contribution Analysis

For each case, log model-level contribution outputs and aggregate by signal:
- average absolute contribution
- contribution direction consistency
- contribution lift for Group A vs Group B

Output a ranked table:

| signal_name | avg_abs_contribution | contribution_direction | contribution_lift_A_vs_B | notes |
|---|---:|---|---:|---|

## Data Quality and Bias Controls

- Temporal integrity: use only data available before or at placement decision date.
- Label consistency: lock outcome labeling rules before analysis.
- Missingness handling: keep missing values null; do not impute unless explicitly pre-registered.
- Leakage check: ensure post-placement features are not included in scoring inputs.
- Stratified analysis: report metrics by care level and cognitive status subgroup.

## Execution Checklist

- Freeze model and feature schema.
- Build labeled Group A and Group B cohorts.
- Validate completeness of required fields.
- Run scoring for each case.
- Generate rankings and predicted labels.
- Compute precision, recall, false positives, false negatives.
- Compute top-3 hit rate.
- Run signal contribution aggregation.
- Document findings and failure modes.

## V1 Output Requirements

This document defines protocol only and does not report fabricated results.

When study run is complete, append:
- cohort size summary
- metric values
- confusion matrix counts
- top predictive signal contribution table
- error analysis on false positives and false negatives

## Result Reporting Template

### Cohort Summary
- total_cases: null
- group_a_cases: null
- group_b_cases: null

### Ranking Performance
- top_3_hit_rate_overall: null
- top_3_hit_rate_group_a: null
- top_3_hit_rate_group_b: null

### Classification Performance
- precision: null
- recall: null
- false_positives: null
- false_negatives: null

### Score Separation
- mean_optime_score_group_a: null
- mean_optime_score_group_b: null
- median_optime_score_group_a: null
- median_optime_score_group_b: null

### Interpretation Guardrails
- Do not tune weights in this phase.
- Treat this as baseline validation.
- Use observed failure patterns to plan V2 model updates.