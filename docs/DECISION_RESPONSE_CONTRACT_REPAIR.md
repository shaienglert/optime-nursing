# Decision response contract repair

Classification: A (implementation bug) / B (test contract maintenance).
RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-004, PR-008.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO

The integrated engine already computes `care_partner_options` but the public
response model silently drops it. Declare the field with an empty-list default;
preserve the engine's provenance, UNKNOWN prices and verification requirements.
This changes serialization only, not eligibility, ranking, or source trust.
HTTP tests check that both the served response and the stored decision retain the
same options. Missing options remain an empty list.

Restore the sales-copilot payment-independence test to normal CI collection by
checking its current approved anti-pay-to-rank statement instead of obsolete copy.
This test proves the sales response follows that policy; it does not by itself
prove the entire recommendation engine is independent of commercial inputs.
The remaining known-failure exclusions are unchanged.
