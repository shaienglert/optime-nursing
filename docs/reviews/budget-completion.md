# Budget and clinical fact integrity

RELEVANT EXISTING PRINCIPLES: PR-002, PR-003, PR-005, PR-008, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: A — implementation bugs. Unknown is not a default; an explicit
replacement supersedes the prior answer. No affordability gate is relaxed.

The imported budget fix requires an unset initial budget, clearing stale ceilings
on an explicit unknown/floor answer, and preserving that answer in adaptive signals.
A family-entered 7000 is valid. Existing saved numeric amounts cannot safely be
classified as defaults solely from their value; do not erase legitimate answers.

Clinical facts must obey the existing explicit-evidence rule: generic rehabilitation
does not establish speech therapy, supervision does not establish skilled nursing,
and pill reminders do not establish complex medication management.
