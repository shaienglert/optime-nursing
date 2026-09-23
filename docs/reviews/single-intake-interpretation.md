# Single intake interpretation completion

RELEVANT EXISTING PRINCIPLES: PR-001, PR-002, PR-003, PR-005, PR-008, PR-009; One Trusted Voice.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO additional approval. Class B completion of the single interpretation layer explicitly requested and approved in the project conversation; Class A removal of divergent frontend patch implementations.

The owner requested completion of the five enumerated tasks on 2026-09-23: one source fact record, all consumers using it, duplicate UI patch removal, confirmed fact continuity, and ten AI-enabled live journeys on the 200-facility pilot.

## Contract

`intake_interpretation.extract_intake_facts` owns extraction per answer revision. Clinical needs, living strategy, person fit, intent and care-delivery projections consume that record. Standalone compatibility callers use the same entry point. No ranking weights, clinical inference rules, facility evidence thresholds, or UNKNOWN meaning are relaxed.

An interpretation digest binds the fact record and validated AI packet to the reviewed profile. Stored reviewed inputs remain bound to their existing opaque handle. Changing answers invalidates the handle. Matching consumes the saved profile; report generation consumes the saved decision.

## Validation scope

Pilot means the isolated synthetic-pilot market with exactly 200 facilities and synthetic provenance. The ordinary production site's real facilities cannot substitute for this acceptance test. Existing offline pilot CI has AI disabled; it is regression coverage only. Live acceptance must assert AI CONSULTED_AND_VALIDATED, pilot identity and the reviewed interpretation identifier through matching.
