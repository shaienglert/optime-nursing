# OPTIME Score v1 Definition

## Purpose
OPTIME Score ranks facilities with transparent component weights based on quality, safety, staffing, reviews, and value.

## Weighting
- Overall Quality: 35%
- Staffing: 25%
- Safety and Inspections: 20%
- Family Reviews: 10%
- Value for Money: 10%

## Formula
Let each component be normalized to 0-100.

OPTIME Score =
(0.35 * Quality) +
(0.25 * Staffing) +
(0.20 * Safety) +
(0.10 * Reviews) +
(0.10 * Value)

## Component Definitions and Data Sources

### 1) Overall Quality (35%)
Data sources:
- CMS Quality Measures datasets
- CMS published quality ratings (qm_rating, overall_rating as fallback)

Inputs:
- Measure-level performance and composite quality ratings.

### 2) Staffing (25%)
Data sources:
- CMS staffing datasets
- Staffing fields in provider datasets (staffing_rating and staffing hours)

Inputs:
- RN hours per resident day
- Total nurse staffing hours per resident day
- Staffing rating

### 3) Safety and Inspections (20%)
Data sources:
- CMS health inspection datasets
- CMS penalties/fines datasets

Inputs:
- Inspection rating
- Deficiency counts and severity
- Penalty/fine signals

### 4) Family Reviews (10%)
Data sources:
- OPTIME FacilityReview table (first-party and approved third-party feeds)

Inputs:
- Average review rating
- Recency-weighted sentiment
- Review volume confidence adjustments

### 5) Value for Money (10%)
Data sources:
- Facility price/payor data (when available)
- CMS quality and staffing signals for value normalization

Inputs:
- Relative cost vs market and peer quality
- Quality-adjusted cost index

## v1 Operational Notes
- Missing components should use explicit fallback logic and confidence penalties.
- Persist component sub-scores in OptimeScore for explainability.
- Keep score_version for backwards compatibility during formula updates.

## Architecture Recommendation
- MVP: Single Facility table with precomputed fields and light score generation.
- Production: Normalized model with periodic component recomputation from source fact tables.

Decision:
Use single-table MVP immediately, while implementing normalized production entities in parallel for long-term scalability.
