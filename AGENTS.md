# OPTIME Repository Agent Governance

This file defines repository-wide implementation governance for all agent-driven tasks.

## Principle Authority

The canonical principle sources are:
- docs/OPTIME_PRINCIPLES.md
- docs/OPTIME_PRINCIPLES_REGISTRY.md

These principles are constitutional constraints, not optional guidance.

## Mandatory Pre-Change Principle Impact Check

Before substantial semantic work on ranking, scoring, recommendations, agents, evidence, unknown handling, confidence, source governance, monetization boundaries, or architecture, contributors must produce:
- RELEVANT EXISTING PRINCIPLES: <list>
- DOES THIS CHANGE ALTER ANY PRINCIPLE? YES / NO
- OWNER APPROVAL REQUIRED? YES / NO

## Classification Gate

Classify changes as:
- A. Implementation Bug
- B. Implementation Completion
- C. Product Principle Ambiguity
- D. Product Principle Change
- E. Architectural Deviation

Allowed without owner approval:
- A
- B

Owner approval required before semantic implementation:
- C
- D
- E

## Owner Approval Protocol

For C, D, or E, stop semantic implementation and present:
- CURRENT PRINCIPLE
- CURRENT BEHAVIOR
- PROBLEM DISCOVERED
- PROPOSED CHANGE
- WHY IT MAY BE NEEDED
- USER IMPACT
- RANKING/SCORING/DATA IMPACT
- RISKS
- ALTERNATIVES
- RECOMMENDATION

Do not treat silence as approval.

## Authorization Clarity

Broad implementation directives such as "continue", "fix it", "improve it", "optimize", or similar are execution instructions, not authorization to change established principles.

Principle changes, principle reinterpretation, and architectural deviations still require explicit owner approval under this governance.

## Permanent Clarification (Active)

- Missing information is not negative evidence.
- More generic completeness does not automatically imply a better facility.
- Verified, case-relevant evidence may strengthen proven match under governed rules.
- Unverified facility-supplied claims may not improve organic ranking.
- Facilities cannot buy ranking.

## Preservation Rules

- Preserve principle intent, not only wording.
- Do not collapse distinctions among quality, match, proven match, potential match, evidence confidence, unknown, negative evidence, source failure, and no data found.
- If two valid implementations imply different product philosophies, escalate for owner decision.
