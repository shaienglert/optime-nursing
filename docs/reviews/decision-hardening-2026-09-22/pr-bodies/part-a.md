Integrate explicit decision authority and report hardening

Preserve the seven authored commits on latest main, #338/#339 behavior, and #340 scorer-import intent. Reports reuse only server-held decisions for identical inputs. Fix concurrent projection writes and unknown-critical-need report crashes.

Principle Impact Check: PR-002, PR-003, PR-005, PR-008, PR-009. Classification A/B. Alters principles: NO. Approval required: NO for implementation repairs; explicit owner approval for semantic corrections is recorded in the task.

Python 3.12.14 and exact requirements. Full suite before 798 passed / 2 failed; after 817 passed / 0 failed under the same 20 exclusions. Restored 21 passing exclusions. Frontend tsc exit 0; Vitest 12 files / 40 tests.

Parity 17/17: TOTAL_DIFFERENCES=391; ALLOWED_ADDITIONS=391; UNEXPECTED_DIFFERENCES=0. Only HTTP decision_id and the two intake fields are added; normalized rankings and DB writes match.
