# OPTIME Dependency Map

Status: Architecture audit
Branch: `audit/core-generalization`

## Purpose

Map the current runtime dependencies before extracting OPTIME Core. This document identifies decision authority, domain coupling, duplication, and the safest extraction sequence. It does not change production behavior.

## Current runtime topology

```text
Frontend product pages
  ├─ questionnaire-context.tsx
  ├─ intake/page.tsx
  └─ page.tsx
        │
        ├─ optime-v2-engine.ts
        │    ├─ questionnaire-context.tsx
        │    ├─ governed-runtime.ts
        │    ├─ questionnaire-graph.ts
        │    ├─ api.ts
        │    └─ budget-utils.ts
        │
        ├─ decision-intelligence-framework.ts
        │    ├─ questionnaire-context.tsx
        │    ├─ optime-v2-engine.ts
        │    └─ budget-utils.ts
        │
        └─ API client
             │
             ▼
Backend main.py
  ├─ patient_decision_engine.py
  │    └─ facility_parameter_service.py
  ├─ facility_parameter_service.py
  ├─ facility models
  ├─ CMS import services
  ├─ evidence and traceability services
  ├─ provider identity and verification services
  ├─ knowledge refresh / agent services
  └─ reporting and scheduler services
```

## Critical dependency findings

### 1. Decision authority is split

The frontend contains material decision behavior in three connected layers:

- `frontend/src/lib/optime-v2-engine.ts`
- `frontend/src/lib/governed-runtime.ts`
- `frontend/src/lib/decision-intelligence-framework.ts`

These layers classify requirements, apply weights, determine eligibility/rejection states, build ranking factors, create explanations and package recommendations.

The backend separately runs `patient_decision_engine.py` and facility parameter evaluation.

**Consequence:** the product currently has more than one place capable of changing the answer.

### 2. The most reusable frontend layer is still domain-coupled

`governed-runtime.ts` contains reusable concepts:

- requirement classification
- evidence states
- authority levels
- rule validation status
- eligibility transitions
- source traceability

But it directly imports `QuestionnaireState` and `SearchFacility`, uses `FacilityEvidenceRecord`, `canonical_facility_id`, clinical assessment types, and hard-coded nursing/rehabilitation/mobility logic.

**Classification:** `REFACTOR`, not `CORE`.

### 3. Questionnaire state is a dependency root

`questionnaire-context.tsx` is imported by:

- `optime-v2-engine.ts`
- `governed-runtime.ts`
- `decision-intelligence-framework.ts`
- `verification-inbox.ts`
- product pages

Because the state object is Senior Living-specific, every consumer inherits domain coupling.

**Consequence:** extracting the questionnaire contract first creates the largest reduction in coupling.

### 4. Backend composition is a domain application, not a core boundary

`backend/app/main.py` directly composes:

- Facility and ResidentOutcome models
- CMS ingestion
- clinical and facility evidence
- patient decision services
- provider identity
- nursing-specific API schemas

This is valid for the Senior Living application, but `main.py` cannot become OPTIME Core.

**Required boundary:** Core must sit below `main.py`; Senior Living must compose Core.

## File classification map

| File / area | Classification | Target |
|---|---|---|
| `frontend/src/context/questionnaire-context.tsx` | SENIOR_DOMAIN + REFACTOR CONTRACT | Senior profile adapter consuming generic questionnaire contracts |
| `frontend/src/lib/optime-v2-engine.ts` | DUPLICATE + SENIOR_DOMAIN | Remove production decision authority; keep only presentation-safe helpers after backend parity |
| `frontend/src/lib/governed-runtime.ts` | REFACTOR | Move generic requirement/evidence contracts and evaluation to backend Core; retain no decision authority in frontend |
| `frontend/src/lib/decision-intelligence-framework.ts` | DUPLICATE | Replace with rendering of backend decision package |
| `frontend/src/lib/questionnaire-graph.ts` | SENIOR_DOMAIN / POSSIBLE ENGINE CONFIG | Separate generic graph runner from Senior question definitions |
| `frontend/src/lib/verification-inbox.ts` | REFACTOR | Generic clarification workflow plus Senior labels/configuration |
| `frontend/src/lib/api.ts` | MIXED | Split generic Core DTOs from Senior Facility DTOs |
| `frontend/src/app/intake/page.tsx` | SENIOR_DOMAIN | Remains product UI |
| `backend/app/main.py` | SENIOR_DOMAIN COMPOSITION | Remains Senior application entry point; imports Core and Senior modules |
| `backend/app/services/patient_decision_engine.py` | REFACTOR | Split generic pair evaluation from Senior requirement mapping |
| `backend/app/services/facility_parameter_service.py` | REFACTOR | Split canonical parameter engine from facility registry/configuration |
| `backend/app/models/facility.py` | SENIOR_DOMAIN | Remains Senior domain model |
| `backend/app/services/cms_*` | SENIOR_DOMAIN | Remain Senior connectors |
| evidence integrity / audit trace services | REFACTOR | Generalize entity references and evidence contracts |
| provider identity / facility memory | SENIOR_DOMAIN + REUSABLE PATTERN | Keep Senior implementation; extract generic verification interfaces only |
| agent knowledge refresh / supervisor services | REFACTOR | General orchestration may be Core; current records and reports are domain-oriented |

## Proposed target dependency direction

```text
OPTIME Core
  ├─ requirements
  ├─ evidence
  ├─ eligibility
  ├─ pair evaluation
  ├─ explanation
  ├─ clarification
  ├─ interaction state
  ├─ outcome
  └─ audit trace
       ▲
       │
Senior Living domain
  ├─ resident profile adapter
  ├─ facility option adapter
  ├─ Senior questionnaire definitions
  ├─ clinical/professional rules
  ├─ CMS evidence connectors
  └─ admission workflow
       ▲
       │
Senior Living API and frontend
```

Future Employment direction:

```text
OPTIME Core
       ▲
       │
Employment domain
  ├─ candidate profile adapter
  ├─ position profile adapter
  ├─ employer profile adapter
  ├─ candidate questionnaire definitions
  ├─ employer/position questionnaire definitions
  ├─ employment evidence connectors
  └─ mutual-interest workflow
       ▲
       │
Candidate experience + Employer workspace
```

Core must never import either domain.

## Safe extraction order

### Step 0 — Freeze behavior

Create golden cases from current Senior Living production outputs. Persist:

- eligible and excluded facilities
- requirement classifications
- unknowns and verification requests
- ordering
- explanations
- evidence traces

No extraction is accepted if these outputs change unintentionally.

### Step 1 — Generic contracts only

Introduce backend Core contracts without moving algorithms yet:

```text
Requirement
RequirementLevel
RequirementOrigin
EvidenceRecord
EvidenceState
EvidenceConfidence
EligibilityResult
PairEvaluation
Explanation
TradeOff
ClarificationQuestion
AuditTrace
```

Senior services adapt existing structures into these contracts.

### Step 2 — Requirement classification

Move classification authority from `governed-runtime.ts` into backend Core.

Senior-specific rules such as nursing, rehabilitation and mobility remain in a Senior rule adapter.

Frontend sends explicit user answers and renders the returned classification.

### Step 3 — Evidence and eligibility

Move evidence-state mapping, mandatory checks, unknown handling and eligibility transitions into backend Core.

The Senior domain supplies evidence records and parameter meanings.

### Step 4 — Explanation package

Backend becomes the sole source of:

- why an option was shown
- advantages
- disadvantages
- unmet important preferences
- missing information
- clarification questions

Frontend stops generating recommendation narratives.

### Step 5 — Remove duplicate frontend authority

Delete or reduce production paths in:

- `optime-v2-engine.ts`
- `governed-runtime.ts`
- `decision-intelligence-framework.ts`

Only rendering, formatting and local UI state may remain.

### Step 6 — Domain-configured questionnaire engine

Separate:

```text
Generic question graph runner
Senior Living question definitions
Senior profile adapter
```

Only after this boundary exists should Employment questionnaires be added.

### Step 7 — Add symmetric pair evaluation

Generalize the evaluation call so either repository can initiate it:

```text
evaluate(subject, option, subject_requirements, option_requirements, evidence)
```

For Employment, the same candidate-position pair is evaluated against requirements declared by both parties. The engine explains; only users express interest, reject, or proceed.

## First implementation slice

The safest first code change is **not** to move the full decision engine.

Implement one narrow backend Core module containing only generic enums and DTOs for requirements and evidence, then adapt `patient_decision_engine.py` to emit them while preserving its current result.

This slice proves the boundary without altering ranking, eligibility, or user-facing explanations.

## Exit criteria before Employment development

Employment implementation may begin only when:

1. Backend is the sole production decision authority.
2. Frontend contains no eligibility, exclusion, ordering or explanation generation.
3. Generic requirement and evidence contracts contain no Senior terminology.
4. Senior Living passes golden regression cases.
5. Questionnaire execution is separated from Senior question definitions.
6. A pair evaluation can be initiated from either side without changing decision principles.
