# System security remediation

Classification: A (implementation bugs) / B (existing security and CI boundary completion).
RELEVANT EXISTING PRINCIPLES: PR-002, PR-004, PR-008; verified evidence and neutral ranking.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO

This patch reimplements the applicable system/learning endpoint guards from #368
on current main, without merging that branch's unrelated history. Human-intelligence,
adaptive-response and resident-outcome writes, knowledge-guard logging, internal
supervisor reads, diagnostics, and the intelligence read that can generate a profile
require the existing admin credential. The browser's best-effort adaptive signal
logging is denied; its questionnaire state and decision request still proceed.
No browser receives an admin credential.

Guardian no longer tolerates a failed subprocess. Its previous status is deleted
before execution, its generated status is excluded from git, and the reader rejects
missing, stale, malformed or inconsistent reports. A failed/missing run or blocked
verdict always fails the final gate. Reporting and artifact upload still run on
failure. PASS and WARN retain their existing policy meanings.

Research fetches are limited to public HTTP(S) destinations, with DNS addresses
validated before each hop and the connection pinned to the validated IP. HTTPS
retains certificate verification and the original hostname for TLS. Redirects,
response size and elapsed time are bounded; proxy environment variables are not
used. Fetch failures retain the existing requests exception handling contract.

Provider containment is tracked separately in #464. Registry production promotion,
unverified prices, matching/UNKNOWN semantics, API/frontend contracts, known failing
tests, dependency cleanup, and PR conflicts remain separate findings. Neither PR
protects production until reviewed, merged and deployed.
