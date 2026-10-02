# Urgent move / unknown availability

RELEVANT EXISTING PRINCIPLES: missing information is not negative evidence;
UNKNOWN availability is neutral and requires direct confirmation; never fabricate
price, availability or medical capability.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO
Classification: A. Implementation Bug / B. Implementation Completion.

The live owner screenshot showed no recommendations for an independent resident
with mild forgetfulness, a $5,000 budget and a move within 30 days. Replaying the
structured dimensions against the main Las Vegas catalog found all 374 facilities
INSUFFICIENT_EVIDENCE because current_availability was the only critical unknown.
The parameter table deliberately returns UNKNOWN for direct confirmation.

Unknown or absent availability remains UNKNOWN and is listed for follow-up, but
does not become an unknown clinical requirement. Explicit NO remains a gap and
unknown clinical MUSTs remain blocking. Unknown prices remain unknown and do not
become affordable recommendations. No coordinate or source data is invented.

Separately, deployment inspection found frontend main 2abb14b7 while the primary
backend remained at e2a67ce7. The backend was aligned to main in deployment
dep-davp4oad0e5s738rpb20, verified live and healthy on 2026-10-02. PR #424 was
not deployed; Draft/NO-GO remains.

Owner explicitly requested retiring the mileage interview question on 2026-10-02.
The area preference stays. Restore and submission clear old persisted radius
values, and OOmniker recognizes explicit removal instead of confirming a no-op.
No cutover is included. Validation: 40 backend tests, 13 intake tests, TypeScript.

Price-floor completion uses only verified positive room base prices in the real
catalog area. No room price means no known floor; synthetic and other-area rows
are excluded. This is not total affordability or a guaranteed current quote.
