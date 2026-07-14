# OPTIME Score Engine Architecture

## 1. Objective
The OPTIME Score Engine produces explainable, comparable, and confidence-aware facility scores for senior living decisions.

Design goals:
- Make ranking transparent for families and care coordinators.
- Separate raw evidence from scoring logic.
- Expose confidence so users can judge data reliability.
- Support model evolution without breaking the UI contract.

## 2. Core Score Set
The engine calculates the following component scores (0-100):
- Medical Quality
- Safety
- Staffing
- Lifestyle
- Activities
- Food
- Environment
- Community
- Memory Support
- Outcome Prediction

Each component score must include:
- value: numeric score from 0 to 100
- source: data lineage for the score
- confidence: reliability estimate from 0 to 1

## 3. Data Contract

```ts
export type ScoreEvidenceSource = {
  provider: string;          // e.g. CMS, State Inspection DB, Internal Survey
  dataset: string;           // e.g. cms_quality_rating_2026_q2
  field: string;             // e.g. staffing_hours_per_resident_day
  timestamp: string;         // ISO date
  weight: number;            // contribution in this component (0-1)
};

export type ScoreComponent = {
  name:
    | "Medical Quality"
    | "Safety"
    | "Staffing"
    | "Lifestyle"
    | "Activities"
    | "Food"
    | "Environment"
    | "Community"
    | "Memory Support"
    | "Outcome Prediction";
  value: number;             // 0-100
  source: ScoreEvidenceSource[];
  confidence: number;        // 0-1
};

export type FacilityScoreCard = {
  facilityId: string;
  generatedAt: string;       // ISO date
  components: ScoreComponent[];
  overallScore: number;      // 0-100 weighted aggregate
  overallConfidence: number; // 0-1
};
```

## 4. Score Construction Pipeline

### Step A: Ingestion
Collect multi-source evidence:
- Public quality datasets (federal/state)
- Inspection and violation records
- Staffing reports
- Outcomes and incident metrics
- User/reviewer feedback
- Facility metadata and amenities

### Step B: Standardization
- Map raw values to canonical fields.
- Apply unit normalization and range clipping.
- Handle missing values with imputation strategy tags.
- Record data freshness metadata.

### Step C: Feature Engineering
Generate component-level features, for example:
- Medical Quality: hospitalization rate, rehospitalization, care quality ratings.
- Safety: falls, medication errors, inspection deficiencies.
- Staffing: RN/LPN/CNA hours, turnover, staffing consistency.
- Lifestyle: resident autonomy indicators, schedule flexibility.
- Activities: program variety, frequency, participation.
- Food: nutrition quality, resident feedback, menu diversity.
- Environment: cleanliness, space quality, outdoor access.
- Community: social engagement, family participation, inclusion.
- Memory Support: dementia-specific programs and trained staff.
- Outcome Prediction: projected wellbeing/risk trajectory model output.

### Step D: Component Scoring
Convert features into 0-100 component values:
- Blend rules-based and model-based calculators.
- Calibrate by geography and facility type.
- Penalize stale or inconsistent evidence.

### Step E: Confidence Estimation
Confidence is computed per component based on:
- Data coverage ratio
- Source quality tier
- Freshness decay
- Source agreement
- Missingness/imputation penalties

### Step F: Aggregation
Calculate overall score as weighted mean of components:

$$
Overall = \sum_{i=1}^{10} w_i \cdot component_i
$$

Default weights (sum = 1.0):
- Medical Quality: 0.16
- Safety: 0.14
- Staffing: 0.14
- Lifestyle: 0.08
- Activities: 0.08
- Food: 0.07
- Environment: 0.08
- Community: 0.08
- Memory Support: 0.09
- Outcome Prediction: 0.08

Overall confidence:

$$
OverallConfidence = \sum_{i=1}^{10} w_i \cdot confidence_i
$$

## 5. Source and Confidence Requirements Per Score

### Medical Quality
- value: 0-100
- source: CMS quality metrics, hospitalization/rehospitalization datasets, inspection outcomes
- confidence: high when clinical datasets are recent and complete

### Safety
- value: 0-100
- source: state/federal incident and deficiency records, safety audit reports
- confidence: reduced when incident data is delayed or sparse

### Staffing
- value: 0-100
- source: staffing submissions, turnover reports, verified schedule consistency indicators
- confidence: boosted by repeated monthly reporting

### Lifestyle
- value: 0-100
- source: resident autonomy surveys, policy metadata, daily routine flexibility indicators
- confidence: medium unless externally validated

### Activities
- value: 0-100
- source: activity calendars, participation rates, resident/family feedback
- confidence: depends on participation telemetry completeness

### Food
- value: 0-100
- source: nutrition compliance, menu diversity records, resident meal satisfaction
- confidence: medium-high with recurring survey cadence

### Environment
- value: 0-100
- source: inspection cleanliness indicators, indoor/outdoor amenity metadata, accessibility checks
- confidence: high when recent inspections exist

### Community
- value: 0-100
- source: social engagement metrics, family visitation signals, group program participation
- confidence: medium when self-reported data dominates

### Memory Support
- value: 0-100
- source: dementia care certifications, memory-care staffing ratios, program evidence
- confidence: high with verifiable credentialing + outcomes

### Outcome Prediction
- value: 0-100
- source: predictive model output using longitudinal quality/safety/staffing and resident-fit features
- confidence: model-calibrated probability quality plus feature completeness

## 6. Explainability Output
Each component explanation should expose:
- Top positive contributors
- Top negative contributors
- Key source references used
- Confidence rationale

Example shape:

```json
{
  "name": "Safety",
  "value": 82,
  "confidence": 0.87,
  "source": [
    {
      "provider": "State Inspection DB",
      "dataset": "inspection_findings_2026_q1",
      "field": "high_risk_deficiencies",
      "timestamp": "2026-04-15",
      "weight": 0.45
    }
  ],
  "explanation": {
    "positives": ["Low serious deficiency count", "Strong medication protocol compliance"],
    "risks": ["Incident reporting lag in last 30 days"],
    "confidenceReason": "High-quality recent inspections with minor reporting delay"
  }
}
```

## 7. Governance and Versioning
- Version every score release: engineVersion, featureVersion, weightProfileVersion.
- Keep an audit log of source snapshots used per run.
- Recompute confidence when source freshness expires.
- Run bias and drift checks per region and resident profile.

## 8. MVP Implementation Checklist
- Define canonical feature schema for all 10 components.
- Implement component calculators with unit tests.
- Implement confidence calculator with penalties/bonuses.
- Expose a single score-card API contract for frontend consumption.
- Add score explanation payload for detail pages.
- Add monitoring dashboard for score drift and confidence coverage.

## 9. Component Formula Definitions (MVP)

All component scores are normalized to 0-100 and clipped to [0, 100].

### Medical Quality Formula

$$
MedicalQuality = 0.40 \cdot QM + 0.25 \cdot Outcomes + 0.20 \cdot Rehospitalization + 0.15 \cdot ClinicalInspection
$$

Where:
- $QM$: composite of CMS quality measure values
- $Outcomes$: adverse clinical outcome performance (inverted where lower is better)
- $Rehospitalization$: short-stay rehospitalization performance (inverted)
- $ClinicalInspection$: clinically relevant inspection/deficiency severity component

### Staffing Formula

$$
Staffing = 0.35 \cdot RNHours + 0.25 \cdot TotalNurseHours + 0.20 \cdot WeekendCoverage + 0.20 \cdot StaffingStability
$$

Where:
- $RNHours$: normalized RN hours per resident day
- $TotalNurseHours$: normalized total nurse hours per resident day
- $WeekendCoverage$: weekend staffing sufficiency
- $StaffingStability$: retention/turnover and reporting consistency indicators

### Safety Formula

$$
Safety = 0.45 \cdot DeficiencySeverity + 0.25 \cdot IncidentRisk + 0.15 \cdot PenaltyHistory + 0.15 \cdot StaffingRisk
$$

Where:
- $DeficiencySeverity$: scope-severity weighted deficiency score (inverted risk)
- $IncidentRisk$: falls/medication/safety event risk component (inverted)
- $PenaltyHistory$: CMS fines and payment denials trend component (inverted)
- $StaffingRisk$: understaffing-related safety risk signal (inverted)
