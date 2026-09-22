# Results-page client clarification recovery

RELEVANT EXISTING PRINCIPLES: PR-003, PR-005, PR-008.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: A — Implementation Bug.

The simplified results page rendered a recommendation introduction even when
the canonical decision state required another client answer. It never displayed
the server's adaptive question. Read the authoritative state, show the existing
question and answer controls, preserve the answer using the same helper as the
adaptive interview, and return to that interview and confirmation flow.
Client-complete cases do not replay stale questions. System-blocked or malformed
responses offer recovery without describing the failure as a missing family fact.
No eligibility, ranking, pricing verification, or evidence rules change.

Do not promise options when the shortlist is empty. This patch does not expose
unverified facilities as recommendations or fix the missing pricing data path.

Pricing diagnosis (separate follow-up): decision_research_worker currently maps
social, medication, ADL, transport, dining, rehabilitation, couple, outside-care,
and continuum capabilities. It does not produce numeric verified pricing for
the budget comparator. A nonempty registry evidence record also skips fetching
the official source regardless of the requested dimension. Therefore the claim
that all empty results are solely a data gap is not established by this code.
