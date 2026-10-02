# Immediate incident delivery

RELEVANT EXISTING PRINCIPLES: observable failure, truthful delivery status,
privacy, no invented evidence or altered recommendation policy.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO
OWNER APPROVAL REQUIRED? NO
Classification: B. Implementation Completion. The owner explicitly requested
immediate mail and archived incident reports rather than hourly polling.

Use the existing supervisor incident SQL table as a durable outbox and the
existing SMTP service. Each persisted incident wakes the worker immediately;
15-second recovery polling only retries failed deliveries. Mail only the
verified owner shaienglert@gmail.com. No request bodies, family text, exception
messages, raw URLs or user identifiers. Browser telemetry is bounded and typed.

SMTP acceptance is not mailbox receipt. A crash after SMTP acceptance and before
the SQL commit can produce a duplicate on recovery; the stable event ID allows
the archive to deduplicate. Worker delivery must be activated and verified in
production. Browser signals are best effort; network disconnection or a process
crash before persistence cannot be covered by an in-process reporter.

Runtime/unhandled browser errors and server 5xx/exceptions are covered. A 200
response with legitimately pending evidence is not a technical fault. Semantic
failures require specific product contract signals; this does not claim universal
error detection. Existing hourly monitoring remains backup only.

Owner scope clarification (2026-10-02): notify only about failures in public
user flows on the live production site. The browser monitor is mounted only
in Vercel production and sends events only from public user pages. The proxy
forwards the page Referer only in production. Server incident capture requires
a Referer on the configured production origin and a public page category;
admin, health and telemetry endpoints are excluded. Internal requests without
user-page provenance do not generate mail. Startup probes are removed and
unclassified legacy pending events are suppressed rather than mailed.

This is page/origin provenance, not proof that a human made the request.
Automated tests against the live public site can share the same provenance;
requests without a Referer are not covered by server capture. No deliberate
production failure or diagnostic email is needed to validate the narrowing.
