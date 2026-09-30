# Live production journey regression fixes

RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-009; mandatory explainability.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO
Classification: A. Implementation Bug / B. Implementation Completion.

Observed live journeys showed an incoming pair explanation duplicated into the next
facility's comparison column, explicit absence of a dementia diagnosis treated as a
positive dementia signal, and confirmed memory-care classification standing in for
explicitly required secured-unit capability. Each fix preserves parameter-first
matching and keeps missing evidence UNKNOWN rather than negative.

Availability remains a direct-confirmation item under the existing neutral policy.
Summary and card wording distinguish verified care capabilities from admission
readiness. No budget, commercial, evidence-weighting, or ranking philosophy changes.

AI ranking narrative validation also drops individual sentences that contradict
verified medication/therapy capability or falsely claim the lowest known price.
Scores and candidate ordering are preserved; an unavailable explanation is explicitly
shown when nothing grounded remains. This guard covers these reproduced factual
contradictions; it is not a universal semantic verifier of arbitrary prose.
