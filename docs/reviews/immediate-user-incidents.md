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
