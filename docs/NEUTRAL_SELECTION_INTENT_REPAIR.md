# Neutral questionnaire selections preserve client intent

Classification: A (implementation bug).
RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-006, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO

An exact questionnaire answer such as Not important must not create a desired
facility property because it contains the substring important. Positive control
values are matched exactly. Explicit questionnaire controls also prevent a
serialized mention of the question from recreating the declined preference.
The existing Required, Preferred and legacy Important answers retain their
established meanings; unresolved choices create no invented preference.

Apply complete-value neutral handling to the existing structured language,
activity, kosher and continuity branches. Preserve arbitrary positive property
values, clinical/system MUSTs, unknown provider evidence, ranking policy and
availability policy. This does not reinterpret free narrative negation; semantic
interpretation remains the existing AI layer's responsibility.

The earlier production report predates merged PRs 435-437. PR 438 independently
addresses source identity and canonical quote paths and is not modified here.
Availability is excluded from organic ranking by Principle 1. Current recorded
urgent-move evidence remains governed by the existing timing contract.

Explanation completion (B): prepend requested-language, required-activity,
kosher and continuity proof only from the actual must_pass/nice_match result.
Unrequested generic language capability is removed from personalized reasons.
Unknown, failed and subsequently withdrawn proof creates no positive bullet.
This changes presentation, not eligibility or the comparator. Every generated
bullet carries its explicit intent key, role and requested value in the audit.

Local validation: 116 focused tests pass, including the existing intent and
radius contracts, the neutral-choice matrix, ranking neutrality, explicit proof,
unknown/failure handling, arbitrary activities and repeated-fit refreshes.
