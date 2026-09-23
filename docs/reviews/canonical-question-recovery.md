# Keep canonical questions available after an invalid AI packet

RELEVANT EXISTING PRINCIPLES: canonical decision authority, visible uncertainty,
no invented client facts, verified intake before recommendations.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: A — the UI hid a policy-owned recovery question already emitted
by `_apply_canonical_policy_without_ai` when semantic packet validation failed.

Show only the existing deterministic fallback for the selected unresolved fact,
with canonical client INCOMPLETE and matching question provenance. Do not mark AI
validated, hydrate its failed patch, declare readiness or bypass confirmation.
An answer makes a fresh normal AI request. If no legitimate recovery question is
available, preserve the existing error/retry state.
