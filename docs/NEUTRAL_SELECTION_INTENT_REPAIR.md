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

## Systemic answer and final-comparison contracts

Classification: B (implementation completion).
RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-006, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO

The completed pipeline, including interview-blocked responses, now observes the
original questionnaire separately from its canonical copy. Every nonempty scalar
and each list selection has source identity; newly added fields are included
without maintaining a question-name catalog. Explicit false/zero/neutral answers
are retained; questionnaireCompletion bookkeeping and empty values are excluded.

Canonical preservation does not prove decision use. Only exact quoted, mapped,
schema-constrained statements establish interpretation traces; these retain their
role/status/knowledge state. A scalar answer can link to a deterministic need only
through its exact explicit source path and preserved value. Grouped list sources
are not credited to every selection. Legacy/advisory preference summaries cannot
claim authoritative tracing. Unaccounted/untraced counts describe missing source
proof, not a conclusion that the system ignored an answer. Normalized/corrected
values may remain unaccounted until their provenance is linked. No artificial
100% usage coverage, inferred clinical rules, or new recommendation blocker.

The final governed evidence comparator records its actual base key and evidence
branch when ordering the complete candidate universe. Pair explanations use the
first real difference from this snapshot, including the named family criterion
or same-source regulatory/reputation measure. An earlier comparator's explanation
cannot replace the final one. True ties retain a shared rank; unavailable or
shape-mismatched snapshots cannot invent a differentiator. The private snapshot
is excluded from the facility claim ledger by its existing private-field rule,
so a derived ranking fact cannot become evidence for itself.

No sort key, eligibility policy, evidence comparability rule, availability weight
or display cap is changed. Auditing answers does not reinterpret narrative text.
Location resolution, comprehensive family-facing answer presentation, new clinical
mapping policies and deployment verification remain outside this repair.

Local validation after this completion: 145 tests pass, including 29 additional
source-accounting/final-comparator cases and the original 116 focused checks.
