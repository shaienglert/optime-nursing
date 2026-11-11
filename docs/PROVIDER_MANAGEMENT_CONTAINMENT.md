# Provider management containment

Classification: A (implementation bug) / B (completion of the existing admin boundary).
RELEVANT EXISTING PRINCIPLES: PR-002, PR-004, PR-008; unverified provider claims cannot improve organic ranking.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO

Provider management currently has no authenticated provider session. Body user IDs,
roles, email domains, and public license attributes cannot authenticate a caller.
All provider mutation endpoints therefore require the existing server-side
`X-Admin-Token` credential, including activity imports, verification persistence,
demo creation, staff and role changes, capabilities, and photos. This fails closed
when `OPTIME_ADMIN_TOKEN` is absent. Public search and read-only activity and memory
lookups remain public. Profile and completeness GETs are also protected because
they recompute and persist completeness data.

Registration and invitation responses no longer contain verification codes; the
identity service no longer returns the plaintext code. No admin credential is
embedded in or forwarded by the public frontend.

This is containment, not provider self-service authentication. Registration email
delivery is not connected. Secure provider login/session issuance, verified account
and facility ownership, per-field authorization, OTP attempt limits, and removal
of the guessed-domain allowlist remain prerequisites before reopening provider
self-service. Existing public-license matching is not proof of ownership.

This patch does not resolve the other system mutation, SSRF, CI, ranking, or API
contract findings. It must be reviewed and deployed before it protects production.
