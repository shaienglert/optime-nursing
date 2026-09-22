# Dementia denial mapping review

RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-005, PR-008.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: A — Implementation Bug.

Apply the user-supplied dementia-negation patch, preserving its authorship.
Explicit denials must not manufacture a positive memory-care requirement.
Preserve existing UNKNOWN/NO treatment and structured questionnaire evidence.

Review found that the supplied patch suppresses positive dementia statements
elsewhere in a mixed story, including a couple where only one person has
dementia. Three added regressions fail on the supplied patch. Scope the new
denial handling to matched mentions so other positive mentions survive.
Existing legacy phrase handling is unchanged; this is not a general-purpose
clinical negation or person-resolution implementation.

The original 11 and the three added regression cases pass locally. Full-suite
results are recorded in the pull request. No live acceptance pass is claimed.
This change does not resolve price evidence, missing follow-up questions,
respiratory mapping, or other reported intake issues.
