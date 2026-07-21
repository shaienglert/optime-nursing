# OPTIME Principles Registry

This registry is the canonical lifecycle record for OPTIME governing principles.

Status values:
- ACTIVE
- SUPERSEDED
- PROPOSED

Owner approval is mandatory for principle-level semantic changes and architectural deviations.

## Principle Impact Check (Required Before Substantial Semantic Work)

Run this check before implementing substantial changes to:
- ranking
- scoring
- recommendations
- agents
- evidence
- unknown handling
- confidence
- facility comparison
- data truth
- source governance
- monetization boundaries
- canonical architecture

Required output:
- RELEVANT EXISTING PRINCIPLES: <list>
- DOES THIS CHANGE ALTER ANY PRINCIPLE? YES / NO
- OWNER APPROVAL REQUIRED? YES / NO

If OWNER APPROVAL REQUIRED is YES, stop semantic implementation until explicit approval is provided.

## Principles

| PRINCIPLE_ID | TITLE | EXACT PRINCIPLE | PRODUCT INTENT | DATE_ESTABLISHED | STATUS | APPLIES_TO | IMPLEMENTATION_REFERENCES | TEST_REFERENCES | SUPERSEDES | SUPERSEDED_BY | OWNER_APPROVAL_REFERENCE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PR-001 | Outcome-Only Optimization | Recommendation logic optimizes user outcome only and excludes business incentives. | Protect resident-first decision quality and neutrality. | 2026-01-01 | ACTIVE | Ranking, recommendation ordering, personalization | docs/OPTIME_PRINCIPLES.md | reports/EVIDENCE_PARITY_REGRESSION_TESTS.json | None | None | Foundational doctrine |
| PR-002 | No Evidence, No Score | Missing values must not be estimated where governance requires verified data. | Prevent fabricated certainty and preserve trust. | 2026-01-01 | ACTIVE | Scoring, truth logic, evidence ingestion | docs/OPTIME_PRINCIPLES.md | reports/EVIDENCE_PARITY_REGRESSION_TESTS.json | None | None | Foundational doctrine |
| PR-003 | Uncertainty Visibility | Unknowns and confidence must be visible and explainable. | Avoid hidden uncertainty in family-facing decisions. | 2026-01-01 | ACTIVE | UX explanations, recommendation narrative, control tower | docs/OPTIME_PRINCIPLES.md | reports/GOLDEN_CASE_RANKING_CAUSALITY_AUDIT.json | None | None | Foundational doctrine |
| PR-004 | No Commercial Bias | Sponsored or commercial relationships must not alter organic ranking. | Keep recommendation trust independent of monetization. | 2026-01-01 | ACTIVE | Ranking pipeline, monetization separation, governance | docs/OPTIME_PRINCIPLES.md | reports/EVIDENCE_PARITY_REGRESSION_TESTS.json | None | None | Foundational doctrine |
| PR-005 | Unknown Is Not Negative Evidence | UNKNOWN is not equivalent to NO and must not be treated as negative evidence. | Preserve fairness under incomplete coverage. | 2026-07-20 | ACTIVE | Ranking semantics, evidence state machine, explanation layer | frontend/src/lib/optime-v2-engine.ts | reports/EVIDENCE_PARITY_REGRESSION_TESTS.json | None | None | Owner clarification 2026-07-20 |
| PR-006 | Verified Case-Relevant Evidence May Strengthen Proven Match | Verified, case-relevant evidence may improve proven match under governed rules. | Reward true decision intelligence while preserving uncertainty integrity. | 2026-07-20 | ACTIVE | Proven match, governed ranking factors, causality audit | frontend/src/lib/optime-v2-engine.ts | reports/EVIDENCE_PARITY_REGRESSION_TESTS.json; reports/GOLDEN_CASE_RANKING_CAUSALITY_AUDIT.json | None | None | Owner clarification 2026-07-20 |
| PR-007 | Generic Completeness Must Not Drive Ranking | More generic profile completeness, source count, or evidence volume does not imply better facility ranking. | Prevent depth-of-research bias from masquerading as quality. | 2026-07-20 | ACTIVE | Comparator tie-breaks, ranking safeguards | frontend/src/lib/optime-v2-engine.ts | reports/EVIDENCE_PARITY_REGRESSION_TESTS.json | None | None | Owner clarification 2026-07-20 |
| PR-008 | Principle Consistency And Owner Approval Gate | Principle ambiguity/change and architectural deviation require explicit owner approval before semantic implementation. | Prevent silent product-philosophy drift. | 2026-07-21 | ACTIVE | All substantial implementation tasks | docs/OPTIME_PRINCIPLES.md; AGENTS.md | N/A (governance process rule) | None | None | Permanent governance directive 2026-07-21 |
| PR-009 | Parameter-First Facility Matching | OPTIME evaluates each facility by verified case-relevant parameters and capabilities, not by facility category/title alone. Facility type is one informational parameter and must not act as an automatic proxy for capability or as a blanket inclusion/exclusion rule unless a verified legal, regulatory, licensing, or clinical constraint directly applies to the case. Capabilities may exist at facility, unit, program, or service-line level and must be evaluated at the most specific evidenced level available. | Prevent category labels from hiding valid care capabilities or creating false assumptions; match the person to actual evidenced capabilities. | 2026-07-21 | ACTIVE | Candidate universe, eligibility, matching, ranking, facility/unit capability model, data acquisition, verification | docs/OPTIME_MASTER_PARAMETER_REGISTRY.md; frontend/src/lib/optime-v2-engine.ts | To be added before semantic engine changes | None | None | Explicit owner approval in conversation 2026-07-21: "הכל לפי פרמטרים" and "קדימה לעבודה" |

## Supersession Policy

When a principle changes with explicit approval:
- create a new PRINCIPLE_ID entry
- mark prior entry as SUPERSEDED
- fill SUPERSEDED_BY on the old row and SUPERSEDES on the new row
- record OWNER_APPROVAL_REFERENCE
- update implementation and test references

Do not overwrite historical entries.