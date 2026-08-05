# OPTIME Core Generalization Audit

Status: Initial audit
Branch: `audit/core-generalization`

## Purpose

Verify whether the current implementation can support additional OPTIME domains, beginning with Employment, without changing the constitutional decision principles.

This audit does not redesign OPTIME. It checks whether the implementation matches the architecture that was defined from the start.

## Classification

- `CORE` — domain-independent and reusable.
- `SENIOR_DOMAIN` — belongs specifically to Senior Living.
- `REFACTOR` — conceptually reusable but implemented with Senior Living assumptions.
- `DUPLICATE` — overlapping decision authority exists in more than one runtime layer.

## Initial findings

### 1. Backend application composition

| File / area | Classification | Finding |
|---|---|---|
| `backend/app/main.py` | REFACTOR | Application composition directly imports Facility, ResidentOutcome, CMS services and patient decision services. The application boundary is currently OPTIME Nursing, not OPTIME Core. |
| `backend/app/models/facility.py` | SENIOR_DOMAIN | Facility, inspection, staffing, quality and resident-outcome records are Senior Living entities. |
| `backend/app/services/cms_*` | SENIOR_DOMAIN | CMS ingestion and normalization are domain data connectors. |
| `backend/app/services/patient_decision_engine.py` | REFACTOR | Contains reusable concepts such as requirement level, eligibility, evidence strength, unknowns and comparison, but they are coupled to patient, facility and clinical parameters. |
| `backend/app/services/facility_parameter_service.py` | REFACTOR | Canonical parameter mechanics may be reusable; the registry and entity model are facility-specific. |
| evidence integrity, knowledge refresh and audit services | REFACTOR | The governance concepts are reusable, but current contracts and records are facility-oriented. |

### 2. Frontend decision authority

| File / area | Classification | Finding |
|---|---|---|
| `frontend/src/lib/optime-v2-engine.ts` | DUPLICATE | Implements material decision logic: personas, weights, match criteria, scoring, rejection rationale, evidence handling and explanations. This is not presentation-only logic. |
| `frontend/src/lib/decision-intelligence-framework.ts` | DUPLICATE | Builds profiles, recommendation tiers, dimension scores, explanations and audit outputs in the frontend. |
| `frontend/src/context/questionnaire-context.tsx` | SENIOR_DOMAIN | The questionnaire state is a hard-coded Senior Living profile, not a domain-configured requirement collection engine. |
| `frontend/src/app/intake/page.tsx` | SENIOR_DOMAIN | Senior Living product experience. |

## Confirmed architectural deviations

### A. More than one decision authority

Production decision logic exists in both Python backend and TypeScript frontend. This can produce inconsistent eligibility, ordering, explanations and evidence treatment.

Required rule:

> One production decision authority. Frontend renders and collects input; backend decides and explains.

### B. Core concepts are embedded in domain code

The implementation already contains the correct constitutional concepts:

- Must / Important / Preference levels
- eligibility before preference
- verified / inferred / unknown evidence
- missing information
- trade-offs
- explanation and auditability

However, these concepts are represented through Senior Living names and schemas.

### C. Questionnaire is not yet a reusable engine

The current questionnaire is a single strongly typed Senior Living state object. Employment requires two independently active profiles:

- candidate profile and requirements
- employer / role profile and requirements

Both must use the same generic requirement structure while retaining separate domain questions.

### D. Current matching topology is one-sided

Senior Living currently evaluates one subject against facilities. Employment requires the same pair evaluation to be callable from either direction:

- candidate searches active positions
- employer searches active candidates

This does not change OPTIME's decision principles. It requires a reusable pair-evaluation contract and two active entity repositories.

## Core contracts that should be extracted

The following are candidates for `OPTIME Core`, subject to deeper code-level verification:

```text
DecisionParty
DecisionOption
Requirement
RequirementLevel
Constraint
Preference
EvidenceRecord
EvidenceSource
EvidenceStrength
Unknown
EligibilityResult
PairEvaluation
Explanation
TradeOff
ClarificationQuestion
InteractionState
Outcome
AuditTrace
```

The Core must not import or name:

```text
Patient
Resident
Facility
CMS
Candidate
Employer
Job
```

Domain packages map their entities and ontology into Core contracts.

## Employment-specific extension confirmed so far

Employment requires two active domain repositories and one symmetric evaluation service:

```text
Candidate repository
        ↕
Pair evaluation and explanation
        ↕
Position repository
```

The engine does not reject people or employers by independent judgment. An option is excluded only when it does not satisfy a requirement explicitly classified as mandatory by the relevant user. Important and nice-to-have gaps remain visible and explained.

## Immediate technical priorities

1. Declare the backend as the sole production decision authority.
2. Inventory every exported decision function in `optime-v2-engine.ts` and `decision-intelligence-framework.ts`.
3. Map each function to `MOVE_TO_BACKEND`, `RENDER_ONLY`, `DELETE_DUPLICATE`, or `SENIOR_DOMAIN`.
4. Extract generic requirement and evidence contracts without altering current Senior Living behavior.
5. Introduce domain boundaries before adding Employment entities.
6. Add golden tests proving that Senior Living recommendations do not change during extraction.

## Current verdict

The constitutional architecture is suitable for OPTIME Jobs.

The current implementation is not yet domain-pluggable. It is a strong Senior Living implementation containing reusable Core concepts, but those concepts must be extracted and duplicate frontend decision authority must be removed before Employment is added.
