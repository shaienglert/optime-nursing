# OPTIME Core

`app.core` contains domain-neutral decision-support contracts.

Rules:

- Core must not import Senior Living, Employment, Facility, Patient, Candidate, Employer, Job, CMS, or other domain modules.
- Domains translate their entities into Core contracts through adapters.
- Core contracts do not rank, reject, or decide independently; they represent requirements, evidence, eligibility state, explanations, trade-offs, clarifications, and audit traces.
- Existing domain behavior must be preserved by golden tests while logic is migrated incrementally.
