# Intake unification: current boundaries and remaining work

RELEVANT EXISTING PRINCIPLES: PR-002, PR-005, PR-008, PR-009.
DOES THIS CHANGE ALTER ANY PRINCIPLE? NO.
OWNER APPROVAL REQUIRED? NO.
Classification: B — completion of the existing explicit intake composition.

PR #342 already established one prepared patient profile per recommendation
request. `run_decision_pipeline` builds it, `_run_prepared_decision` consumes its
living strategy, human context and client intent, and the core accepts that same
profile. Canonical decision state separately controls progression and visibility.
These are existing boundaries, not a new architecture.

## Remaining duplicate interpretation

The profile builder constructed a living strategy, then the verified human-context
builder constructed it again from the same input. This change passes the already
prepared strategy into the latter. Direct callers retain their existing behavior.
No interpretation, eligibility or ranking rules change.

## Remaining consolidation work (not claimed complete)

- `decision_engine_core.build_patient_needs_profile` maps care needs from raw input.
- `human_intelligence_runtime` and `living_strategy_runtime` derive separate signals
  during intake construction. Their meanings must be reconciled explicitly before
  removing either interpretation.
- `combined_care_solution_runtime._query_signals` reinterprets the narrative after
  intake, including ADL and medication requirements, and repeats for each facility.
- `_care_partner_layer` also reads the narrative downstream.
- Separate interview and recommendation HTTP requests rebuild intake; carrying a
  confirmed version across requests is not supplied by this request-local refactor.

Next consolidation must preserve unknowns, explicit denials, person attribution,
and distinctions such as reminders versus medication administration. Moving regex
rules into a new shared file alone would not solve these semantic conflicts.
Ten live verified journeys remain a separate release requirement.
