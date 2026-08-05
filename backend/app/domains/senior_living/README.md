# Senior Living Domain Adapter

This package owns Senior Living terminology and translates current patient/facility decision payloads into domain-neutral OPTIME Core contracts.

The first adapter is intentionally non-invasive: it does not change eligibility, ordering, scoring, or explanations produced by the existing engine. It only provides a neutral representation that future domains can also implement.
