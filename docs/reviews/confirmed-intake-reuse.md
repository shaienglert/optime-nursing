# Confirmed intake reuse

RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-008, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: B — completion of existing prepared-profile authority.
User direction: complete the unified profile through confirmation and recommendations.

Use the existing bounded server result store to hold a complete intake artifact.
The browser receives an opaque identifier, never authority to upload a profile.
The confirmation page fetches and displays the profile that will be reused.
Recommendation requests carrying that identifier must match all case inputs;
confirmation UI metadata and navigation continuity (`aiProcessContinuity`) are excluded.
The stored case remains the input authority; navigation events do not rewrite it.
Missing/expired/mismatched identifiers fail
closed instead of silently interpreting a different profile. Legacy requests without
an identifier retain their existing behavior for compatibility.

This store is process-local with the existing two-hour TTL and 256-entry bound.
Restart, eviction, or routing to another worker requires review again. It is not
durable cross-worker storage. No claim of durable persistence is made.

Combined-care signals are computed when constructing the intake profile and passed
through the existing pipeline, rather than inferred again for each facility. Their
Care-partner service requirements are likewise prepared at intake and consumed
without reading the story again. Current interpretation rules are preserved; semantic reconciliation of those rules
with the core need mapper remains separate work.
